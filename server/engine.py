from __future__ import annotations

import math
import random
from typing import Any

from .models import Action, Fleet, MatchConfig, Planet, Ping, PlayerState
from .utils import clamp, deterministic_rng, distance


LEVEL_DISTRIBUTION = [
    (1, 0.4),
    (2, 0.25),
    (3, 0.2),
    (4, 0.1),
    (5, 0.05),
]


def stats_for_level(level: int) -> dict[str, float]:
    energy_cap = 40 + level * 40
    energy_growth = 1.0 + level * 0.6
    silver_cap = 30 + level * 30
    silver_growth = 0.6 + level * 0.35
    defense = 0.8 + level * 0.25
    speed = 0.6 + level * 0.08
    sensor_range = 0.18 + level * 0.06
    return {
        "energy_cap": energy_cap,
        "energy_growth": energy_growth,
        "silver_cap": silver_cap,
        "silver_growth": silver_growth,
        "defense": defense,
        "speed": speed,
        "sensor_range": sensor_range,
    }


class GameState:
    def __init__(self, config: MatchConfig, player_names: list[str]):
        self.config = config
        self.tick = 0
        self.planets: list[Planet] = []
        self.fleets: list[Fleet] = []
        self.pings: list[Ping] = []
        self.players = [PlayerState(id=i, name=player_names[i]) for i in range(len(player_names))]
        self._next_fleet_id = 1
        self._next_ping_id = 1
        self._generate_world()

    def _generate_world(self) -> None:
        rng = random.Random(self.config.seed)
        planets: list[Planet] = []
        for planet_id in range(self.config.planet_count):
            x = rng.uniform(-1, 1)
            y = rng.uniform(-1, 1)
            level = self._roll_level(rng)
            stats = stats_for_level(level)
            planet = Planet(
                id=planet_id,
                x=x,
                y=y,
                level=level,
                energy=stats["energy_cap"] * 0.5,
                energy_cap=stats["energy_cap"],
                energy_growth=stats["energy_growth"],
                silver=stats["silver_cap"] * 0.4,
                silver_cap=stats["silver_cap"],
                silver_growth=stats["silver_growth"],
                defense=stats["defense"],
                speed=stats["speed"],
                sensor_range=stats["sensor_range"],
            )
            planets.append(planet)

        self.planets = planets
        self._assign_home_planets(rng)
        self._assign_artifacts(rng)

    def _roll_level(self, rng: random.Random) -> int:
        roll = rng.random()
        cumulative = 0.0
        for level, chance in LEVEL_DISTRIBUTION:
            cumulative += chance
            if roll <= cumulative:
                return level
        return 1

    def _assign_home_planets(self, rng: random.Random) -> None:
        candidates = self.planets[:]
        rng.shuffle(candidates)
        chosen: list[Planet] = []
        min_distance = self.config.player_home_min_distance
        for candidate in candidates:
            if any(distance((candidate.x, candidate.y), (home.x, home.y)) < min_distance for home in chosen):
                continue
            chosen.append(candidate)
            if len(chosen) == len(self.players):
                break
        if len(chosen) < len(self.players):
            for candidate in candidates:
                if candidate in chosen:
                    continue
                chosen.append(candidate)
                if len(chosen) == len(self.players):
                    break

        for player, home in zip(self.players, chosen):
            home.level = 3
            stats = stats_for_level(3)
            home.energy_cap = stats["energy_cap"]
            home.energy_growth = stats["energy_growth"]
            home.silver_cap = stats["silver_cap"]
            home.silver_growth = stats["silver_growth"]
            home.defense = stats["defense"]
            home.speed = stats["speed"]
            home.sensor_range = stats["sensor_range"]
            home.energy = home.energy_cap * 0.8
            home.silver = home.silver_cap * 0.5
            home.owner = player.id

    def _assign_artifacts(self, rng: random.Random) -> None:
        candidates = [p for p in self.planets if p.owner is None]
        candidates.sort(key=lambda p: p.level, reverse=True)
        top = candidates[: max(self.config.artifact_count * 4, self.config.artifact_count)]
        rng.shuffle(top)
        for planet in top[: self.config.artifact_count]:
            planet.is_artifact = True

    def _planet_by_id(self, planet_id: int) -> Planet:
        return self.planets[planet_id]

    def advance_tick(self, actions_by_player: dict[int, list[Action]]) -> dict[str, Any]:
        self._apply_growth()
        scans = self._process_actions(actions_by_player)
        self._move_fleets()
        self._resolve_arrivals()
        self._decay_pings()
        self._emit_artifact_pings()
        self._update_scores()
        snapshot = self._build_snapshot(scans)
        self.tick += 1
        return snapshot

    def _apply_growth(self) -> None:
        for planet in self.planets:
            planet.energy = clamp(planet.energy + planet.energy_growth, 0.0, planet.energy_cap)
            planet.silver = clamp(planet.silver + planet.silver_growth, 0.0, planet.silver_cap)

    def _process_actions(self, actions_by_player: dict[int, list[Action]]) -> dict[int, list[int]]:
        scans: dict[int, list[int]] = {pid: [] for pid in range(len(self.players))}
        for player_id in sorted(actions_by_player.keys()):
            actions = actions_by_player[player_id][: self.config.max_actions_per_tick]
            for action in actions:
                if action["type"] == "scan":
                    scan_ids = self._handle_scan(player_id, action)
                    scans[player_id].extend(scan_ids)
                elif action["type"] == "send_fleet":
                    self._handle_send_fleet(player_id, action)
                elif action["type"] == "upgrade":
                    self._handle_upgrade(player_id, action)
        return scans

    def _handle_scan(self, player_id: int, action: Action) -> list[int]:
        radius = float(action["radius"])
        center = (float(action["x"]), float(action["y"]))
        cost = 8.0 * radius
        owned = [p for p in self.planets if p.owner == player_id]
        if not owned:
            return []
        owned.sort(key=lambda p: distance((p.x, p.y), center))
        source = owned[0]
        if source.energy < cost:
            return []
        source.energy -= cost
        revealed = []
        for planet in self.planets:
            if distance((planet.x, planet.y), center) <= radius:
                revealed.append(planet.id)
        return revealed

    def _handle_send_fleet(self, player_id: int, action: Action) -> None:
        source_id = int(action["from_id"])
        dest_id = int(action["to_id"])
        if source_id == dest_id:
            return
        if source_id < 0 or source_id >= len(self.planets) or dest_id < 0 or dest_id >= len(self.planets):
            return
        source = self._planet_by_id(source_id)
        if source.owner != player_id:
            return
        energy = float(action["energy"])
        if energy <= 0 or energy > source.energy:
            return
        dest = self._planet_by_id(dest_id)
        dist = distance((source.x, source.y), (dest.x, dest.y))
        travel_ticks = max(1, math.ceil(dist / (source.speed * self.config.speed_const)))
        source.energy -= energy
        fleet = Fleet(
            id=self._next_fleet_id,
            owner=player_id,
            source_id=source_id,
            dest_id=dest_id,
            energy=energy,
            launch_tick=self.tick,
            total_ticks=travel_ticks,
            ticks_remaining=travel_ticks,
        )
        self._next_fleet_id += 1
        self.fleets.append(fleet)
        self._emit_fleet_ping(fleet)

    def _handle_upgrade(self, player_id: int, action: Action) -> None:
        planet_id = int(action["planet_id"])
        if planet_id < 0 or planet_id >= len(self.planets):
            return
        planet = self._planet_by_id(planet_id)
        if planet.owner != player_id:
            return
        upgrade = action["upgrade"]
        cost = 15 + planet.level * 12
        if planet.silver < cost:
            return
        planet.silver -= cost
        if upgrade == "energy":
            planet.energy_cap += 12 + planet.level * 3
            planet.energy_growth += 0.2 + planet.level * 0.05
        elif upgrade == "silver":
            planet.silver_cap += 10 + planet.level * 3
            planet.silver_growth += 0.15 + planet.level * 0.05
        elif upgrade == "defense":
            planet.defense += 0.15 + planet.level * 0.04
        elif upgrade == "speed":
            planet.speed += 0.04 + planet.level * 0.01
        elif upgrade == "sensor":
            planet.sensor_range += 0.04 + planet.level * 0.01

    def _move_fleets(self) -> None:
        for fleet in self.fleets:
            fleet.ticks_remaining -= 1

    def _resolve_arrivals(self) -> None:
        arrived: list[Fleet] = [fleet for fleet in self.fleets if fleet.ticks_remaining <= 0]
        arrived.sort(key=lambda f: f.id)
        for fleet in arrived:
            dest = self._planet_by_id(fleet.dest_id)
            if dest.owner is None or dest.owner == fleet.owner:
                dest.owner = fleet.owner
                dest.energy = clamp(dest.energy + fleet.energy, 0.0, dest.energy_cap)
            else:
                self._resolve_combat(dest, fleet)
        self.fleets = [fleet for fleet in self.fleets if fleet.ticks_remaining > 0]

    def _resolve_combat(self, dest: Planet, fleet: Fleet) -> None:
        defense_factor = 1.0 + dest.defense * self.config.defense_multiplier
        damage = fleet.energy / defense_factor
        dest.energy -= damage
        capture_threshold = dest.energy_cap * self.config.capture_threshold_fraction
        if dest.energy < capture_threshold:
            dest.owner = fleet.owner
            leftover = max(0.0, fleet.energy - damage)
            dest.energy = clamp(leftover, 0.0, dest.energy_cap)
        else:
            dest.energy = clamp(dest.energy, 0.0, dest.energy_cap)

    def _emit_fleet_ping(self, fleet: Fleet) -> None:
        source = self._planet_by_id(fleet.source_id)
        rng = deterministic_rng(self.config.seed, ["ping", self.tick, fleet.id])
        jitter_x = rng.uniform(-self.config.ping_jitter, self.config.ping_jitter)
        jitter_y = rng.uniform(-self.config.ping_jitter, self.config.ping_jitter)
        radius = self.config.ping_base_radius + math.sqrt(fleet.energy) * 0.01
        strength = self.config.ping_base_strength + math.sqrt(fleet.energy) * 0.02
        if source.is_artifact:
            radius += self.config.artifact_ping_radius * 0.5
            strength += self.config.artifact_ping_strength * 0.8
        ping = Ping(
            id=self._next_ping_id,
            x=source.x + jitter_x,
            y=source.y + jitter_y,
            radius=radius,
            strength=strength,
            source_player=fleet.owner,
            tick=self.tick,
            ttl=self.config.ping_ttl_ticks,
        )
        self._next_ping_id += 1
        self.pings.append(ping)

    def _emit_artifact_pings(self) -> None:
        for planet in self.planets:
            if not planet.is_artifact or planet.owner is None:
                continue
            ping = Ping(
                id=self._next_ping_id,
                x=planet.x,
                y=planet.y,
                radius=self.config.artifact_ping_radius,
                strength=self.config.artifact_ping_strength,
                source_player=planet.owner,
                tick=self.tick,
                ttl=1,
            )
            self._next_ping_id += 1
            self.pings.append(ping)

    def _decay_pings(self) -> None:
        for ping in self.pings:
            ping.ttl -= 1
        self.pings = [ping for ping in self.pings if ping.ttl > 0]

    def _update_scores(self) -> None:
        for player in self.players:
            owned = [p for p in self.planets if p.owner == player.id]
            owned.sort(key=lambda p: p.energy_cap, reverse=True)
            territory_gain = sum(p.energy_cap for p in owned[: self.config.score_top_n]) / 1000.0
            artifacts = sum(1 for p in self.planets if p.owner == player.id and p.is_artifact)
            player.artifacts_held = artifacts
            artifact_gain = artifacts * self.config.artifact_points_per_tick
            player.territory_score += territory_gain
            player.artifact_score += artifact_gain
            player.score = player.territory_score + player.artifact_score

    def _build_snapshot(self, scans: dict[int, list[int]]) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "planets": [self._planet_to_dict(p) for p in self.planets],
            "fleets": [self._fleet_to_dict(f) for f in self.fleets],
            "pings": [self._ping_to_dict(p) for p in self.pings],
            "scores": [self._player_score(p) for p in self.players],
            "scans": scans,
        }

    def _planet_to_dict(self, planet: Planet) -> dict[str, Any]:
        return {
            "id": planet.id,
            "x": planet.x,
            "y": planet.y,
            "level": planet.level,
            "energy": planet.energy,
            "energy_cap": planet.energy_cap,
            "energy_growth": planet.energy_growth,
            "silver": planet.silver,
            "silver_cap": planet.silver_cap,
            "silver_growth": planet.silver_growth,
            "defense": planet.defense,
            "speed": planet.speed,
            "sensor_range": planet.sensor_range,
            "owner": planet.owner,
            "is_artifact": planet.is_artifact,
        }

    def _fleet_to_dict(self, fleet: Fleet) -> dict[str, Any]:
        source = self._planet_by_id(fleet.source_id)
        dest = self._planet_by_id(fleet.dest_id)
        progress = 1.0 - (fleet.ticks_remaining / fleet.total_ticks)
        x = source.x + (dest.x - source.x) * progress
        y = source.y + (dest.y - source.y) * progress
        return {
            "id": fleet.id,
            "owner": fleet.owner,
            "source_id": fleet.source_id,
            "dest_id": fleet.dest_id,
            "energy": fleet.energy,
            "ticks_remaining": fleet.ticks_remaining,
            "total_ticks": fleet.total_ticks,
            "x": x,
            "y": y,
        }

    def _ping_to_dict(self, ping: Ping) -> dict[str, Any]:
        return {
            "id": ping.id,
            "x": ping.x,
            "y": ping.y,
            "radius": ping.radius,
            "strength": ping.strength,
            "source_player": ping.source_player,
            "tick": ping.tick,
        }

    def _player_score(self, player: PlayerState) -> dict[str, Any]:
        return {
            "id": player.id,
            "name": player.name,
            "score": player.score,
            "territory_score": player.territory_score,
            "artifact_score": player.artifact_score,
            "artifacts_held": player.artifacts_held,
        }

    def observation_for_player(self, player_id: int, scans: list[int] | None = None) -> dict[str, Any]:
        if scans is None:
            scans = []
        player = self.players[player_id]
        visible_planets = set(scans)
        owned = [p for p in self.planets if p.owner == player_id]
        for planet in owned:
            visible_planets.add(planet.id)
        for planet in owned:
            for other in self.planets:
                if distance((planet.x, planet.y), (other.x, other.y)) <= planet.sensor_range:
                    visible_planets.add(other.id)

        observations = []
        for planet in self.planets:
            if planet.id in visible_planets:
                snapshot = self._planet_to_dict(planet)
                snapshot["visibility"] = "owned" if planet.owner == player_id else "visible"
                snapshot["last_seen_tick"] = self.tick
                player.known_planets[planet.id] = snapshot
            elif planet.id in player.known_planets:
                snapshot = dict(player.known_planets[planet.id])
                snapshot["visibility"] = "stale"
            else:
                continue
            observations.append(snapshot)

        visible_fleets = []
        for fleet in self.fleets:
            source = self._planet_by_id(fleet.source_id)
            dest = self._planet_by_id(fleet.dest_id)
            progress = 1.0 - (fleet.ticks_remaining / fleet.total_ticks)
            x = source.x + (dest.x - source.x) * progress
            y = source.y + (dest.y - source.y) * progress
            if any(distance((x, y), (p.x, p.y)) <= p.sensor_range for p in owned):
                visible_fleets.append(self._fleet_to_dict(fleet))

        visible_pings = []
        for ping in self.pings:
            if any(distance((ping.x, ping.y), (p.x, p.y)) <= p.sensor_range for p in owned):
                visible_pings.append(self._ping_to_dict(ping))

        return {
            "tick": self.tick,
            "player_id": player_id,
            "planets": observations,
            "fleets": visible_fleets,
            "pings": visible_pings,
            "scores": [self._player_score(p) for p in self.players],
            "max_actions": self.config.max_actions_per_tick,
            "match_ticks": self.config.match_ticks,
            "tick_ms": self.config.tick_ms,
        }

    def observation_omniscient(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "player_id": None,
            "planets": [self._planet_to_dict(p) for p in self.planets],
            "fleets": [self._fleet_to_dict(f) for f in self.fleets],
            "pings": [self._ping_to_dict(p) for p in self.pings],
            "scores": [self._player_score(p) for p in self.players],
            "max_actions": self.config.max_actions_per_tick,
            "match_ticks": self.config.match_ticks,
            "tick_ms": self.config.tick_ms,
        }
