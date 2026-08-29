import { APIError } from "encore.dev/api";

export type DRStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "needs_information"
  | "approved"
  | "execution_pending"
  | "executed"
  | "rejected"
  | "expired";

export const DR_TRANSITIONS: Record<DRStatus, DRStatus[]> = {
  draft: ["submitted"],
  submitted: ["under_review", "rejected", "expired"],
  under_review: ["approved", "rejected", "needs_information", "expired"],
  needs_information: ["submitted", "expired"],
  approved: ["execution_pending", "expired"],
  execution_pending: ["executed", "rejected", "expired"],
  executed: [],
  rejected: [],
  expired: [],
};

export function assertDRTransition(from: DRStatus, to: DRStatus): void {
  const allowed = DR_TRANSITIONS[from];
  if (!allowed || !allowed.includes(to)) {
    throw APIError.invalidArgument(`invalid decision request status transition: ${from} -> ${to}`);
  }
}
