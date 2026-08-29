import { CronJob } from "encore.dev/cron";
import { api } from "encore.dev/api";
import { deliveryRelayTick } from "./delivery-relay.service";

export const deliveryRelayTickEndpoint = api(
  { method: "POST", expose: false, path: "/commercial/engagement/delivery-relay/tick" },
  async (): Promise<void> => {
    await deliveryRelayTick("engagement-delivery-relay");
  }
);

const _ = new CronJob("engagement-delivery-relay", {
  title: "Customer engagement outbound delivery relay tick",
  every: "1m",
  endpoint: deliveryRelayTickEndpoint,
});
