import { api, Header } from "encore.dev/api";
import {
  listOutbox,
  retryOutbox,
  OutboxSummary,
} from "./services/event-operations.service";

export interface ListOutboxRequest {
  workspaceId: string;
  status: "retryable" | "dead" | "pending" | "claimed" | "delivered";
  authorization?: Header<"Authorization">;
}

export interface RetryOutboxRequest {
  eventId: string;
  workspaceId: string;
  authorization?: Header<"Authorization">;
}

export const listOutboxEndpoint = api(
  { method: "GET", expose: true, path: "/events/outbox" },
  async (req: ListOutboxRequest): Promise<{ items: OutboxSummary[] }> => {
    return listOutbox(req);
  }
);

export const retryOutboxEndpoint = api(
  { method: "POST", expose: true, path: "/events/outbox/:eventId/retry" },
  async (req: RetryOutboxRequest): Promise<{ status: "requeued" }> => {
    return retryOutbox(req);
  }
);
