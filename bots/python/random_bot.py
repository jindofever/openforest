import os
import random
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
    actions: list[dict[str, Any]] = []
    if not owned:
        return actions

    rng = random.Random(observation.get("tick", 0))
    if rng.random() < 0.4:
        source = rng.choice(owned)
        actions.append({
            "type": "scan",
            "x": source["x"],
            "y": source["y"],
            "radius": rng.uniform(0.2, 0.4),
        })

    targets = [p for p in planets if p.get("owner") != player_id]
    if targets:
        source = rng.choice(owned)
        target = rng.choice(targets)
        actions.append({
            "type": "send_fleet",
            "from_id": source["id"],
            "to_id": target["id"],
            "energy": max(5.0, source["energy"] * 0.3),
        })

    if rng.random() < 0.3:
        source = rng.choice(owned)
        actions.append({
            "type": "upgrade",
            "planet_id": source["id"],
            "upgrade": rng.choice(["energy", "silver", "defense", "speed", "sensor"]),
        })

    return actions[: observation.get("max_actions", 5)]


if __name__ == "__main__":
    run_stdio(bot)
