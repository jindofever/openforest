import http from "http";
import crypto from "crypto";
import { commitHash } from "./commit";

export type BotFn = (observation: Record<string, unknown>) => Array<Record<string, unknown>>;

export function createHttpServer(botFn: BotFn): http.Server {
  const pending = new Map<number, { actions: Array<Record<string, unknown>>; nonce: string }>();

  return http.createServer((req, res) => {
    if (req.method !== "POST" || req.url !== "/act") {
      res.statusCode = 404;
      res.end();
      return;
    }
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
    });
    req.on("end", () => {
      try {
        const payload = JSON.parse(body || "{}");
        const phase = payload.phase;
        const tick = Number(payload.tick ?? 0);
        if (phase === "commit") {
          const observation = payload.observation ?? {};
          const actions = botFn(observation);
          const nonce = crypto.randomBytes(8).toString("hex");
          pending.set(tick, { actions, nonce });
          const commit = commitHash(actions, nonce);
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ commit }));
          return;
        }
        if (phase === "reveal") {
          const stored = pending.get(tick) ?? { actions: [], nonce: "" };
          pending.delete(tick);
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ actions: stored.actions, nonce: stored.nonce }));
          return;
        }
        res.statusCode = 400;
        res.end(JSON.stringify({ error: "unknown_phase" }));
      } catch (err) {
        res.statusCode = 400;
        res.end(JSON.stringify({ error: "invalid_json" }));
      }
    });
  });
}
