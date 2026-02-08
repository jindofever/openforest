from server.engine import GameState
from server.models import Fleet, MatchConfig


def build_config() -> MatchConfig:
    return MatchConfig(
        seed=1,
        tick_ms=500,
        match_ticks=10,
        planet_count=10,
        artifact_count=1,
        max_actions_per_tick=5,
        speed_const=0.08,
        capture_threshold_fraction=0.15,
        defense_multiplier=0.2,
        ping_ttl_ticks=3,
        ping_jitter=0.03,
        ping_base_radius=0.05,
        ping_base_strength=0.4,
        artifact_ping_radius=0.08,
        artifact_ping_strength=0.25,
        artifact_points_per_tick=1.5,
        score_top_n=10,
        commit_timeout_ms=200,
        reveal_timeout_ms=200,
        player_home_min_distance=0.7,
    )


def test_combat_capture() -> None:
    state = GameState(build_config(), ["A", "B"])
    planet = state.planets[0]
    planet.owner = 1
    planet.energy_cap = 100
    planet.energy = 10
    planet.defense = 1.0

    fleet = Fleet(
        id=1,
        owner=0,
        source_id=0,
        dest_id=0,
        energy=50,
        launch_tick=0,
        total_ticks=1,
        ticks_remaining=0,
    )

    state._resolve_combat(planet, fleet)
    assert planet.owner == 0
    assert planet.energy > 0
    assert planet.energy < planet.energy_cap


def test_combat_defense_holds() -> None:
    state = GameState(build_config(), ["A", "B"])
    planet = state.planets[0]
    planet.owner = 1
    planet.energy_cap = 100
    planet.energy = 80
    planet.defense = 2.0

    fleet = Fleet(
        id=2,
        owner=0,
        source_id=0,
        dest_id=0,
        energy=30,
        launch_tick=0,
        total_ticks=1,
        ticks_remaining=0,
    )

    state._resolve_combat(planet, fleet)
    assert planet.owner == 1
    assert planet.energy > 0
