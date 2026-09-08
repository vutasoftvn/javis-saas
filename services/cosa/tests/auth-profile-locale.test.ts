import jwt from "jsonwebtoken";
import { describe, expect, it } from "vitest";
import {
  registerPlatformUser,
  getPlatformUserProfile,
  updatePlatformUserProfile,
} from "../services/auth.service";
import { getLocaleSnapshotForWorkspace } from "../handlers/auth.handler";

const TEST_SECRET = "cosa-control-delegation-dev-secret-change-in-prod";

function signControlDelegation(opts: { sub: string; workspaceId: string; role?: string }): string {
  return jwt.sign(
    { sub: opts.sub, workspace_id: opts.workspaceId, role: opts.role ?? "member" },
    process.env.COSA_CONTROL_DELEGATION_SECRET || TEST_SECRET,
    { audience: "cosa_control", issuer: "cosa_apps", expiresIn: "10m" }
  );
}

async function createProfileForTest() {
  return registerPlatformUser({
    email: `locale-${Date.now()}-${Math.random()}@test.invalid`,
    password: "SecurePassword123",
    workspace_name: "Locale test workspace",
  });
}

describe("Auth Profile Locale", () => {
  it("defaults a new profile to vi-VN and returns it from GET /platform/auth/me", async () => {
    const session = await createProfileForTest();
    const me = await getPlatformUserProfile(session.user!.id);
    expect(me.preferred_locale).toBe("vi-VN");
  });

  it("allows setting preferred_locale to en-US during registerPlatformUser", async () => {
    const session = await registerPlatformUser({
      email: `locale-en-${Date.now()}-${Math.random()}@test.invalid`,
      password: "SecurePassword123",
      workspace_name: "Locale EN workspace",
      preferred_locale: "en-US",
    });
    expect(session.user!.preferred_locale).toBe("en-US");
    const me = await getPlatformUserProfile(session.user!.id);
    expect(me.preferred_locale).toBe("en-US");
  });

  it("changes only the authenticated caller locale", async () => {
    const alice = await createProfileForTest();
    const bob = await createProfileForTest();
    const changed = await updatePlatformUserProfile(alice.user!.id, { preferred_locale: "en-US" });
    expect(changed.preferred_locale).toBe("en-US");
    expect((await getPlatformUserProfile(bob.user!.id)).preferred_locale).toBe("vi-VN");
  });

  it("rejects unsupported locale without changing stored preference", async () => {
    const session = await createProfileForTest();
    await expect(
      updatePlatformUserProfile(session.user!.id, { preferred_locale: "fr-FR" as any })
    ).rejects.toThrow();
    expect((await getPlatformUserProfile(session.user!.id)).preferred_locale).toBe("vi-VN");
  });

  it("returns a locale snapshot only for a caller that belongs to the workspace", async () => {
    const session = await createProfileForTest();
    const foreign = await createProfileForTest();

    const validDelegation = signControlDelegation({
      sub: session.user!.id,
      workspaceId: session.platform_workspace_id!,
    });
    const foreignDelegation = signControlDelegation({
      sub: foreign.user!.id,
      workspaceId: foreign.platform_workspace_id!,
    });

    const snapshot = await getLocaleSnapshotForWorkspace({
      workspaceId: session.platform_workspace_id!,
      authorization: `Bearer ${validDelegation}`,
    });
    expect(snapshot.workspace_id).toBe(session.platform_workspace_id!);
    expect(snapshot.preferred_locale).toBe("vi-VN");

    // Foreign workspace delegation must be rejected
    await expect(
      getLocaleSnapshotForWorkspace({
        workspaceId: session.platform_workspace_id!,
        authorization: `Bearer ${foreignDelegation}`,
      })
    ).rejects.toThrow();
  });
});

