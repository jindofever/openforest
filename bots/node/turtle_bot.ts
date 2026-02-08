import { runStdio } from "../../sdks/node/src/index";

runStdio((observation) => {
  const playerId = observation.player_id as number | null;
  const planets = (observation.planets ?? []) as Array<Record<string, any>>;
  const owned = planets.filter((p) => p.owner === playerId);
  const actions: Array<Record<string, unknown>> = [];

  if (!owned.length) {
    return actions;
  }

  const maxActions = Number(observation.max_actions ?? 5);
  const home = owned.reduce((best, p) => (p.energy_cap > best.energy_cap ? p : best), owned[0]);

  actions.push({ type: "upgrade", planet_id: home.id, upgrade: "defense" });
  actions.push({ type: "upgrade", planet_id: home.id, upgrade: "sensor" });

  if (actions.length < maxActions) {
    actions.push({ type: "scan", x: home.x, y: home.y, radius: 0.35 });
  }

  if (home.energy > home.energy_cap * 0.7 && actions.length < maxActions) {
    const neutrals = planets.filter((p) => p.owner === null);
    if (neutrals.length) {
      const target = neutrals.reduce((best, p) => {
        const dist = (p.x - home.x) ** 2 + (p.y - home.y) ** 2;
        const bestDist = (best.x - home.x) ** 2 + (best.y - home.y) ** 2;
        return dist < bestDist ? p : best;
      }, neutrals[0]);
      actions.push({
        type: "send_fleet",
        from_id: home.id,
        to_id: target.id,
        energy: home.energy * 0.25,
      });
    }
  }

  return actions.slice(0, maxActions);
});
