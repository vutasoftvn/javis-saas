import { CronJob } from "encore.dev/cron";
import { api } from "encore.dev/api";
import { relayTick } from "./outbox-relay.service";

export const relayTickEndpoint = api(
  { method: "POST", expose: false, path: "/events/relay/tick" },
  async (): Promise<void> => {
    await relayTick();
  }
);

const _ = new CronJob("outbox-relay", {
  title: "Local outbox relay tick",
  every: "1m",
  endpoint: relayTickEndpoint,
});
