import { describe, expect, it } from "vitest";
import {
  createLegalEntityProfile,
  listLegalEntityProfiles,
  requestVerification,
  applyVerification,
} from "../services/legal-entity-profile.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

describe("legal-entity-profile service", () => {
  it("creates profile with UNREGISTERED status when no reg number", async () => {
    const wsId = generateSnowflake();
    const profile = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "MICRO_ENTERPRISE",
    });

    expect(profile.status).toBe("UNREGISTERED");
    expect(profile.workspaceId).toBe(String(wsId));
  });

  it("creates profile with REGISTRATION_READINESS when reg number provided", async () => {
    const wsId = generateSnowflake();
    const profile = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "MICRO_ENTERPRISE",
      registrationNumber: "0101234567",
      taxId: "0101234567",
    });

    expect(profile.status).toBe("REGISTRATION_READINESS");
    expect(profile.registrationNumber).toBe("0101234567");
  });

  it("handles verification flow requiring approval and forbids direct auto-verify", async () => {
    const wsId = generateSnowflake();
    const profile = await createLegalEntityProfile({
      workspaceId: wsId,
      entityType: "LLC",
      registrationNumber: "0309998887",
    });

    const verificationReq = await requestVerification({
      profileId: BigInt(profile.id),
      actorMemberId: 1001n,
    });
    expect(verificationReq.status).toBe("PENDING_APPROVAL");
    expect(verificationReq.approvalId.startsWith("appr_legal_")).toBe(true);

    // Rejects invalid approvalId
    await expect(
      applyVerification({
        profileId: BigInt(profile.id),
        approvalId: "invalid_id",
        approverMemberId: 1002n,
      })
    ).rejects.toThrow();

    // Succeeds with valid approvalId
    const verified = await applyVerification({
      profileId: BigInt(profile.id),
      approvalId: verificationReq.approvalId,
      approverMemberId: 1002n,
    });
    expect(verified.status).toBe("REGISTERED_VERIFIED");
    expect(verified.verifiedAt).toBeTruthy();
  });
});
