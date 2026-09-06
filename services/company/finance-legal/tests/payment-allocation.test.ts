// F4 phần 2 — khớp payment_requests với bank_transactions thật. Test qua
// handler HTTP thật, cùng pattern payment-request.test.ts.
import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { createPaymentRequest, submitPaymentRequest, approvePaymentRequest } from "../handlers/payment-request.handler";
import { createPaymentAllocation, reversePaymentAllocation } from "../handlers/payment-allocation.handler";

const { bankConnections, bankTransactions, paymentRequests } = schema;

async function foundersSetup(displayName: string) {
  const session = await createTestSession({ role: "founder", displayName });
  const entity = await createLegalEntityProfile({
    workspaceId: BigInt(session.workspaceId),
    entityType: "MICRO_ENTERPRISE",
  });
  return {
    session,
    authorization: `Bearer ${session.accessToken}`,
    legalEntityId: entity.id,
  };
}

async function insertOutboundBankTransaction(p: { workspaceId: bigint; amountDecimal: string; currency?: string }) {
  const connId = generateSnowflake();
  await db.insert(bankConnections).values({
    id: connId,
    workspaceId: p.workspaceId,
    provider: "manual",
  });

  const txnId = generateSnowflake();
  await db.insert(bankTransactions).values({
    id: txnId,
    workspaceId: p.workspaceId,
    bankConnectionId: connId,
    externalTransactionId: `txn_${txnId}`,
    postedAt: new Date(),
    amount: p.amountDecimal,
    currency: p.currency ?? "VND",
    direction: "OUT",
    description: "Chuyen khoan nha cung cap",
  });
  return txnId;
}

async function approvedPaymentRequest(p: {
  authorization: string;
  workspaceId: string;
  legalEntityId: string;
  amountMinor: string;
  idempotencyKey: string;
}) {
  const created = await createPaymentRequest({
    authorization: p.authorization,
    workspaceId: p.workspaceId,
    legalEntityId: p.legalEntityId,
    amountMinor: p.amountMinor,
    currency: "VND",
    beneficiaryBankBin: "970415",
    beneficiaryAccountNumber: "123456789",
    beneficiaryName: "NHA CUNG CAP",
    purpose: "Phi dich vu",
    idempotencyKey: p.idempotencyKey,
  });
  const submitted = await submitPaymentRequest({
    id: created.id,
    expectedVersion: created.version,
    authorization: p.authorization,
    workspaceId: p.workspaceId,
  });
  return approvePaymentRequest({
    id: created.id,
    expectedVersion: submitted.version,
    authorization: p.authorization,
    workspaceId: p.workspaceId,
  });
}

