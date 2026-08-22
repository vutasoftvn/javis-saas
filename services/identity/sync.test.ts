import { describe, it, expect } from "vitest";
import { registerPlatform } from "../control-plane/auth";
import { syncFromPlatform } from "./sync";
import { getMe } from "./me";
import { verifyAccessToken } from "./token";

describe("Sync from Platform into Local Identity", () => {
  it("syncs a new platform user & company to local database", async () => {
    const timestamp = Date.now();
    const platformRes = await registerPlatform({
      email: `sync_user_${timestamp}@example.com`,
      password: "password123",
      full_name: "Sync Tester",
      company_name: `Sync Workspace ${timestamp}`,
    });

    expect(platformRes.access_token).toBeDefined();
    expect(platformRes.company_id).toBeDefined();

    // Perform Sync
    const syncRes = await syncFromPlatform({
      platform_access_token: platformRes.access_token,
      company_id: platformRes.company_id!,
    });

    expect(syncRes.access_token).toBeDefined();
    expect(syncRes.token_type).toBe("bearer");

    // Local JWT verification
    const localPayload = verifyAccessToken(syncRes.access_token);
    expect(localPayload.sub).toBeDefined();

    // Verify local getMe
    const me = await getMe({ userID: localPayload.sub });
    expect(me.email).toBe(`sync_user_${timestamp}@example.com`);
    expect(me.displayName).toBe("Sync Tester");
    expect(me.workspaceId).toBeDefined();
    expect(me.role).toBe("admin");
  });

  it("is idempotent when syncing the same platform user multiple times", async () => {
    const timestamp = Date.now();
    const platformRes = await registerPlatform({
      email: `idempotent_${timestamp}@example.com`,
      password: "password123",
      full_name: "Idempotent User",
      company_name: `Idempotent Co ${timestamp}`,
    });

    // First sync
    const firstSync = await syncFromPlatform({
      platform_access_token: platformRes.access_token,
      company_id: platformRes.company_id!,
    });

    // Second sync
    const secondSync = await syncFromPlatform({
      platform_access_token: platformRes.access_token,
      company_id: platformRes.company_id!,
    });

    const firstPayload = verifyAccessToken(firstSync.access_token);
    const secondPayload = verifyAccessToken(secondSync.access_token);

    expect(firstPayload.sub).toBe(secondPayload.sub);
  });
});
