from __future__ import annotations

import secrets
from typing import Any, Callable

from fastapi import FastAPI

from .commit import commit_hash


BotFn = Callable[[dict[str, Any]], list[dict[str, Any]]]


def create_http_app(bot_fn: BotFn) -> FastAPI:
    app = FastAPI()
    pending: dict[int, tuple[list[dict[str, Any]], str]] = {}

    @app.post("/act")
    async def act(payload: dict[str, Any]) -> dict[str, Any]:
        phase = payload.get("phase")
        tick = int(payload.get("tick", 0))
        if phase == "commit":
            observation = payload.get("observation", {})
            actions = bot_fn(observation)
            nonce = secrets.token_hex(8)
            pending[tick] = (actions, nonce)
            commit = commit_hash(actions, nonce)
            return {"commit": commit}
        if phase == "reveal":
            actions, nonce = pending.pop(tick, ([], ""))
            return {"actions": actions, "nonce": nonce}
        return {"error": "unknown_phase"}

    return app
