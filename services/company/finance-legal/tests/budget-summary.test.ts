import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { createProject } from "../../operations/handlers/project.handler";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import {
  createBudgetEnvelopeService,
  getBudgetSummary,
} from "../services/budget-summary.service";
import { createPaymentRequest, submitPaymentRequest, approvePaymentRequest } from "../handlers/payment-request.handler";

async function foundersSetup(displayName: string) {
  const session = await createTestSession({ role: "founder", displayName });
  const authorization = `Bearer ${session.accessToken}`;
  const entity = await createLegalEntityProfile({
    workspaceId: BigInt(session.workspaceId),
    entityType: "MICRO_ENTERPRISE",
  });
  const project = await createProject({
    authorization,
    workspaceId: session.workspaceId,
    title: "Budget test project",
  });
  const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
  return { session, authorization, ctx, legalEntityId: entity.id, projectId: project.id };
}

describe("budget-summary.service — computeProjectBudgetPosition / getBudgetSummary", () => {
  it("returns coverage=NO_ENVELOPE when no envelope covers the project", async () => {
    const { ctx, projectId } = await foundersSetup("Budget No Envelope Ws");

    const summary = await getBudgetSummary(ctx, projectId);
    expect(summary.coverage).toBe("NO_ENVELOPE");
  });

  it("computes actualPaid/committedUnpaid/forecastUnapproved correctly and does not subtract forecast from remaining", async () => {
    const { authorization, ctx, legalEntityId, projectId } = await foundersSetup("Budget Math Ws");

    await createBudgetEnvelopeService(ctx, {
      projectId,
      legalEntityId,
      currency: "VND",
      periodStart: "2026-01-01",
      periodEnd: "2026-12-31",
      limitMinor: "10000000",
    });

    // APPROVED, fully unpaid -> committedUnpaid = 2,000,000
    const approvedReq = await createPaymentRequest({
      authorization,
      workspaceId: ctx.workspaceId,
      legalEntityId,
      projectId,
      amountMinor: "2000000",
      currency: "VND",
      beneficiaryBankBin: "970415",
      beneficiaryAccountNumber: "111",
      beneficiaryName: "NCC A",
      purpose: "chi A",
      idempotencyKey: "budget-math-approved",
    });
    const submittedReq = await submitPaymentRequest({
      id: approvedReq.id, expectedVersion: approvedReq.version,
      authorization, workspaceId: ctx.workspaceId,
    });
    await approvePaymentRequest({
      id: submittedReq.id, expectedVersion: submittedReq.version,
      authorization, workspaceId: ctx.workspaceId,
    });

    // DRAFT (forecast only) -> forecastUnapproved = 1,000,000, must NOT reduce remaining
    await createPaymentRequest({
      authorization,
      workspaceId: ctx.workspaceId,
      legalEntityId,
      projectId,
      amountMinor: "1000000",
      currency: "VND",
      beneficiaryBankBin: "970415",
      beneficiaryAccountNumber: "222",
      beneficiaryName: "NCC B",
      purpose: "chi B (forecast)",
      idempotencyKey: "budget-math-forecast",
    });

    const summary = await getBudgetSummary(ctx, projectId);
    expect(summary.committedUnpaidMinor).toBe("2000000");
    expect(summary.forecastUnapprovedMinor).toBe("1000000");
    expect(summary.actualPaidMinor).toBe("0");
    expect(summary.remainingAfterCommitmentsMinor).toBe("8000000"); // 10,000,000 - 0 - 2,000,000
    expect(summary.coverage).toBe("COMPLETE");
  });
});
