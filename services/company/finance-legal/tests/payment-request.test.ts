// F4 (docs/superpowers/plans/2026-09-05-business-agents-finance.md) — state
// machine đề nghị chi. Test qua handler HTTP thật (không gọi service trần)
// để đúng đường thật founder/agent sẽ dùng, theo pattern đã có ở
// legal-obligation-lifecycle.test.ts (IA18).
import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import {
  createPaymentRequest,
  updatePaymentRequest,
  submitPaymentRequest,
  approvePaymentRequest,
  rejectPaymentRequest,
  cancelPaymentRequest,
  reportPaymentTransfer,
  getPaymentRequest,
} from "../handlers/payment-request.handler";

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

function baseInput(legalEntityId: string, idempotencyKey: string) {
  return {
    legalEntityId,
    amountMinor: "1500000",
    currency: "VND",
    beneficiaryBankBin: "970415",
    beneficiaryAccountNumber: "123456789",
    beneficiaryName: "NHA CUNG CAP",
    purpose: "Phi dich vu onboarding",
    idempotencyKey,
  };
}

describe("F4 — payment request state machine", () => {
  it("creates a DRAFT request and is idempotent on the same idempotencyKey", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("PR Create Ws");

    const created = await createPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      ...baseInput(legalEntityId, "req-idem-1"),
    });

    expect(created.approvalState).toBe("DRAFT");
    expect(created.settlementState).toBe("UNPAID");
    expect(created.amountMinor).toBe("1500000");
    expect(created.version).toBe(1);

    // Gọi lại với CÙNG idempotencyKey — không tạo request thứ hai.
    const repeated = await createPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      ...baseInput(legalEntityId, "req-idem-1"),
    });
    expect(repeated.id).toBe(created.id);
  });

  it("rejects a non-positive amount", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("PR NonPositive Ws");

    await expect(
      createPaymentRequest({
        authorization,
        workspaceId: session.workspaceId,
        ...baseInput(legalEntityId, "req-neg-1"),
        amountMinor: "0",
      })
    ).rejects.toThrow(/positive/i);
  });

  it("full happy path: DRAFT -> SUBMITTED -> APPROVED -> report-transfer REPORTED, never auto PAID", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("PR Happy Path Ws");

    const created = await createPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      ...baseInput(legalEntityId, "req-happy-1"),
    });

    const submitted = await submitPaymentRequest({
      id: created.id,
      expectedVersion: created.version,
      authorization,
      workspaceId: session.workspaceId,
    });
    expect(submitted.approvalState).toBe("SUBMITTED");

    const approved = await approvePaymentRequest({
      id: created.id,
      expectedVersion: submitted.version,
      authorization,
      workspaceId: session.workspaceId,
    });
    expect(approved.approvalState).toBe("APPROVED");
    // Tạo QR (chưa xây) vẫn phải giữ UNPAID — APPROVED không đồng nghĩa đã trả.
    expect(approved.settlementState).toBe("UNPAID");
    expect(approved.approvalHash).toBeTruthy();
    expect(approved.approvedVersion).toBe(approved.version);

    const reported = await reportPaymentTransfer({
      id: created.id,
      expectedVersion: approved.version,
      authorization,
      workspaceId: session.workspaceId,
    });
    // Founder tự báo đã chuyển — chỉ REPORTED, KHÔNG tự chuyển thành PAID
    // (đó là việc của payment-allocation khớp bank_transaction thật).
    expect(reported.settlementState).toBe("REPORTED");
    expect(reported.approvalState).toBe("APPROVED");
  });

  it("rejects an invalid transition (approve directly from DRAFT, skipping SUBMITTED)", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("PR Invalid Transition Ws");

    const created = await createPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      ...baseInput(legalEntityId, "req-invalid-1"),
    });

    await expect(
      approvePaymentRequest({
        id: created.id,
        expectedVersion: created.version,
        authorization,
        workspaceId: session.workspaceId,
      })
    ).rejects.toThrow(/Invalid payment request transition/);
  });

  it("enforces CAS on update — stale expectedVersion is rejected", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("PR CAS Ws");

    const created = await createPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      ...baseInput(legalEntityId, "req-cas-1"),
    });

    await updatePaymentRequest({
      id: created.id,
      expectedVersion: created.version,
      authorization,
      workspaceId: session.workspaceId,
      purpose: "Updated purpose",
    });

    // Sửa lần 2 vẫn dùng version CŨ (1) — phải bị từ chối vì đã có ai đó
    // (chính request trên) cập nhật lên version 2 rồi.
    await expect(
      updatePaymentRequest({
        id: created.id,
        expectedVersion: created.version,
        authorization,
        workspaceId: session.workspaceId,
        purpose: "Second update racing on stale version",
      })
    ).rejects.toMatchObject({ code: "CONCURRENT_MODIFICATION" });
  });

  it("invalidates a stale approval when beneficiary/amount is edited after APPROVED (reverts to DRAFT)", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("PR Stale Approval Ws");

    const created = await createPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      ...baseInput(legalEntityId, "req-stale-approval-1"),
    });
    const submitted = await submitPaymentRequest({
      id: created.id,
      expectedVersion: created.version,
      authorization,
      workspaceId: session.workspaceId,
    });
    const approved = await approvePaymentRequest({
      id: created.id,
      expectedVersion: submitted.version,
      authorization,
      workspaceId: session.workspaceId,
    });
    expect(approved.approvalState).toBe("APPROVED");

    // Sửa amount sau khi đã duyệt — proof cũ (approvalHash) phải hết hiệu
    // lực, không được âm thầm giữ nguyên APPROVED cho số tiền MỚI chưa ai
    // duyệt.
    const edited = await updatePaymentRequest({
      id: created.id,
      expectedVersion: approved.version,
      authorization,
      workspaceId: session.workspaceId,
      amountMinor: "9999999",
    });

    expect(edited.approvalState).toBe("DRAFT");
    expect(edited.approvalHash).toBeNull();
    expect(edited.approvedVersion).toBeNull();
    expect(edited.amountMinor).toBe("9999999");

    // report-transfer trên request đã quay lại DRAFT phải bị từ chối — proof
    // duyệt không còn hợp lệ cho số tiền mới.
    await expect(
      reportPaymentTransfer({
        id: created.id,
        expectedVersion: edited.version,
        authorization,
        workspaceId: session.workspaceId,
      })
    ).rejects.toThrow(/not APPROVED/);
  });

  it("rejects a SUBMITTED request with a reason, and rejecting without a reason is refused", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("PR Reject Ws");

    const created = await createPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      ...baseInput(legalEntityId, "req-reject-1"),
    });
    const submitted = await submitPaymentRequest({
      id: created.id,
      expectedVersion: created.version,
      authorization,
      workspaceId: session.workspaceId,
    });

    await expect(
      rejectPaymentRequest({
        id: created.id,
        expectedVersion: submitted.version,
        authorization,
        workspaceId: session.workspaceId,
        reason: "",
      })
    ).rejects.toThrow(/reason/i);

    const rejected = await rejectPaymentRequest({
      id: created.id,
      expectedVersion: submitted.version,
      authorization,
      workspaceId: session.workspaceId,
      reason: "Beneficiary bank account could not be verified",
    });
    expect(rejected.approvalState).toBe("REJECTED");
  });

  it("cancels a DRAFT/SUBMITTED/APPROVED request but refuses once settlement has been reported", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("PR Cancel Ws");

    const created = await createPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      ...baseInput(legalEntityId, "req-cancel-1"),
    });
    const submitted = await submitPaymentRequest({
      id: created.id,
      expectedVersion: created.version,
      authorization,
      workspaceId: session.workspaceId,
    });
    const approved = await approvePaymentRequest({
      id: created.id,
      expectedVersion: submitted.version,
      authorization,
      workspaceId: session.workspaceId,
    });
    const reported = await reportPaymentTransfer({
      id: created.id,
      expectedVersion: approved.version,
      authorization,
      workspaceId: session.workspaceId,
    });

    // Đã REPORTED (coi như tiền đã gửi thật) — không được "cancel" để xoá
    // dấu vết giao dịch đã xảy ra.
    await expect(
      cancelPaymentRequest({
        id: created.id,
        expectedVersion: reported.version,
        authorization,
        workspaceId: session.workspaceId,
      })
    ).rejects.toThrow(/settlement has started/);

    // Nhưng 1 request KHÁC vẫn còn UNPAID ở DRAFT thì cancel được bình thường.
    const other = await createPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      ...baseInput(legalEntityId, "req-cancel-2"),
    });
    const cancelled = await cancelPaymentRequest({
      id: other.id,
      expectedVersion: other.version,
      authorization,
      workspaceId: session.workspaceId,
    });
    expect(cancelled.approvalState).toBe("CANCELLED");
  });

  it("denies creating a payment request for a member with no finance authority (fail-closed, not founder default-allow)", async () => {
    // role mặc định của createTestSession (không truyền role) là "admin",
    // KHÔNG nằm trong ["founder","co-founder"] và không có role assignment
    // nào — phải bị DENY, không được âm thầm cho qua.
    const session = await createTestSession({ displayName: "PR No Authority Ws" });
    const entity = await createLegalEntityProfile({
      workspaceId: BigInt(session.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });

    await expect(
      createPaymentRequest({
        authorization: `Bearer ${session.accessToken}`,
        workspaceId: session.workspaceId,
        ...baseInput(entity.id, "req-no-authority-1"),
      })
    ).rejects.toThrow(/Permission denied/);
  });

  it("get returns the persisted request, not a client-fabricated view", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("PR Get Ws");

    const created = await createPaymentRequest({
      authorization,
      workspaceId: session.workspaceId,
      ...baseInput(legalEntityId, "req-get-1"),
    });

    const fetched = await getPaymentRequest({
      id: created.id,
      authorization,
      workspaceId: session.workspaceId,
    });
    expect(fetched.id).toBe(created.id);
    expect(fetched.beneficiaryName).toBe("NHA CUNG CAP");
  });
});
