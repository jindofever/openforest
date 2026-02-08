import json
import os
from typing import Any


class ReplayLogger:
    def __init__(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self._file = open(path, "w", encoding="utf-8")

    def log_tick(
        self,
        tick: int,
        state: dict[str, Any],
        observations: dict[int, dict[str, Any]],
        actions: dict[int, list[dict[str, Any]]],
    ) -> None:
        record = {
            "tick": tick,
            "state": state,
            "observations": observations,
            "actions": actions,
        }
        self._file.write(json.dumps(record, separators=(",", ":")) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()
