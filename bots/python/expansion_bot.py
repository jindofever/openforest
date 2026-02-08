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
    neutrals = [p for p in planets if p.get("owner") is None]
    actions: list[dict[str, Any]] = []

    if not owned:
        return actions

    for source in sorted(owned, key=lambda p: p.get("energy", 0.0), reverse=True):
        if len(actions) >= observation.get("max_actions", 5):
            break
        if source.get("energy", 0.0) < source.get("energy_cap", 0.0) * 0.5:
            continue
        if not neutrals:
            break
        target = min(
            neutrals,
            key=lambda p: (p["x"] - source["x"]) ** 2 + (p["y"] - source["y"]) ** 2,
        )
        actions.append({
            "type": "send_fleet",
            "from_id": source["id"],
            "to_id": target["id"],
            "energy": max(8.0, source["energy"] * 0.35),
        })
    if len(actions) < observation.get("max_actions", 5):
        home = max(owned, key=lambda p: p.get("energy_cap", 0.0))
        actions.append({"type": "upgrade", "planet_id": home["id"], "upgrade": "energy"})
    return actions


if __name__ == "__main__":
    run_stdio(bot)
