import { APIError } from "encore.dev/api";

export type ThreadStatus =
  | "open" | "pending_customer" | "pending_internal" | "snoozed" | "resolved";

export type ThreadMode =
  | "human_assigned" | "team_queue" | "agent_autopilot" | "agent_copilot" | "awaiting_decision";

// Bảng chuyển hợp lệ. `reopened` KHÔNG phải persisted status — inbound message / lệnh reopen
// đưa `resolved` về `open`, và ghi outcome event riêng.
export const STATUS_TRANSITIONS: Record<ThreadStatus, ThreadStatus[]> = {
  open: ["pending_customer", "pending_internal", "snoozed", "resolved"],
  pending_customer: ["open", "pending_internal", "snoozed", "resolved"],
  pending_internal: ["open", "pending_customer", "snoozed", "resolved"],
  snoozed: ["open", "pending_customer", "pending_internal"],
  resolved: ["open"],
};

export function assertStatusTransition(from: ThreadStatus, to: ThreadStatus): void {
  const allowed = STATUS_TRANSITIONS[from];
  if (!allowed || !allowed.includes(to)) {
    throw APIError.invalidArgument(`invalid thread status transition: ${from} -> ${to}`);
  }
}
