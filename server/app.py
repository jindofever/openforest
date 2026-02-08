from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

from .bot_manager import BotManager
from .engine import GameState
from .models import MatchConfig
from .replay import ReplayLogger


def load_config(path: str) -> MatchConfig:
    with open(path, "r", encoding="utf-8") as file:
        raw = json.load(file)
    return MatchConfig(**raw)


def create_app(
    config_path: str | None = None,
    player_count: int = 4,
    http_bots: list[str] | None = None,
    replay_path: str | None = None,
) -> FastAPI:
    config_path = config_path or os.path.join(os.path.dirname(__file__), "..", "config.json")
    config_path = os.path.abspath(config_path)
    config = load_config(config_path)
    player_names = [f"Player {i}" for i in range(player_count)]
    game_state = GameState(config, player_names)
    bot_manager = BotManager(config.commit_timeout_ms, config.reveal_timeout_ms)

    if http_bots:
        for idx, url in enumerate(http_bots):
            if idx < player_count:
                bot_manager.register_http(idx, url)

    if replay_path is None:
        timestamp = int(time.time())
        replay_path = os.path.join(os.path.dirname(__file__), "..", "replays", f"match_{timestamp}.jsonl")
    replay_logger = ReplayLogger(os.path.abspath(replay_path))

    app = FastAPI()
    app.state.config = config
    app.state.game_state = game_state
    app.state.bot_manager = bot_manager
    app.state.replay_logger = replay_logger
    app.state.spectators: list[dict[str, Any]] = []
    app.state.latest_observations: dict[int, dict[str, Any]] = {}

    @app.on_event("startup")
    async def start_match() -> None:
        asyncio.create_task(run_match(app))

    @app.get("/status")
    async def status() -> dict[str, Any]:
        return {
            "tick": app.state.game_state.tick,
            "match_ticks": app.state.config.match_ticks,
            "players": [p.name for p in app.state.game_state.players],
        }

    @app.websocket("/ws/player/{player_id}")
    async def ws_player(websocket: WebSocket, player_id: int) -> None:
        await websocket.accept()
        app.state.bot_manager.register_ws(player_id, websocket)
        queue = app.state.bot_manager.ws_connections[player_id]["queue"]
        try:
            while True:
                data = await websocket.receive_json()
                await queue.put(data)
        except WebSocketDisconnect:
            return

    @app.websocket("/ws/spectator")
    async def ws_spectator(websocket: WebSocket) -> None:
        await websocket.accept()
        spectator = {"ws": websocket, "player_id": None, "omniscient": True}
        app.state.spectators.append(spectator)
        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "set_perspective":
                    spectator["player_id"] = data.get("player_id")
                    spectator["omniscient"] = bool(data.get("omniscient"))
        except WebSocketDisconnect:
            app.state.spectators.remove(spectator)

    return app


async def run_match(app: FastAPI) -> None:
    state: GameState = app.state.game_state
    config: MatchConfig = app.state.config
    bot_manager: BotManager = app.state.bot_manager
    replay_logger: ReplayLogger = app.state.replay_logger

    observations: dict[int, dict[str, Any]] = {
        player.id: state.observation_for_player(player.id) for player in state.players
    }
    app.state.latest_observations = observations

    for _ in range(config.match_ticks):
        await bot_manager.commit_phase(state.tick, observations)
        actions = await bot_manager.reveal_phase(state.tick)
        snapshot = state.advance_tick(actions)
        processed_tick = snapshot["tick"]
        observations = {
            player.id: state.observation_for_player(player.id, snapshot["scans"].get(player.id, []))
            for player in state.players
        }
        app.state.latest_observations = observations
        replay_logger.log_tick(processed_tick, snapshot, observations, actions)
        await broadcast_spectators(app, observations)
        await asyncio.sleep(config.tick_ms / 1000.0)


async def broadcast_spectators(app: FastAPI, observations: dict[int, dict[str, Any]]) -> None:
    state: GameState = app.state.game_state
    spectators = list(app.state.spectators)
    for spectator in spectators:
        ws: WebSocket = spectator["ws"]
        try:
            if spectator.get("omniscient"):
                payload = state.observation_omniscient()
            else:
                player_id = spectator.get("player_id")
                payload = observations.get(player_id, state.observation_omniscient())
            await ws.send_json({"type": "state", "payload": payload})
        except Exception:
            try:
                await ws.close()
            except Exception:
                pass
            if spectator in app.state.spectators:
                app.state.spectators.remove(spectator)


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Open Forest game server")
    parser.add_argument("--config", default=None, help="Path to config.json")
    parser.add_argument("--players", type=int, default=4, help="Number of players")
    parser.add_argument("--http-bot", action="append", default=[], help="HTTP bot base URL")
    parser.add_argument("--replay", default=None, help="Replay JSONL output path")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app_instance = create_app(args.config, args.players, args.http_bot, args.replay)
    uvicorn.run(app_instance, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
