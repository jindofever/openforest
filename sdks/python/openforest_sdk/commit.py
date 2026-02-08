import json
import hashlib
from typing import Any


def canonical_actions(actions: list[dict[str, Any]]) -> str:
    return json.dumps(actions, sort_keys=True, separators=(",", ":"))


def commit_hash(actions: list[dict[str, Any]], nonce: str) -> str:
    payload = canonical_actions(actions) + nonce
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
