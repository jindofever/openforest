import hashlib
import json
import math
import random
from typing import Any, Iterable


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def deterministic_rng(seed: int, parts: Iterable[Any]) -> random.Random:
    hasher = hashlib.sha256()
    hasher.update(str(seed).encode("utf-8"))
    for part in parts:
        hasher.update(b":")
        hasher.update(str(part).encode("utf-8"))
    digest = hasher.hexdigest()
    seed_int = int(digest[:16], 16)
    return random.Random(seed_int)
