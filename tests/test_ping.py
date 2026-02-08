from server.engine import GameState
from server.models import Fleet, MatchConfig
from server.utils import deterministic_rng


def build_config() -> MatchConfig:
    return MatchConfig(
        seed=7,
        tick_ms=500,
        match_ticks=10,
        planet_count=10,
        artifact_count=1,
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


def test_ping_deterministic() -> None:
    config = build_config()
    state = GameState(config, ["A", "B"])
    source = state.planets[0]
    fleet = Fleet(
        id=5,
        owner=0,
        source_id=source.id,
        dest_id=1,
        energy=40,
        launch_tick=0,
        total_ticks=1,
        ticks_remaining=1,
    )

    state._emit_fleet_ping(fleet)
    ping = state.pings[0]

    rng = deterministic_rng(config.seed, ["ping", state.tick, fleet.id])
    jitter_x = rng.uniform(-config.ping_jitter, config.ping_jitter)
    jitter_y = rng.uniform(-config.ping_jitter, config.ping_jitter)

    assert abs(ping.x - (source.x + jitter_x)) < 1e-9
    assert abs(ping.y - (source.y + jitter_y)) < 1e-9
