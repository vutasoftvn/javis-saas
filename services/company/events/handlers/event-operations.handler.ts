import { Header } from "encore.dev/api";
import { listOutbox, retryOutbox, ListOutboxParams, RetryOutboxParams } from "../services/event-operations.service";

export interface ListOutboxRequest {
  workspaceId: string;
  status: "retryable" | "dead" | "pending" | "claimed" | "delivered";
  authorization?: Header<"Authorization">;
}

export async function listOutboxHandler(req: ListOutboxRequest) {
  return listOutbox({
    workspaceId: req.workspaceId,
    status: req.status,
    authorization: req.authorization,
  });
}

export interface RetryOutboxRequest {
  eventId: string;
  workspaceId: string;
  authorization?: Header<"Authorization">;
}

export async function retryOutboxHandler(req: RetryOutboxRequest) {
  return retryOutbox({
    eventId: req.eventId,
    workspaceId: req.workspaceId,
    authorization: req.authorization,
  });
}
