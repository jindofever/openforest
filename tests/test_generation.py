from server.engine import GameState
from server.models import MatchConfig


def build_config(seed: int) -> MatchConfig:
    return MatchConfig(
        seed=seed,
        tick_ms=500,
        match_ticks=10,
        planet_count=1200,
        artifact_count=5,
        max_actions_per_tick=5,
        speed_const=0.08,
        capture_threshold_fraction=0.15,
        defense_multiplier=0.2,
        ping_ttl_ticks=3,
        ping_jitter=0.03,
        ping_base_radius=0.05,
        ping_base_strength=0.4,
        artifact_ping_radius=0.08,
        artifact_ping_strength=0.25,
        artifact_points_per_tick=1.5,
        score_top_n=10,
        commit_timeout_ms=200,
        reveal_timeout_ms=200,
        player_home_min_distance=0.7,
    )


def test_planet_generation_deterministic() -> None:
    config = build_config(42)
    state_a = GameState(config, ["A", "B"])
    state_b = GameState(config, ["A", "B"])

    sample_a = [(p.x, p.y, p.level) for p in state_a.planets[:10]]
    sample_b = [(p.x, p.y, p.level) for p in state_b.planets[:10]]
    assert sample_a == sample_b


def test_planet_generation_seed_variation() -> None:
    state_a = GameState(build_config(42), ["A", "B"])
    state_b = GameState(build_config(43), ["A", "B"])
    sample_a = [(p.x, p.y, p.level) for p in state_a.planets[:5]]
    sample_b = [(p.x, p.y, p.level) for p in state_b.planets[:5]]
    assert sample_a != sample_b
