import { describe, it, expect } from "vitest";
import { registerPlatform } from "../../control-plane/handlers/auth.handler";
import { syncFromPlatform } from "../handlers/sync.handler";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";

describe("Sync from Platform into Local Identity", () => {
  it("syncs a new platform user & company to local database", async () => {
    const testEmail = `synctest_${Date.now()}@example.com`;
    const regRes = await registerPlatform({
      email: testEmail,
      password: "password123",
      full_name: "Sync User",
      company_name: "Sync Ventures Inc",
    });

    expect(regRes.access_token).toBeDefined();
    expect(regRes.company_id).toBeDefined();

    const syncRes = await syncFromPlatform({
      platform_access_token: regRes.access_token,
      company_id: regRes.company_id!,
    });

    expect(syncRes.access_token).toBeDefined();
    expect(syncRes.token_type).toBe("bearer");

    const [localUser] = await db
      .select()
      .from(schema.identityUsers)
      .where(eq(schema.identityUsers.email, testEmail))
      .limit(1);

    expect(localUser).toBeDefined();
    expect(localUser.displayName).toBe("Sync User");
    expect(localUser.role).toBe("founder");

    const [localWs] = await db
      .select()
      .from(schema.identityWorkspaces)
      .where(eq(schema.identityWorkspaces.platformCompanyId, regRes.company_id!))
      .limit(1);

    expect(localWs).toBeDefined();
    expect(localWs.name).toBe("Sync Ventures Inc");
  });

  it("is idempotent when syncing the same platform user multiple times", async () => {
    const testEmail = `synctest2_${Date.now()}@example.com`;
    const regRes = await registerPlatform({
      email: testEmail,
      password: "password123",
      full_name: "Sync User 2",
      company_name: "Sync Ventures Inc 2",
    });

    const firstSync = await syncFromPlatform({
      platformAccessToken: regRes.access_token,
      companyId: regRes.company_id!,
    });

    const secondSync = await syncFromPlatform({
      platformAccessToken: regRes.access_token,
      companyId: regRes.company_id!,
    });

    expect(firstSync.access_token).toBeDefined();
    expect(secondSync.access_token).toBeDefined();
  });
});
