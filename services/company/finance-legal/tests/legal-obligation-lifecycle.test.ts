import { describe, expect, it } from "vitest";
import {
  createObligationInstanceService,
  transitionObligationStatus,
  listObligationTransitions,
  listOpenObligations,
} from "../services/legal-obligation.service";
import {
  createWeeklyReviewService,
  aggregateWeeklyObligationsSummary,
} from "../../operations/strategy/services/weekly-review.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const {
  regulationSources,
  regulationVersions,
  legalObligationTemplates,
  legalEntityProfiles,
  legalObligationInstances,
  obligationTransitions,
} = schema;

describe("legal-obligation-lifecycle (Task L3)", () => {
  it("enforces CAS state transitions and mandates evidence for FULFILLED", async () => {
    const wsId = generateSnowflake();

    // 1. Create an obligation instance in OPEN status
    const instance = await createObligationInstanceService({
      workspaceId: wsId,
      source: "USER_CREATED",
      title: "Quarterly VAT Declaration",
      dueDate: "2026-04-30",
    });

    expect(instance.status).toBe("OPEN");

    // 2. Transition OPEN -> IN_PROGRESS
    const inProgress = await transitionObligationStatus({
      workspaceId: wsId,
      instanceId: BigInt(instance.id),
      expectedFromStatus: "OPEN",
      toStatus: "IN_PROGRESS",
      rationale: "Assigned to accountant for drafting",
    });

    expect(inProgress.status).toBe("IN_PROGRESS");

    // 3. Attempt IN_PROGRESS -> FULFILLED without evidence -> rejects
    await expect(
      transitionObligationStatus({
        workspaceId: wsId,
        instanceId: BigInt(instance.id),
        expectedFromStatus: "IN_PROGRESS",
        toStatus: "FULFILLED",
        rationale: "Done without paper",
      })
    ).rejects.toMatchObject({ code: "EVIDENCE_REQUIRED" });

    // 4. Transition IN_PROGRESS -> FULFILLED with evidenceRefs -> succeeds
    const fulfilled = await transitionObligationStatus({
      workspaceId: wsId,
      instanceId: BigInt(instance.id),
      expectedFromStatus: "IN_PROGRESS",
      toStatus: "FULFILLED",
      evidenceRefs: ["vault://tax/vat-2026-q1.pdf"],
      rationale: "Filing confirmed by General Department of Taxation",
    });

    expect(fulfilled.status).toBe("FULFILLED");
    expect(fulfilled.evidenceRefs).toEqual(["vault://tax/vat-2026-q1.pdf"]);

    // 5. CAS conflict check: trying to transition from OPEN when already FULFILLED -> rejects
    await expect(
      transitionObligationStatus({
        workspaceId: wsId,
        instanceId: BigInt(instance.id),
        expectedFromStatus: "OPEN",
        toStatus: "CANCELLED",
      })
    ).rejects.toMatchObject({ code: "CONCURRENT_MODIFICATION" });

    // 6. Verify audit trail in obligation_transitions
    const transitions = await listObligationTransitions(wsId, BigInt(instance.id));
    expect(transitions.length).toBe(2);

    const fulfillTransition = transitions.find((t) => t.toStatus === "FULFILLED");
    expect(fulfillTransition).toBeDefined();
    expect(fulfillTransition?.fromStatus).toBe("IN_PROGRESS");
    expect(fulfillTransition?.evidenceRefs).toContain("vault://tax/vat-2026-q1.pdf");
  });

  it("prevents duplicate obligation instances for the same template and period", async () => {
    const wsId = generateSnowflake();
    const entityId = generateSnowflake();

    // Create entity profile
    await db.insert(legalEntityProfiles).values({
      id: entityId,
      workspaceId: wsId,
      entityType: "LLC",
      status: "VERIFIED",
    });

    // Create template
    const sourceId = generateSnowflake();
    await db.insert(regulationSources).values({
      id: sourceId,
      sourceName: "Tax Admin Law",
      issuer: "National Assembly",
      number: `LAW-TAX-${Date.now()}`,
      url: "https://example.gov.vn/tax",
      layer: "CURRENT_LAW",
    });

    const verId = generateSnowflake();
    await db.insert(regulationVersions).values({
      id: verId,
      regulationSourceId: sourceId,
      version: "2026",
      effectiveFrom: "2026-01-01" as any,
    });

    const templateId = generateSnowflake();
    await db.insert(legalObligationTemplates).values({
      id: templateId,
      regulationVersionId: verId,
      title: "Quarterly CIT Advance Payment",
      typicalDueOffsetDays: 30,
    });

    // First creation
    const inst1 = await createObligationInstanceService({
      workspaceId: wsId,
      templateId,
      legalEntityProfileId: entityId,
      periodKey: "2026-Q1",
      source: "REGULATION_TEMPLATE",
      title: "Quarterly CIT Advance Payment",
      dueDate: "2026-04-30",
    });

    // Second creation with same (templateId, periodKey, legalEntityProfileId)
    const inst2 = await createObligationInstanceService({
      workspaceId: wsId,
      templateId,
      legalEntityProfileId: entityId,
      periodKey: "2026-Q1",
      source: "REGULATION_TEMPLATE",
      title: "Quarterly CIT Advance Payment",
      dueDate: "2026-04-30",
    });

    // Idempotent: returns existing instance ID
    expect(inst2.id).toBe(inst1.id);
  });

  it("aggregates active and overdue obligations into weekly review", async () => {
    const wsId = generateSnowflake();

    // 1. Create an OPEN obligation in past (overdue)
    await createObligationInstanceService({
      workspaceId: wsId,
      source: "USER_CREATED",
      title: "Overdue Annual Audit",
      dueDate: "2026-01-01",
    });

    // 2. Create an IN_PROGRESS obligation in future
    const inProgress = await createObligationInstanceService({
      workspaceId: wsId,
      source: "USER_CREATED",
      title: "Pending Trademark Renewal",
      dueDate: "2026-12-31",
    });
    await transitionObligationStatus({
      workspaceId: wsId,
      instanceId: BigInt(inProgress.id),
      toStatus: "IN_PROGRESS",
    });

    // 3. Create a FULFILLED obligation
    const fulfilled = await createObligationInstanceService({
      workspaceId: wsId,
      source: "USER_CREATED",
      title: "Business License Renewal",
      dueDate: "2026-02-01",
    });
    await transitionObligationStatus({
      workspaceId: wsId,
      instanceId: BigInt(fulfilled.id),
      toStatus: "FULFILLED",
      evidenceRefs: ["vault://license-renewed.pdf"],
    });

    // 4. Test aggregateWeeklyObligationsSummary
    const summary = await aggregateWeeklyObligationsSummary(wsId);
    expect(summary.openCount).toBe(1);
    expect(summary.inProgressCount).toBe(1);
    expect(summary.overdueCount).toBe(1);
    expect(summary.fulfilledCount).toBe(1);
    expect(summary.summaryText).toContain("2 active legal obligations (1 overdue, 1 fulfilled)");

    // 5. Create weekly review without obligationsSummary -> automatically aggregates
    const review = await createWeeklyReviewService({
      workspaceId: wsId,
      weekStartDate: "2026-09-01",
      summary: "Week 36 Strategy & Operations Review",
    });

    expect(review.obligationsSummary).toBe(summary.summaryText);
  });
});
