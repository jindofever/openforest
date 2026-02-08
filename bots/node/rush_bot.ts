import { runStdio } from "../../sdks/node/src/index";

runStdio((observation) => {
  const playerId = observation.player_id as number | null;
  const planets = (observation.planets ?? []) as Array<Record<string, any>>;
  const owned = planets.filter((p) => p.owner === playerId);
  const targets = planets.filter((p) => p.owner !== null && p.owner !== playerId);
  const neutrals = planets.filter((p) => p.owner === null);

  if (!owned.length) {
    return [];
  }
  const source = owned.reduce((best, p) => (p.energy > best.energy ? p : best), owned[0]);
  const pool = targets.length ? targets : neutrals;
  if (!pool.length) {
    return [];
  }
  const target = pool.reduce((best, p) => {
    const dist = (p.x - source.x) ** 2 + (p.y - source.y) ** 2;
    const bestDist = (best.x - source.x) ** 2 + (best.y - source.y) ** 2;
    return dist < bestDist ? p : best;
  }, pool[0]);

  return [
    {
      type: "send_fleet",
      from_id: source.id,
      to_id: target.id,
      energy: Math.max(10, source.energy * 0.6),
    },
  ];
});
