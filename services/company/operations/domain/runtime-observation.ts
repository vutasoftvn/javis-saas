export interface RuntimeObservation {
  readonly sourceKind: "company" | "agent";
  readonly status: "healthy" | "degraded" | "unavailable" | "not_observed";
  readonly observedAt: Date | null;
  readonly evidenceRef: string | null;
}
