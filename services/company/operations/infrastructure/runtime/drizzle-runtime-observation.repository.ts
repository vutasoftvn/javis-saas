import { and, eq, desc } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { RuntimeObservation } from "../../domain/runtime-observation";
import { RuntimeObservationPort } from "../../application/runtime/runtime-observation.port";

const { runtimeSourceSignals } = schema;

export class DrizzleRuntimeObservationRepository implements RuntimeObservationPort {
  async latest(
    workspaceId: string,
    sourceKind: RuntimeObservation["sourceKind"]
  ): Promise<RuntimeObservation | null> {
    const wsId = BigInt(workspaceId);

    const [row] = await db
      .select()
      .from(runtimeSourceSignals)
      .where(
        and(
          eq(runtimeSourceSignals.workspaceId, wsId),
          eq(runtimeSourceSignals.sourceKind, sourceKind)
        )
      )
      .orderBy(desc(runtimeSourceSignals.observedAt))
      .limit(1);

    if (!row) {
      return {
        sourceKind,
        status: "not_observed",
        observedAt: null,
        evidenceRef: null,
      };
    }

    let status: RuntimeObservation["status"] = "healthy";
    const stateUpper = (row.state || "").toUpperCase();
    if (stateUpper === "FAILED" || stateUpper === "ERROR" || stateUpper === "UNAVAILABLE") {
      status = "unavailable";
    } else if (stateUpper === "DEGRADED" || stateUpper === "WARNING" || stateUpper === "PAUSED") {
      status = "degraded";
    } else if (stateUpper === "OK" || stateUpper === "HEALTHY" || stateUpper === "RUNNING" || stateUpper === "ACTIVE") {
      status = "healthy";
    }

    return {
      sourceKind,
      status,
      observedAt: row.observedAt,
      evidenceRef: `operating.runtime_source_signals:${row.id}`,
    };
  }

  async listSourceSignals(workspaceId: string) {
    const wsId = BigInt(workspaceId);
    return db
      .select()
      .from(runtimeSourceSignals)
      .where(eq(runtimeSourceSignals.workspaceId, wsId))
      .orderBy(desc(runtimeSourceSignals.observedAt))
      .limit(50);
  }
}
