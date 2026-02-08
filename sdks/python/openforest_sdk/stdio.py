from __future__ import annotations

import json
import secrets
import sys
from typing import Any, Callable

from .commit import commit_hash


BotFn = Callable[[dict[str, Any]], list[dict[str, Any]]]


def run_stdio(bot_fn: BotFn) -> None:
    pending: dict[int, tuple[list[dict[str, Any]], str]] = {}
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        message = json.loads(line)
        msg_type = message.get("type")
        tick = message.get("tick")
        if msg_type == "commit":
            observation = message.get("observation", {})
            actions = bot_fn(observation)
            nonce = secrets.token_hex(8)
            pending[int(tick)] = (actions, nonce)
            commit = commit_hash(actions, nonce)
            response = {"type": "commit", "tick": tick, "commit": commit}
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        elif msg_type == "reveal":
            actions, nonce = pending.pop(int(tick), ([], ""))
            response = {"type": "reveal", "tick": tick, "actions": actions, "nonce": nonce}
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
