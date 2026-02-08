# Open Forest

A deterministic, multi-agent RTS inspired by Dark Forest. Play bot-vs-bot matches under partial information with commit/reveal turns, ping noise, and artifact scoring.

## Repo Layout

- `server/` FastAPI authoritative game server + WebSocket protocol
- `ui/` Vite + Canvas spectator UI
- `sdks/python/` Python bot SDK (function/HTTP/stdio)
- `sdks/node/` Node bot SDK (TypeScript types + helpers)
- `bots/python/` Sample Python bots (4 strategies)
- `bots/node/` Sample Node bots (4 strategies)
- `runner/` Local subprocess match runner + CLI
- `tests/` Determinism/combat/ping/scoring tests

## Quickstart (macOS)

```bash
cd openforest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Start the Server

```bash
python -m server.app --players 4
```

### Run the Spectator UI

```bash
cd ui
npm install
npm run dev
```

Open `http://localhost:5173` in a browser.

### Run a Local Match (Subprocess Bots)

```bash
python runner/run_match.py --players 4 \
  --bot bots/python/random_bot.py \
  --bot bots/python/rush_bot.py \
  --bot bots/python/expansion_bot.py \
  --bot bots/python/turtle_bot.py
```

A replay will be written to `replays/` as JSONL.

## Bot Interfaces

### Python SDK (stdio)

```python
from openforest_sdk import run_stdio

def bot(observation):
    return [{"type": "scan", "x": 0.0, "y": 0.0, "radius": 0.3}]

if __name__ == "__main__":
    run_stdio(bot)
```

### Python SDK (HTTP)

```python
from openforest_sdk import create_http_app
import uvicorn

def bot(observation):
    return []

app = create_http_app(bot)
uvicorn.run(app, host="0.0.0.0", port=9001)
```

Start the server with:

```bash
python -m server.app --players 1 --http-bot http://localhost:9001
```

### Node SDK (stdio)

```ts
import { runStdio } from "../sdks/node/src/index";

runStdio((_observation) => {
  return [{ type: "scan", x: 0, y: 0, radius: 0.25 }];
});
```

## Protocol Summary

- **Commit phase:** bot receives observation and responds with `sha256(actions_json + nonce)`.
- **Reveal phase:** bot reveals `actions_json` and `nonce`.
- Invalid or missing reveals are ignored for that tick.

## Config

Edit `config.json` to tune tick timing, scoring, and ping behavior. Defaults match the requested rules:

- `tick_ms=500`
- `match_ticks=2400`
- 1200 planets, 5 artifacts
- scoring and ping constants

## Tests

```bash
pytest
```

## Tournament Notes

For tournaments, spawn multiple matches with different seeds via `runner/run_match.py --seed <n>` and archive `replays/*.jsonl`.
