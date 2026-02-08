import "./style.css";

type Observation = {
  tick: number;
  player_id: number | null;
  planets: Array<Record<string, any>>;
  fleets: Array<Record<string, any>>;
  pings: Array<Record<string, any>>;
  scores: Array<Record<string, any>>;
  max_actions: number;
  match_ticks?: number;
  tick_ms?: number;
};

const canvas = document.getElementById("map") as HTMLCanvasElement;
const ctx = canvas.getContext("2d")!;
const tickEl = document.getElementById("tick")!;
const remainingEl = document.getElementById("remaining")!;
const scoreboardEl = document.getElementById("scoreboard")!;
const playerSelect = document.getElementById("player-select") as HTMLSelectElement;
const omniscientToggle = document.getElementById("omniscient") as HTMLInputElement;

let latest: Observation | null = null;
let matchTicks = 2400;

function resize() {
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.floor(rect.width * window.devicePixelRatio);
  canvas.height = Math.floor(rect.height * window.devicePixelRatio);
}

window.addEventListener("resize", resize);
resize();

function toScreen(x: number, y: number) {
  const padding = 24 * window.devicePixelRatio;
  const width = canvas.width - padding * 2;
  const height = canvas.height - padding * 2;
  const sx = padding + ((x + 1) / 2) * width;
  const sy = padding + ((1 - (y + 1) / 2)) * height;
  return { x: sx, y: sy };
}

function render() {
  requestAnimationFrame(render);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!latest) {
    return;
  }

  for (const ping of latest.pings ?? []) {
    const pos = toScreen(ping.x, ping.y);
    ctx.beginPath();
    ctx.strokeStyle = `rgba(30, 143, 111, ${0.2 + ping.strength * 0.2})`;
    ctx.lineWidth = 2;
    ctx.arc(pos.x, pos.y, ping.radius * canvas.width * 0.25, 0, Math.PI * 2);
    ctx.stroke();
  }

  for (const fleet of latest.fleets ?? []) {
    const pos = toScreen(fleet.x, fleet.y);
    ctx.beginPath();
    ctx.fillStyle = fleet.owner === latest.player_id ? "#1e8f6f" : "#e3745b";
    ctx.arc(pos.x, pos.y, 3 * window.devicePixelRatio, 0, Math.PI * 2);
    ctx.fill();
  }

  for (const planet of latest.planets ?? []) {
    const pos = toScreen(planet.x, planet.y);
    const isOwned = planet.owner === latest.player_id;
    const isNeutral = planet.owner === null || planet.owner === undefined;
    const isStale = planet.visibility === "stale";
    const baseRadius = 4 + planet.level * 0.6;
    const radius = baseRadius * window.devicePixelRatio;

    ctx.beginPath();
    if (isNeutral) {
      ctx.fillStyle = `rgba(183, 196, 191, ${isStale ? 0.25 : 0.8})`;
    } else if (isOwned) {
      ctx.fillStyle = `rgba(30, 143, 111, ${isStale ? 0.3 : 0.9})`;
    } else {
      ctx.fillStyle = `rgba(227, 116, 91, ${isStale ? 0.25 : 0.85})`;
    }
    ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
    ctx.fill();

    if (planet.is_artifact) {
      ctx.beginPath();
      ctx.strokeStyle = `rgba(245, 198, 115, ${isStale ? 0.3 : 0.8})`;
      ctx.lineWidth = 2;
      ctx.arc(pos.x, pos.y, radius + 4, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
}

function updateScoreboard(scores: Array<Record<string, any>>) {
  scoreboardEl.innerHTML = "";
  scores
    .slice()
    .sort((a, b) => b.score - a.score)
    .forEach((player) => {
      const row = document.createElement("div");
      row.className = "score-row";
      row.innerHTML = `
        <div class="score-main">
          <span>${player.name}</span>
          <strong>${player.score.toFixed(1)}</strong>
        </div>
        <div class="score-meta">
          <span>T ${player.territory_score.toFixed(1)}</span>
          <span>A ${player.artifact_score.toFixed(1)}</span>
        </div>
      `;
      scoreboardEl.appendChild(row);
    });

  if (!playerSelect.options.length) {
    const omniscientOption = document.createElement("option");
    omniscientOption.value = "";
    omniscientOption.textContent = "Spectator";
    playerSelect.appendChild(omniscientOption);
    scores.forEach((player) => {
      const option = document.createElement("option");
      option.value = String(player.id);
      option.textContent = player.name;
      playerSelect.appendChild(option);
    });
  }
}

function connect() {
  const ws = new WebSocket("ws://localhost:8000/ws/spectator");

  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "state") {
      latest = message.payload as Observation;
      tickEl.textContent = String(latest.tick ?? 0);
      matchTicks = latest.match_ticks ?? matchTicks;
      remainingEl.textContent = String(Math.max(0, matchTicks - latest.tick));
      updateScoreboard(latest.scores ?? []);
    }
  });

  function sendPerspective() {
    const omniscient = omniscientToggle.checked;
    const selected = playerSelect.value;
    ws.send(
      JSON.stringify({
        type: "set_perspective",
        omniscient,
        player_id: selected ? Number(selected) : null,
      })
    );
  }

  omniscientToggle.addEventListener("change", sendPerspective);
  playerSelect.addEventListener("change", () => {
    omniscientToggle.checked = playerSelect.value === "";
    sendPerspective();
  });
}

connect();
render();
