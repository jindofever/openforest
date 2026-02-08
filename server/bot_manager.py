from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi import WebSocket

from .utils import json_dumps, sha256_hex


class BotManager:
    def __init__(self, commit_timeout_ms: int, reveal_timeout_ms: int) -> None:
        self.commit_timeout = commit_timeout_ms / 1000.0
        self.reveal_timeout = reveal_timeout_ms / 1000.0
        self.ws_connections: dict[int, dict[str, Any]] = {}
        self.http_bots: dict[int, str] = {}
        self.pending_commits: dict[int, str] = {}

    def register_ws(self, player_id: int, websocket: WebSocket) -> None:
        self.ws_connections[player_id] = {"ws": websocket, "queue": asyncio.Queue()}

    def register_http(self, player_id: int, url: str) -> None:
        self.http_bots[player_id] = url.rstrip("/")

    async def commit_phase(self, tick: int, observations: dict[int, dict[str, Any]]) -> None:
        self.pending_commits = {}
        tasks = []
        for player_id, obs in observations.items():
            if player_id in self.ws_connections:
                tasks.append(self._commit_ws(player_id, obs, tick))
            elif player_id in self.http_bots:
                tasks.append(self._commit_http(player_id, obs, tick))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def reveal_phase(self, tick: int) -> dict[int, list[dict[str, Any]]]:
        actions_by_player: dict[int, list[dict[str, Any]]] = {}
        tasks = []
        for player_id in set(self.ws_connections.keys()) | set(self.http_bots.keys()):
            if player_id in self.ws_connections:
                tasks.append(self._reveal_ws(player_id, tick))
            elif player_id in self.http_bots:
                tasks.append(self._reveal_http(player_id, tick))
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, tuple):
                    player_id, actions = result
                    actions_by_player[player_id] = actions
        return actions_by_player

    async def _commit_ws(self, player_id: int, observation: dict[str, Any], tick: int) -> None:
        ws = self.ws_connections[player_id]["ws"]
        queue = self.ws_connections[player_id]["queue"]
        try:
            await ws.send_json({"type": "commit", "tick": tick, "observation": observation})
            data = await asyncio.wait_for(queue.get(), timeout=self.commit_timeout)
            if data.get("type") != "commit" or data.get("tick") != tick:
                return
            commit = data.get("commit")
            if isinstance(commit, str):
                self.pending_commits[player_id] = commit
        except Exception:
            return

    async def _commit_http(self, player_id: int, observation: dict[str, Any], tick: int) -> None:
        url = self.http_bots[player_id]
        payload = {"phase": "commit", "tick": tick, "observation": observation}
        try:
            async with httpx.AsyncClient(timeout=self.commit_timeout) as client:
                resp = await client.post(f"{url}/act", json=payload)
                data = resp.json()
            commit = data.get("commit")
            if isinstance(commit, str):
                self.pending_commits[player_id] = commit
        except Exception:
            return

    async def _reveal_ws(self, player_id: int, tick: int) -> tuple[int, list[dict[str, Any]]] | None:
        if player_id not in self.pending_commits:
            return None
        ws = self.ws_connections[player_id]["ws"]
        queue = self.ws_connections[player_id]["queue"]
        try:
            await ws.send_json({"type": "reveal", "tick": tick})
            data = await asyncio.wait_for(queue.get(), timeout=self.reveal_timeout)
            if data.get("type") != "reveal" or data.get("tick") != tick:
                return None
            actions = data.get("actions")
            nonce = data.get("nonce")
            if not isinstance(actions, list) or not isinstance(nonce, str):
                return None
            actions_json = json_dumps(actions)
            commit = sha256_hex(actions_json + nonce)
            if commit != self.pending_commits.get(player_id):
                return None
            return player_id, actions
        except Exception:
            return None

    async def _reveal_http(self, player_id: int, tick: int) -> tuple[int, list[dict[str, Any]]] | None:
        if player_id not in self.pending_commits:
            return None
        url = self.http_bots[player_id]
        payload = {"phase": "reveal", "tick": tick}
        try:
            async with httpx.AsyncClient(timeout=self.reveal_timeout) as client:
                resp = await client.post(f"{url}/act", json=payload)
                data = resp.json()
            actions = data.get("actions")
            nonce = data.get("nonce")
            if not isinstance(actions, list) or not isinstance(nonce, str):
                return None
            actions_json = json_dumps(actions)
            commit = sha256_hex(actions_json + nonce)
            if commit != self.pending_commits.get(player_id):
                return None
            return player_id, actions
        except Exception:
            return None
