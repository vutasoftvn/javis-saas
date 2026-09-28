import { CronJob } from "encore.dev/cron";
import { api } from "encore.dev/api";
import { relayTick } from "./outbox-relay.service";
import { aiInitiativeRelayTick } from "../operations/services/ai-initiative-relay.service";

export const relayTickEndpoint = api(
  { method: "POST", expose: false, path: "/events/relay/tick" },
  async (): Promise<void> => {
    await relayTick();
    // Task 6/13 — ai.initiative.promoted.v1 has its own claim/target (see
    // ai-initiative-relay.service.ts docstring); one tick drives both relays
    // so callers (cron, and E2E tests via this same endpoint) don't need to
    // know there are two.
    await aiInitiativeRelayTick();
  }
);

const _ = new CronJob("outbox-relay", {
  title: "Local outbox relay tick",
  every: "1m",
  endpoint: relayTickEndpoint,
});
