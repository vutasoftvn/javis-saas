import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, createSecondWorkspace, addMemberToWorkspace } from "../../tests/_helpers";
import { createProject, getProject } from "../../handlers/project.handler";
import {
  createMetricContract,
  updateMetricContract,
  publishMetricContractHandler,
  reviseMetricContractHandler,
  getMetricContract,
  listMetricContracts,
} from "../handlers/metric-contract.handler";

describe("Metric Contract Aggregate & Versioning (Task 1 / Tranche B2)", () => {
  it("enforces immutable published versions, explicit founder publishing, and tenant boundary", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();
    const memberA = await addMemberToWorkspace(wsA.workspaceId, "member");

    // 1. Create project in workspace A
    const projA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Metric Contract Test Project",
      lifecycleStage: "P3_BUILD_VALIDATE",
    });

    const validContractPayload = {
      projectId: projA.id,
      metricKey: "activation_rate",
      displayName: "Core Workflow Activation Rate",
      unit: "percentage",
      numeratorDefinition: "Users who complete step 3 within 24h",
      denominatorDefinition: "Total onboarded users in cohort",
      cohortDefinition: "Weekly signups in pilot program",
      sourceMapping: {
        system: "mixpanel",
        identifier: "event_activation_completed",
        aggregation: "count_distinct_users",
        window: "7d",
      },
      cadence: "weekly",
      freshUntil: new Date(Date.now() + 86400000 * 30).toISOString(),
      guardrail: "Min 20 users per cohort",
      ownerMemberId: wsA.userId,
      decisionUse: "Determine if pilot cohort achieves baseline workflow completion before G4 evaluation",
    };

    // 2. Reject empty denominator or missing owner
    await expect(
      createMetricContract({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        ...validContractPayload,
        denominatorDefinition: "",
      })
    ).rejects.toThrow(/denominatorDefinition is required/i);

    // 3. Reject forbidden SQL/credential in sourceMapping
    await expect(
      createMetricContract({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        ...validContractPayload,
        sourceMapping: {
          system: "mixpanel",
          identifier: "SELECT * FROM users; DROP TABLE users; --",
          aggregation: "count",
          window: "7d",
        },
      })
    ).rejects.toThrow(/forbidden|insecure/i);

    // 4. Create valid draft contract as founder (v1)
    const v1Draft = await createMetricContract({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      ...validContractPayload,
    });
    expect(v1Draft.version).toBe(1);
    expect(v1Draft.status).toBe("DRAFT");
    expect(v1Draft.metricKey).toBe("activation_rate");

    // 5. Update draft contract is allowed
    const v1Updated = await updateMetricContract({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: v1Draft.id,
      displayName: "Core Workflow Activation Rate (Updated)",
    });
    expect(v1Updated.displayName).toBe("Core Workflow Activation Rate (Updated)");

    // 6. Non-founder cannot publish contract
    await expect(
      publishMetricContractHandler({
        authorization: memberA.bearerToken,
        workspaceId: wsA.workspaceId,
        id: v1Draft.id,
        approvalRef: "APR-METRIC-1",
      })
    ).rejects.toThrow(/founder|admin|privilege/i);

    // 7. Publishing without approval ref fails
    await expect(
      publishMetricContractHandler({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        id: v1Draft.id,
        approvalRef: "",
      })
    ).rejects.toThrow(/approvalRef is required/i);

    // 8. Founder publishes contract v1
    const v1Published = await publishMetricContractHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: v1Draft.id,
      approvalRef: "APR-METRIC-1",
    });
    expect(v1Published.status).toBe("ACTIVE");
    expect(v1Published.approvalRef).toBe("APR-METRIC-1");
    expect(v1Published.publishedAt).toBeDefined();

    // 9. Patching published contract is rejected (immutable)
    await expect(
      updateMetricContract({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        id: v1Draft.id,
        unit: "USD",
      })
    ).rejects.toThrow(/immutable/i);

    // 10. Non-founder cannot revise contract
    await expect(
      reviseMetricContractHandler({
        authorization: memberA.bearerToken,
        workspaceId: wsA.workspaceId,
        id: v1Draft.id,
        cohortDefinition: "Paid enterprise accounts only",
      })
    ).rejects.toThrow(/founder|admin|privilege/i);

    // 11. Founder revises contract -> creates v2 (DRAFT)
    const v2Draft = await reviseMetricContractHandler({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: v1Draft.id,
      cohortDefinition: "Paid enterprise accounts only",
      changeRationale: "Narrow cohort to verified enterprise trial users",
    });
    expect(v2Draft.version).toBe(2);
    expect(v2Draft.status).toBe("DRAFT");
    expect(v2Draft.cohortDefinition).toBe("Paid enterprise accounts only");
    expect(v2Draft.metricKey).toBe("activation_rate");

    // Check v1 is still version 1 and ACTIVE
    const v1Check = await getMetricContract({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: v1Draft.id,
    });
    expect(v1Check.version).toBe(1);
    expect(v1Check.status).toBe("ACTIVE");

    // 12. Workspace B cannot access or modify Workspace A contract
    await expect(
      getMetricContract({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        id: v1Draft.id,
      })
    ).rejects.toThrow(/not found|không tồn tại/i);

    await expect(
      publishMetricContractHandler({
        authorization: wsB.bearerToken,
        workspaceId: wsB.workspaceId,
        id: v1Draft.id,
        approvalRef: "APR-B",
      })
    ).rejects.toThrow(/not found|không tồn tại/i);

    // 13. Invariant: Project stage remains unchanged (P3_BUILD_VALIDATE)
    const projAfter = await getProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      id: projA.id,
    });
    expect(projAfter.lifecycleStage).toBe("P3_BUILD_VALIDATE");

    // 14. List contracts
    const list = await listMetricContracts({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      projectId: projA.id,
    });
    expect(list.items.length).toBe(2); // v2 and v1
  });
});
