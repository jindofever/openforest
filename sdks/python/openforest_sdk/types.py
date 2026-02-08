from __future__ import annotations

from dataclasses import dataclass
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
class PlanetView:
    id: int
    x: float
    y: float
    level: int
    energy: float
    energy_cap: float
    silver: float
    silver_cap: float
    defense: float
    speed: float
    sensor_range: float
    owner: int | None
    is_artifact: bool
    visibility: str
    last_seen_tick: int


@dataclass
class FleetView:
    id: int
    owner: int
    source_id: int
    dest_id: int
    energy: float
    ticks_remaining: int
    total_ticks: int
    x: float
    y: float


@dataclass
class PingView:
    id: int
    x: float
    y: float
    radius: float
    strength: float
    source_player: int
    tick: int


@dataclass
class Observation:
    tick: int
    player_id: int | None
    planets: list[dict[str, Any]]
    fleets: list[dict[str, Any]]
    pings: list[dict[str, Any]]
    scores: list[dict[str, Any]]
    max_actions: int
