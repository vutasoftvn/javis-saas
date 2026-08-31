import { RuntimeObservation } from "../../domain/runtime-observation";

export interface ProjectedSourceStatus {
  readonly sourceKind: string;
  readonly plane: string;
  readonly status: "HEALTHY" | "DEGRADED" | "UNAVAILABLE" | "NOT_OBSERVED";
  readonly lastObservedAt: string | null;
  readonly evidenceRef: string | null;
}

export class RuntimeSignalProjector {
  static toSourceStatus(obs: RuntimeObservation): ProjectedSourceStatus {
    const plane = obs.sourceKind === "company" ? "company" : "agent";

    let statusUpper: ProjectedSourceStatus["status"] = "NOT_OBSERVED";
    if (obs.status === "healthy") statusUpper = "HEALTHY";
    else if (obs.status === "degraded") statusUpper = "DEGRADED";
    else if (obs.status === "unavailable") statusUpper = "UNAVAILABLE";

    return {
      sourceKind: obs.sourceKind === "company" ? "company_db" : "agent_db",
      plane,
      status: statusUpper,
      lastObservedAt: obs.observedAt ? obs.observedAt.toISOString() : null,
      evidenceRef: obs.evidenceRef,
    };
  }
}
