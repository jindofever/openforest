import os
import sys
from typing import Any

SDK_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sdks", "python"))
if SDK_PATH not in sys.path:
    sys.path.insert(0, SDK_PATH)

from openforest_sdk import run_stdio


def bot(observation: dict[str, Any]) -> list[dict[str, Any]]:
    player_id = observation.get("player_id")
    planets = observation.get("planets", [])
    owned = [p for p in planets if p.get("owner") == player_id]
    targets = [p for p in planets if p.get("owner") not in (None, player_id)]
    neutrals = [p for p in planets if p.get("owner") is None]

    if not owned:
        return []

    source = max(owned, key=lambda p: p.get("energy", 0.0))
    target_pool = targets or neutrals
    if not target_pool:
        return []
    target = min(target_pool, key=lambda p: (p["x"] - source["x"]) ** 2 + (p["y"] - source["y"]) ** 2)
    return [{
        "type": "send_fleet",
        "from_id": source["id"],
        "to_id": target["id"],
        "energy": max(10.0, source["energy"] * 0.6),
    }]


if __name__ == "__main__":
    run_stdio(bot)
