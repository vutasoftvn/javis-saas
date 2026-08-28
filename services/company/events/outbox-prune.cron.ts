import { CronJob } from "encore.dev/cron";
import { api } from "encore.dev/api";
import { pruneDeliveredOutbox } from "../shared/events/outbox.repository";

export const pruneTickEndpoint = api(
  { method: "POST", expose: false, path: "/events/prune/tick" },
  async (): Promise<{ prunedCount: number }> => {
    const days = Number(process.env.COSA_OUTBOX_RETENTION_DAYS || 30);
    const count = await pruneDeliveredOutbox(days);
    return { prunedCount: count };
  }
);

const _ = new CronJob("outbox-prune", {
  title: "Prune delivered outbox events older than retention period",
  every: "24h",
  endpoint: pruneTickEndpoint,
});
