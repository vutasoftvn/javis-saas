import { describe, expect, it } from "vitest";
import {
  createLegalEntityProfile,
  listLegalEntityProfiles,
  requestVerification,
  applyVerification,
} from "../services/legal-entity-profile.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { db, schema } from "../db";
import { eq } from "drizzle-orm";

const REQUESTER = 1001n;
const APPROVER = 1002n;

describe("legal-entity-profile service", () => {
  it("creates profile with DRAFT status when no reg number", async () => {
    const wsId = generateSnowflake();
    const profile = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "MICRO_ENTERPRISE",
    });

    expect(profile.status).toBe("DRAFT");
    expect(profile.workspaceId).toBe(String(wsId));
  });

  it("creates profile with REGISTERED_UNVERIFIED when reg number provided", async () => {
    const wsId = generateSnowflake();
    const profile = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "MICRO_ENTERPRISE",
      registrationNumber: "0101234567",
      taxId: "0101234567",
    });

    expect(profile.status).toBe("REGISTERED_UNVERIFIED");
    expect(profile.registrationNumber).toBe("0101234567");
  });

  async function seedPendingProfile() {
    const wsId = generateSnowflake();
    const profile = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "LLC",
      registrationNumber: "0309998887",
    });
    return { wsId, profileId: BigInt(profile.id) };
  }

  it("M1 §6: durable approval — happy path with separation of duty", async () => {
    const { wsId, profileId } = await seedPendingProfile();

    const req = await requestVerification({
      profileId,
      workspaceId: wsId,
      actorMemberId: REQUESTER,
    });
    // approvalId là Snowflake string, KHÔNG còn prefix `appr_legal_`.
    expect(req.status).toBe("PENDING_APPROVAL");
    expect(() => BigInt(req.approvalId)).not.toThrow();
    expect(req.approvalId.startsWith("appr_legal_")).toBe(false);

    // Bản ghi approval thật sự nằm trong DB, PENDING, có expiry.
    const [row] = await db
      .select()
      .from(schema.legalVerificationApprovals)
      .where(eq(schema.legalVerificationApprovals.id, BigInt(req.approvalId)));
    expect(row.status).toBe("PENDING");
    expect(row.requestedBy).toBe(REQUESTER);
    expect(row.expiresAt.getTime()).toBeGreaterThan(Date.now());

    const verified = await applyVerification({
      profileId,
      workspaceId: wsId,
      approvalId: req.approvalId,
      approverMemberId: APPROVER,
    });
    expect(verified.status).toBe("VERIFIED");
    expect(verified.verifiedAt).toBeTruthy();

    const [after] = await db
      .select()
      .from(schema.legalVerificationApprovals)
      .where(eq(schema.legalVerificationApprovals.id, BigInt(req.approvalId)));
    expect(after.status).toBe("APPROVED");
    expect(after.approvedBy).toBe(APPROVER);
    expect(after.decidedAt).toBeTruthy();
  });

  it("M1 §6: forged `appr_legal_` prefix string is rejected", async () => {
    const { wsId, profileId } = await seedPendingProfile();
    await requestVerification({ profileId, workspaceId: wsId, actorMemberId: REQUESTER });

    await expect(
      applyVerification({
        profileId,
        workspaceId: wsId,
        approvalId: "appr_legal_AAAAAAAAAAAAAAAA",
        approverMemberId: APPROVER,
      })
    ).rejects.toThrow(/Invalid approval reference/);
  });

  it("M1 §6: approval from another workspace cannot be used (no cross-tenant)", async () => {
    const a = await seedPendingProfile();
    const b = await seedPendingProfile();

    const reqA = await requestVerification({
      profileId: a.profileId,
      workspaceId: a.wsId,
      actorMemberId: REQUESTER,
    });

    // Workspace B cố dùng approvalId của workspace A trên profile của B.
    await expect(
      applyVerification({
        profileId: b.profileId,
        workspaceId: b.wsId,
        approvalId: reqA.approvalId,
        approverMemberId: APPROVER,
      })
    ).rejects.toThrow(/not bound to this workspace/);
  });

  it("M1 §6: approval bound to a different legal entity is rejected", async () => {
    const wsId = generateSnowflake();
    const p1 = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "LLC",
      registrationNumber: "0300000001",
    });
    const p2 = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "LLC",
      registrationNumber: "0300000002",
    });
    const req = await requestVerification({
      profileId: BigInt(p1.id),
      workspaceId: wsId,
      actorMemberId: REQUESTER,
    });

    await expect(
      applyVerification({
        profileId: BigInt(p2.id),
        workspaceId: wsId,
        approvalId: req.approvalId,
        approverMemberId: APPROVER,
      })
    ).rejects.toThrow(/not bound to this legal entity/);
  });

  it("M1 §6: approver must differ from requester (SoD)", async () => {
    const { wsId, profileId } = await seedPendingProfile();
    const req = await requestVerification({
      profileId,
      workspaceId: wsId,
      actorMemberId: REQUESTER,
    });

    await expect(
      applyVerification({
        profileId,
        workspaceId: wsId,
        approvalId: req.approvalId,
        approverMemberId: REQUESTER,
      })
    ).rejects.toThrow(/separation of duty/);
  });

  it("M1 §6: expired approval is rejected and marked EXPIRED", async () => {
    const { wsId, profileId } = await seedPendingProfile();
    const req = await requestVerification({
      profileId,
      workspaceId: wsId,
      actorMemberId: REQUESTER,
    });
    // Ép hết hạn.
    await db
      .update(schema.legalVerificationApprovals)
      .set({ expiresAt: new Date(Date.now() - 1000) })
      .where(eq(schema.legalVerificationApprovals.id, BigInt(req.approvalId)));

    await expect(
      applyVerification({
        profileId,
        workspaceId: wsId,
        approvalId: req.approvalId,
        approverMemberId: APPROVER,
      })
    ).rejects.toThrow(/expired/i);

    const [row] = await db
      .select()
      .from(schema.legalVerificationApprovals)
      .where(eq(schema.legalVerificationApprovals.id, BigInt(req.approvalId)));
    expect(row.status).toBe("EXPIRED");
  });

  it("M1 §6: an already-APPROVED approval cannot be replayed", async () => {
    const { wsId, profileId } = await seedPendingProfile();
    const req = await requestVerification({
      profileId,
      workspaceId: wsId,
      actorMemberId: REQUESTER,
    });
    await applyVerification({
      profileId,
      workspaceId: wsId,
      approvalId: req.approvalId,
      approverMemberId: APPROVER,
    });

    await expect(
      applyVerification({
        profileId,
        workspaceId: wsId,
        approvalId: req.approvalId,
        approverMemberId: APPROVER,
      })
    ).rejects.toThrow(/not PENDING/);
  });

  it("M1 §6: requestVerification requires a registration number", async () => {
    const wsId = generateSnowflake();
    const profile = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "MICRO_ENTERPRISE",
    });
    await expect(
      requestVerification({
        profileId: BigInt(profile.id),
        workspaceId: wsId,
        actorMemberId: REQUESTER,
      })
    ).rejects.toThrow(/registration number/);
  });

  it("M1 §6: requestVerification for a profile in another workspace is notFound", async () => {
    const { wsId, profileId } = await seedPendingProfile();
    const otherWs = generateSnowflake();
    await expect(
      requestVerification({ profileId, workspaceId: otherWs, actorMemberId: REQUESTER })
    ).rejects.toThrow(/not found/i);
    // profile không bị đẩy sang VERIFIED bởi request thất bại.
    const rows = await listLegalEntityProfiles(wsId);
    expect(rows[0].status).toBe("REGISTERED_UNVERIFIED");
    expect(rows[0].status).not.toBe("VERIFIED");
  });

  it("M1 §6: repeated requestVerification reuses the same PENDING approval", async () => {
    const { wsId, profileId } = await seedPendingProfile();
    const a = await requestVerification({ profileId, workspaceId: wsId, actorMemberId: REQUESTER });
    const b = await requestVerification({ profileId, workspaceId: wsId, actorMemberId: REQUESTER });
    expect(a.approvalId).toBe(b.approvalId);
  });
});
