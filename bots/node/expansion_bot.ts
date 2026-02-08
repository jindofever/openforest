import { runStdio } from "../../sdks/node/src/index";

runStdio((observation) => {
  const playerId = observation.player_id as number | null;
  const planets = (observation.planets ?? []) as Array<Record<string, any>>;
  const owned = planets.filter((p) => p.owner === playerId);
  const neutrals = planets.filter((p) => p.owner === null);
  const actions: Array<Record<string, unknown>> = [];

  if (!owned.length) {
    return actions;
  }

  const maxActions = Number(observation.max_actions ?? 5);
  const sortedOwned = [...owned].sort((a, b) => b.energy - a.energy);

  for (const source of sortedOwned) {
    if (actions.length >= maxActions || !neutrals.length) {
      break;
    }
    if (source.energy < source.energy_cap * 0.5) {
      continue;
    }
    const target = neutrals.reduce((best, p) => {
      const dist = (p.x - source.x) ** 2 + (p.y - source.y) ** 2;
      const bestDist = (best.x - source.x) ** 2 + (best.y - source.y) ** 2;
      return dist < bestDist ? p : best;
    }, neutrals[0]);
    actions.push({
      type: "send_fleet",
      from_id: source.id,
      to_id: target.id,
      energy: Math.max(8, source.energy * 0.35),
    });
  }

  if (actions.length < maxActions) {
    const home = owned.reduce((best, p) => (p.energy_cap > best.energy_cap ? p : best), owned[0]);
    actions.push({ type: "upgrade", planet_id: home.id, upgrade: "energy" });
  }

  return actions;
});
