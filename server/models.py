from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict, Union


class ActionScan(TypedDict):
    type: Literal["scan"]
    x: float
    y: float
    radius: float


class ActionSendFleet(TypedDict):
    type: Literal["send_fleet"]
    from_id: int
    to_id: int
    energy: float


class ActionUpgrade(TypedDict):
    type: Literal["upgrade"]
    planet_id: int
    upgrade: Literal["energy", "silver", "defense", "speed", "sensor"]


Action = Union[ActionScan, ActionSendFleet, ActionUpgrade]


@dataclass
class Planet:
    id: int
    x: float
    y: float
    level: int
    energy: float
    energy_cap: float
    energy_growth: float
    silver: float
    silver_cap: float
    silver_growth: float
    defense: float
    speed: float
    sensor_range: float
    owner: int | None = None
    is_artifact: bool = False


@dataclass
class Fleet:
    id: int
    owner: int
    source_id: int
    dest_id: int
    energy: float
    launch_tick: int
    total_ticks: int
    ticks_remaining: int


@dataclass
class Ping:
    id: int
    x: float
    y: float
    radius: float
    strength: float
    source_player: int
    tick: int
    ttl: int


@dataclass
class PlayerState:
    id: int
    name: str
    score: float = 0.0
    territory_score: float = 0.0
    artifact_score: float = 0.0
    artifacts_held: int = 0
    known_planets: dict[int, dict[str, Any]] = field(default_factory=dict)


@dataclass
class MatchConfig:
    seed: int
    tick_ms: int
    match_ticks: int
    planet_count: int
    artifact_count: int
    max_actions_per_tick: int
    speed_const: float
    capture_threshold_fraction: float
    defense_multiplier: float
    ping_ttl_ticks: int
    ping_jitter: float
    ping_base_radius: float
    ping_base_strength: float
    artifact_ping_radius: float
    artifact_ping_strength: float
    artifact_points_per_tick: float
    score_top_n: int
    commit_timeout_ms: int
    reveal_timeout_ms: int
    player_home_min_distance: float
