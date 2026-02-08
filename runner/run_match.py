from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
from typing import Any

from server.engine import GameState
from server.models import MatchConfig
from server.replay import ReplayLogger
from server.utils import json_dumps, sha256_hex


class BotProcess:
    def __init__(self, path: str) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.queue: queue.Queue[str] = queue.Queue()
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            self.queue.put(line)

    def send(self, payload: dict[str, Any]) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def recv(self, timeout: float) -> dict[str, Any] | None:
        try:
            line = self.queue.get(timeout=timeout)
            return json.loads(line)
        except Exception:
            return None

    def close(self) -> None:
        try:
            self.proc.terminate()
        except Exception:
            pass


def load_config(path: str) -> MatchConfig:
    with open(path, "r", encoding="utf-8") as file:
        raw = json.load(file)
    return MatchConfig(**raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local match runner for Open Forest")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--players", type=int, default=4)
    parser.add_argument("--bot", action="append", default=[], help="Path to python bot script")
    parser.add_argument("--replay", default=None)
    args = parser.parse_args()

    config = load_config(os.path.abspath(args.config))
    if args.seed is not None:
        config.seed = args.seed
    player_names = [f"Bot {i}" for i in range(args.players)]
    state = GameState(config, player_names)

    bots: list[BotProcess] = []
    bot_paths = args.bot
    if not bot_paths:
        bot_paths = [os.path.join("bots", "python", "random_bot.py")]
    while len(bot_paths) < args.players:
        bot_paths.append(bot_paths[len(bot_paths) % len(bot_paths)])

    for path in bot_paths[: args.players]:
        bots.append(BotProcess(path))

    if args.replay is None:
        timestamp = int(time.time())
        args.replay = os.path.join("replays", f"local_match_{timestamp}.jsonl")
    replay = ReplayLogger(os.path.abspath(args.replay))

    observations = {player.id: state.observation_for_player(player.id) for player in state.players}

    for _ in range(config.match_ticks):
        commits: dict[int, str] = {}
        for player_id, bot in enumerate(bots):
            bot.send({"type": "commit", "tick": state.tick, "observation": observations[player_id]})

        for player_id, bot in enumerate(bots):
            reply = bot.recv(config.commit_timeout_ms / 1000.0)
            if reply and reply.get("type") == "commit" and reply.get("tick") == state.tick:
                commit = reply.get("commit")
                if isinstance(commit, str):
                    commits[player_id] = commit

        actions_by_player: dict[int, list[dict[str, Any]]] = {}
        for player_id, bot in enumerate(bots):
            if player_id not in commits:
                continue
            bot.send({"type": "reveal", "tick": state.tick})

        for player_id, bot in enumerate(bots):
            if player_id not in commits:
                continue
            reply = bot.recv(config.reveal_timeout_ms / 1000.0)
            if not reply or reply.get("type") != "reveal" or reply.get("tick") != state.tick:
                continue
            actions = reply.get("actions")
            nonce = reply.get("nonce")
            if not isinstance(actions, list) or not isinstance(nonce, str):
                continue
            if sha256_hex(json_dumps(actions) + nonce) != commits.get(player_id):
                continue
            actions_by_player[player_id] = actions

        snapshot = state.advance_tick(actions_by_player)
        processed_tick = snapshot["tick"]
        observations = {
            player.id: state.observation_for_player(player.id, snapshot["scans"].get(player.id, []))
            for player in state.players
        }
        replay.log_tick(processed_tick, snapshot, observations, actions_by_player)

    for bot in bots:
        bot.close()


if __name__ == "__main__":
    main()
