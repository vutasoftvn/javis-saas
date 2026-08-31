import { describe, expect, it } from "vitest";
import { RuntimeOverviewQuery } from "../application/runtime/runtime-overview-query";
import { RuntimeObservationPort } from "../application/runtime/runtime-observation.port";
import { RuntimeObservation } from "../domain/runtime-observation";

class MultiTenantObservationPort implements RuntimeObservationPort {
  private obs: { ws: string; obs: RuntimeObservation }[] = [];

  setObservation(workspaceId: string, obs: RuntimeObservation) {
    this.obs.push({ ws: workspaceId, obs });
  }

  async latest(
    workspaceId: string,
    sourceKind: RuntimeObservation["sourceKind"]
  ): Promise<RuntimeObservation | null> {
    const found = this.obs.find((item) => item.ws === workspaceId && item.obs.sourceKind === sourceKind);
    return found
      ? found.obs
      : {
          sourceKind,
          status: "not_observed",
          observedAt: null,
          evidenceRef: null,
        };
  }
}

describe("Workspace Runtime Tenant Isolation Tests", () => {
  it("never returns observation evidence from a different workspace", async () => {
    const port = new MultiTenantObservationPort();
    const query = new RuntimeOverviewQuery(port);

    port.setObservation("ws_tenant_A", {
      sourceKind: "company",
      status: "healthy",
      observedAt: new Date("2026-08-31T10:00:00.000Z"),
      evidenceRef: "operating.runtime_source_signals:secret_evidence_A",
    });

    const tenantAStatuses = await query.getSourceStatuses("ws_tenant_A");
    const tenantBStatuses = await query.getSourceStatuses("ws_tenant_B");

    expect(tenantAStatuses.find((s) => s.sourceKind === "company_db")?.evidenceRef).toBe(
      "operating.runtime_source_signals:secret_evidence_A"
    );

    // Tenant B sees not_observed and null evidence
    const tenantBCompany = tenantBStatuses.find((s) => s.sourceKind === "company_db");
    expect(tenantBCompany?.status).toBe("NOT_OBSERVED");
    expect(tenantBCompany?.evidenceRef).toBeNull();
  });
});
