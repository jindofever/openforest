from server.engine import GameState
from server.models import MatchConfig


def build_config() -> MatchConfig:
    return MatchConfig(
        seed=9,
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


def test_scoring_updates() -> None:
    config = build_config()
    state = GameState(config, ["A", "B"])
    for planet in state.planets:
        planet.owner = None
        planet.is_artifact = False

    state.planets[0].owner = 0
    state.planets[0].energy_cap = 100
    state.planets[1].owner = 0
    state.planets[1].energy_cap = 80
    state.planets[2].owner = 0
    state.planets[2].energy_cap = 60
    state.planets[2].is_artifact = True

    state._update_scores()
    player = state.players[0]
    assert player.territory_score == (100 + 80 + 60) / 1000.0
    assert player.artifact_score == config.artifact_points_per_tick
    assert player.score == player.territory_score + player.artifact_score
