import { describe, expect, it } from "vitest";
import { RuntimeOverviewQuery } from "../application/runtime/runtime-overview-query";
import { RuntimeObservationPort } from "../application/runtime/runtime-observation.port";
import { RuntimeObservation } from "../domain/runtime-observation";

class StubObservationPort implements RuntimeObservationPort {
  private obs: RuntimeObservation[] = [];

  setObservation(obs: RuntimeObservation) {
    this.obs.push(obs);
  }

  async latest(
    workspaceId: string,
    sourceKind: RuntimeObservation["sourceKind"]
  ): Promise<RuntimeObservation | null> {
    return this.obs.find((o) => o.sourceKind === sourceKind) || {
      sourceKind,
      status: "not_observed",
      observedAt: null,
      evidenceRef: null,
    };
  }
}

describe("Workspace Runtime Observation Truth Tests", () => {
  it("returns not_observed with null timestamp and null evidenceRef when no signal exists", async () => {
    const port = new StubObservationPort();
    const query = new RuntimeOverviewQuery(port);

    const statuses = await query.getSourceStatuses("ws_empty");
    expect(statuses).toHaveLength(2);

    const companyStatus = statuses.find((s) => s.sourceKind === "company_db");
    expect(companyStatus?.status).toBe("NOT_OBSERVED");
    expect(companyStatus?.lastObservedAt).toBeNull();
    expect(companyStatus?.evidenceRef).toBeNull();
  });

  it("returns healthy with stored timestamp and durable evidenceRef when healthy signal observed", async () => {
    const port = new StubObservationPort();
    const date = new Date("2026-08-31T12:00:00.000Z");

    port.setObservation({
      sourceKind: "company",
      status: "healthy",
      observedAt: date,
      evidenceRef: "operating.runtime_source_signals:sig_101",
    });

    const query = new RuntimeOverviewQuery(port);
    const statuses = await query.getSourceStatuses("ws_active");

    const companyStatus = statuses.find((s) => s.sourceKind === "company_db");
    expect(companyStatus?.status).toBe("HEALTHY");
    expect(companyStatus?.lastObservedAt).toBe(date.toISOString());
    expect(companyStatus?.evidenceRef).toBe("operating.runtime_source_signals:sig_101");
  });

  it("returns degraded / unavailable when error or warning signal observed", async () => {
    const port = new StubObservationPort();
    const date = new Date("2026-08-31T12:05:00.000Z");

    port.setObservation({
      sourceKind: "agent",
      status: "unavailable",
      observedAt: date,
      evidenceRef: "operating.runtime_source_signals:sig_999",
    });

    const query = new RuntimeOverviewQuery(port);
    const statuses = await query.getSourceStatuses("ws_active");

    const agentStatus = statuses.find((s) => s.sourceKind === "agent_db");
    expect(agentStatus?.status).toBe("UNAVAILABLE");
    expect(agentStatus?.lastObservedAt).toBe(date.toISOString());
    expect(agentStatus?.evidenceRef).toBe("operating.runtime_source_signals:sig_999");
  });
});
