/**
 * Strategy domain canonical events
 * @deprecated chưa có producer/consumer canonical — không dùng cho BusinessEventEnvelope
 */
export const EXPERIMENT_CREATED = "experiment.created";
export const EVIDENCE_RECORDED = "evidence.recorded";
export const GATE_EVALUATED = "gate.evaluated";
export const DECISION_RECORDED = "decision.recorded";

export const VENTURE_STAGE_CHANGED = "venture.stage.changed.v1";
export const PROJECT_PHASE_CHANGED = "project.phase.changed.v1";
export const LEGAL_STATUS_CHANGED = "legal.status.changed.v1";
export const LEGAL_OBLIGATION_CREATED = "legal.obligation.created.v1";
export const FINANCE_ACCOUNTING_DOCUMENT_CONFIRMED = "finance.accounting_document.confirmed.v1";
export const FINANCE_BANK_TRANSACTION_INGESTED = "finance.bank_transaction.ingested";
export const NEXT_BEST_ACTION_ACCEPTED = "strategy.next_best_action.accepted.v1";
export const WEEKLY_REVIEW_COMPLETED = "operations.weekly_review.completed.v1";
export const PROJECT_OPERATING_SETUP_ACTIVATED = "project.operating_setup.activated.v1";

export * from "./events/envelope";


export * from "./events/event-types";


