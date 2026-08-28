import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  recordFinancialTransaction,
  getFinancialTransaction,
  approveFinancialTransaction,
} from "../handlers/financial-transaction.handler";
import {
  createObligation,
  getObligation,
  fulfillObligation,
} from "../handlers/legal-obligation.handler";
import {
  getFinancialTransactionService,
  approveFinancialTransactionService,
} from "../services/financial-transaction.service";
import {
  getObligationService,
  fulfillObligationService,
} from "../services/legal-obligation.service";

async function makeAuthedWorkspace(displayName: string, role = "founder") {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
    role,
  });
  const authorization = `Bearer ${user.accessToken}`;
  const ctx = await requireWorkspaceAccess(authorization, user.workspaceId);
  return { workspaceId: user.workspaceId, authorization, ctx, user };
}

describe("Finance-Legal Tenant Isolation & Query Scope", () => {
  it("FinancialTransaction: cross-workspace get and approve returns 404 at query layer", async () => {
    const wsA = await makeAuthedWorkspace("Tenant Iso Fin A", "founder");
    const wsB = await makeAuthedWorkspace("Tenant Iso Fin B", "founder");

    const txnB = await recordFinancialTransaction({
      workspaceId: wsB.workspaceId,
      transactionDate: "2026-01-20",
      description: "Large payout in B",
      amount: "50000000.00",
      direction: "OUT",
      authorization: wsB.authorization,
    });
    expect(txnB.approvalStatus).toBe("PENDING_APPROVAL");

    // wsA get fails
    await expect(getFinancialTransactionService(txnB.id, wsA.ctx)).rejects.toThrow(/not found/i);

    // wsB get succeeds
    const fetchedByB = await getFinancialTransactionService(txnB.id, wsB.ctx);
    expect(fetchedByB.id).toBe(txnB.id);

    // wsA approve fails with not found (even though wsA has founder role in workspace A)
    await expect(
      approveFinancialTransactionService({ id: txnB.id, ctx: wsA.ctx })
    ).rejects.toThrow(/not found/i);

    await expect(
      approveFinancialTransaction({
        id: txnB.id,
        workspaceId: wsA.workspaceId,
        authorization: wsA.authorization,
      })
    ).rejects.toThrow(/not found/i);

    // Verify record B is still PENDING_APPROVAL
    const stillPending = await getFinancialTransactionService(txnB.id, wsB.ctx);
    expect(stillPending.approvalStatus).toBe("PENDING_APPROVAL");
  });

  it("LegalObligation: cross-workspace get and fulfill returns 404 at query layer", async () => {
    const wsA = await makeAuthedWorkspace("Tenant Iso Legal A");
    const wsB = await makeAuthedWorkspace("Tenant Iso Legal B");

    const obB = await createObligation({
      workspaceId: wsB.workspaceId,
      title: "File quarterly tax for WS B",
      dueAt: "2026-03-31",
      authorization: wsB.authorization,
    });
    expect(obB.status).toBe("OPEN");

    // wsA get fails
    await expect(getObligationService(obB.id, wsA.ctx)).rejects.toThrow(/not found/i);

    // wsB get succeeds
    const fetchedByB = await getObligationService(obB.id, wsB.ctx);
    expect(fetchedByB.id).toBe(obB.id);

    // wsA fulfill fails
    await expect(fulfillObligationService(obB.id, wsA.ctx)).rejects.toThrow(/not found/i);
    await expect(
      fulfillObligation({
        id: obB.id,
        workspaceId: wsA.workspaceId,
        authorization: wsA.authorization,
      })
    ).rejects.toThrow(/not found/i);

    // Verify record B is still OPEN
    const stillOpen = await getObligationService(obB.id, wsB.ctx);
    expect(stillOpen.status).toBe("OPEN");
  });
});
