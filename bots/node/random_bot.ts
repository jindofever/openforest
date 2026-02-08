import { runStdio } from "../../sdks/node/src/index";

runStdio((observation) => {
  const playerId = observation.player_id as number | null;
  const planets = (observation.planets ?? []) as Array<Record<string, any>>;
  const owned = planets.filter((p) => p.owner === playerId);
  if (!owned.length) {
    return [];
  }
  const tick = Number(observation.tick ?? 0);
  const rand = (n: number) => Math.abs(Math.sin(tick + n));
  const actions: Array<Record<string, unknown>> = [];

  if (rand(1) < 0.4) {
    const source = owned[Math.floor(rand(2) * owned.length)];
    actions.push({
      type: "scan",
      x: source.x,
      y: source.y,
      radius: 0.25 + rand(3) * 0.2,
    });
  }

  const targets = planets.filter((p) => p.owner !== playerId);
  if (targets.length) {
    const source = owned[Math.floor(rand(4) * owned.length)];
    const target = targets[Math.floor(rand(5) * targets.length)];
    actions.push({
      type: "send_fleet",
      from_id: source.id,
      to_id: target.id,
      energy: Math.max(6, source.energy * 0.3),
    });
  }

  if (rand(6) < 0.3) {
    const source = owned[Math.floor(rand(7) * owned.length)];
    actions.push({
      type: "upgrade",
      planet_id: source.id,
      upgrade: "energy",
    });
  }

  return actions.slice(0, Number(observation.max_actions ?? 5));
});