describe("F4 phần 2 — payment allocation (khớp bank_transaction thật)", () => {
  it("fully allocates a request against a matching bank transaction, marking settlement PAID", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("Alloc Full Ws");
    const wsId = BigInt(session.workspaceId);

    const approved = await approvedPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      legalEntityId,
      amountMinor: "1500000",
      idempotencyKey: "req-alloc-full-1",
    });
    const txnId = await insertOutboundBankTransaction({ workspaceId: wsId, amountDecimal: "1500000.00" });

    const allocation = await createPaymentAllocation({
      requestId: approved.id,
      bankTransactionId: String(txnId),
      amountMinor: "1500000",
      idempotencyKey: "alloc-full-1",
      authorization,
      workspaceId: session.workspaceId,
    });

    expect(allocation.status).toBe("ACTIVE");
    expect(allocation.amountMinor).toBe("1500000");

    const [reqRow] = await db.select().from(paymentRequests).where(eq(paymentRequests.id, BigInt(approved.id)));
    expect(reqRow!.settlementState).toBe("PAID");
  });

  it("supports partial allocation (500k + 1m across two allocations)", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("Alloc Partial Ws");
    const wsId = BigInt(session.workspaceId);

    const approved = await approvedPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      legalEntityId,
      amountMinor: "1500000",
      idempotencyKey: "req-alloc-partial-1",
    });
    const txnId = await insertOutboundBankTransaction({ workspaceId: wsId, amountDecimal: "1500000.00" });

    const first = await createPaymentAllocation({
      requestId: approved.id,
      bankTransactionId: String(txnId),
      amountMinor: "500000",
      idempotencyKey: "alloc-partial-a",
      authorization,
      workspaceId: session.workspaceId,
    });
    expect(first.status).toBe("ACTIVE");

    const [afterFirst] = await db.select().from(paymentRequests).where(eq(paymentRequests.id, BigInt(approved.id)));
    expect(afterFirst!.settlementState).toBe("PARTIAL");

    const second = await createPaymentAllocation({
      requestId: approved.id,
      bankTransactionId: String(txnId),
      amountMinor: "1000000",
      idempotencyKey: "alloc-partial-b",
      authorization,
      workspaceId: session.workspaceId,
    });
    expect(second.status).toBe("ACTIVE");

    const [afterSecond] = await db.select().from(paymentRequests).where(eq(paymentRequests.id, BigInt(approved.id)));
    expect(afterSecond!.settlementState).toBe("PAID");
  });

  it("rejects an allocation that would exceed the request remainder (ALLOCATION_EXCEEDED)", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("Alloc Exceed Request Ws");
    const wsId = BigInt(session.workspaceId);

    const approved = await approvedPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      legalEntityId,
      amountMinor: "1000000",
      idempotencyKey: "req-alloc-exceed-1",
    });
    const txnId = await insertOutboundBankTransaction({ workspaceId: wsId, amountDecimal: "5000000.00" });

    await expect(
      createPaymentAllocation({
        requestId: approved.id,
        bankTransactionId: String(txnId),
        amountMinor: "1000001",
        idempotencyKey: "alloc-exceed-1",
        authorization,
        workspaceId: session.workspaceId,
      })
    ).rejects.toMatchObject({ code: "ALLOCATION_EXCEEDED" });
  });

  it("rejects an allocation that would exceed the bank transaction's remaining balance", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("Alloc Exceed Bank Ws");
    const wsId = BigInt(session.workspaceId);

    const approved = await approvedPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      legalEntityId,
      amountMinor: "9000000",
      idempotencyKey: "req-alloc-exceed-bank-1",
    });
    const txnId = await insertOutboundBankTransaction({ workspaceId: wsId, amountDecimal: "1000000.00" });

    await expect(
      createPaymentAllocation({
        requestId: approved.id,
        bankTransactionId: String(txnId),
        amountMinor: "1000001",
        idempotencyKey: "alloc-exceed-bank-1",
        authorization,
        workspaceId: session.workspaceId,
      })
    ).rejects.toMatchObject({ code: "ALLOCATION_EXCEEDED" });
  });

  it("rejects allocating against a non-OUT (IN) bank transaction", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("Alloc Direction Ws");
    const wsId = BigInt(session.workspaceId);

    const approved = await approvedPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      legalEntityId,
      amountMinor: "1000000",
      idempotencyKey: "req-alloc-direction-1",
    });

    const connId = generateSnowflake();
    await db.insert(bankConnections).values({ id: connId, workspaceId: wsId, provider: "manual" });
    const txnId = generateSnowflake();
    await db.insert(bankTransactions).values({
      id: txnId,
      workspaceId: wsId,
      bankConnectionId: connId,
      externalTransactionId: `txn_in_${txnId}`,
      postedAt: new Date(),
      amount: "1000000.00",
      currency: "VND",
      direction: "IN",
      description: "Khach hang thanh toan",
    });

    await expect(
      createPaymentAllocation({
        requestId: approved.id,
        bankTransactionId: String(txnId),
        amountMinor: "1000000",
        idempotencyKey: "alloc-direction-1",
        authorization,
        workspaceId: session.workspaceId,
      })
    ).rejects.toThrow(/must be OUT/);
  });

  it("rejects allocating against a request that is not yet APPROVED", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("Alloc Not Approved Ws");
    const wsId = BigInt(session.workspaceId);

    const created = await createPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      legalEntityId,
      amountMinor: "1000000",
      currency: "VND",
      beneficiaryBankBin: "970415",
      beneficiaryAccountNumber: "123456789",
      beneficiaryName: "NHA CUNG CAP",
      purpose: "Phi dich vu",
      idempotencyKey: "req-alloc-notapproved-1",
    });
    const txnId = await insertOutboundBankTransaction({ workspaceId: wsId, amountDecimal: "1000000.00" });

    await expect(
      createPaymentAllocation({
        requestId: created.id,
        bankTransactionId: String(txnId),
        amountMinor: "1000000",
        idempotencyKey: "alloc-notapproved-1",
        authorization,
        workspaceId: session.workspaceId,
      })
    ).rejects.toThrow(/not APPROVED/);
  });

  it("is idempotent on the same idempotencyKey (retry does not double-allocate)", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("Alloc Idempotent Ws");
    const wsId = BigInt(session.workspaceId);

    const approved = await approvedPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      legalEntityId,
      amountMinor: "1500000",
      idempotencyKey: "req-alloc-idem-1",
    });
    const txnId = await insertOutboundBankTransaction({ workspaceId: wsId, amountDecimal: "1500000.00" });

    const first = await createPaymentAllocation({
      requestId: approved.id,
      bankTransactionId: String(txnId),
      amountMinor: "1500000",
      idempotencyKey: "alloc-idem-1",
      authorization,
      workspaceId: session.workspaceId,
    });
    const second = await createPaymentAllocation({
      requestId: approved.id,
      bankTransactionId: String(txnId),
      amountMinor: "1500000",
      idempotencyKey: "alloc-idem-1",
      authorization,
      workspaceId: session.workspaceId,
    });
    expect(second.id).toBe(first.id);
  });

  it("reverses an allocation without deleting it, and marks the request EXCEPTION when no allocation remains", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("Alloc Reverse Ws");
    const wsId = BigInt(session.workspaceId);

    const approved = await approvedPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      legalEntityId,
      amountMinor: "1500000",
      idempotencyKey: "req-alloc-reverse-1",
    });
    const txnId = await insertOutboundBankTransaction({ workspaceId: wsId, amountDecimal: "1500000.00" });

    const allocation = await createPaymentAllocation({
      requestId: approved.id,
      bankTransactionId: String(txnId),
      amountMinor: "1500000",
      idempotencyKey: "alloc-reverse-1",
      authorization,
      workspaceId: session.workspaceId,
    });

    await expect(
      reversePaymentAllocation({
        id: allocation.id,
        reason: "",
        authorization,
        workspaceId: session.workspaceId,
      })
    ).rejects.toThrow(/reason/i);

    const reversed = await reversePaymentAllocation({
      id: allocation.id,
      reason: "Wrongly matched — different beneficiary account",
      authorization,
      workspaceId: session.workspaceId,
    });
    expect(reversed.status).toBe("REVERSED");
    expect(reversed.reversedReason).toContain("Wrongly matched");

    const [reqRow] = await db.select().from(paymentRequests).where(eq(paymentRequests.id, BigInt(approved.id)));
    // Không âm thầm quay lại UNPAID (như thể chưa từng có giao dịch) — cần
    // review vì 1 khoản đã "khớp" giờ không còn khớp nữa.
    expect(reqRow!.settlementState).toBe("EXCEPTION");

    // Cùng 1 allocation không reverse được 2 lần.
    await expect(
      reversePaymentAllocation({
        id: allocation.id,
        reason: "Trying again",
        authorization,
        workspaceId: session.workspaceId,
      })
    ).rejects.toThrow(/already REVERSED/);
  });
});
