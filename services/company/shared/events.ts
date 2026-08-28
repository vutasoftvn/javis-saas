/**
 * Strategy domain canonical events
 * @deprecated chưa có producer/consumer canonical — không dùng cho BusinessEventEnvelope
 */
export const EXPERIMENT_CREATED = "experiment.created";
export const EVIDENCE_RECORDED = "evidence.recorded";
export const GATE_EVALUATED = "gate.evaluated";
export const DECISION_RECORDED = "decision.recorded";

export * from "./events/envelope";
export * from "./events/event-types";
