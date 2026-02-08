import readline from "readline";
import crypto from "crypto";
import { commitHash } from "./commit";

export type BotFn = (observation: Record<string, unknown>) => Array<Record<string, unknown>>;

export function runStdio(botFn: BotFn): void {
  const pending = new Map<number, { actions: Array<Record<string, unknown>>; nonce: string }>();
  const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });

  rl.on("line", (line) => {
    if (!line.trim()) {
      return;
    }
    const message = JSON.parse(line);
    const msgType = message.type;
    const tick = Number(message.tick ?? 0);

    if (msgType === "commit") {
      const observation = message.observation ?? {};
      const actions = botFn(observation);
      const nonce = crypto.randomBytes(8).toString("hex");
      pending.set(tick, { actions, nonce });
      const commit = commitHash(actions, nonce);
      const response = { type: "commit", tick, commit };
      process.stdout.write(JSON.stringify(response) + "\n");
    } else if (msgType === "reveal") {
      const stored = pending.get(tick) ?? { actions: [], nonce: "" };
      pending.delete(tick);
      const response = { type: "reveal", tick, actions: stored.actions, nonce: stored.nonce };
      process.stdout.write(JSON.stringify(response) + "\n");
    }
  });
}
