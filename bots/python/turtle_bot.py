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
    actions: list[dict[str, Any]] = []

    if not owned:
        return actions

    home = max(owned, key=lambda p: p.get("energy_cap", 0.0))
    actions.append({"type": "upgrade", "planet_id": home["id"], "upgrade": "defense"})
    actions.append({"type": "upgrade", "planet_id": home["id"], "upgrade": "sensor"})

    if len(actions) < observation.get("max_actions", 5):
        actions.append({
            "type": "scan",
            "x": home["x"],
            "y": home["y"],
            "radius": 0.35,
        })

    if home.get("energy", 0.0) > home.get("energy_cap", 1.0) * 0.7:
        targets = [p for p in planets if p.get("owner") is None]
        if targets:
            target = min(
                targets,
                key=lambda p: (p["x"] - home["x"]) ** 2 + (p["y"] - home["y"]) ** 2,
            )
            actions.append({
                "type": "send_fleet",
                "from_id": home["id"],
                "to_id": target["id"],
                "energy": home["energy"] * 0.25,
            })

    return actions[: observation.get("max_actions", 5)]


if __name__ == "__main__":
    run_stdio(bot)
