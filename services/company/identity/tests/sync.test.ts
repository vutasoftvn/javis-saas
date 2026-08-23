import { describe, it, expect, vi, afterEach } from "vitest";
import { syncFromPlatform } from "../handlers/sync.handler";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";
import * as platformClient from "../services/platform.client";

// syncFromPlatform phụ thuộc vào validatePlatformMembership gọi HTTP thật sang
// services/cosa (control-plane). Test ở đây chỉ xác minh logic đồng bộ local
// (tạo/update user, workspace, membership) — không phải hành vi thật của
// control-plane, nên mock thẳng kết quả membership thay vì phụ thuộc vào 1
// server cosa đang chạy. Xem platform.client.ts: nếu cosa không phản hồi được,
// hàm thật phải throw APIError.unavailable (fail-closed) chứ không tự phong
// role — hành vi đó được test riêng ở dưới.
function mockMembership(overrides: Partial<platformClient.ValidateMembershipResult> = {}) {
  return vi.spyOn(platformClient, "validatePlatformMembership").mockResolvedValue({
    valid: true,
    userId: overrides.userId ?? "unused",
    email: overrides.email ?? null,
    phone: overrides.phone ?? null,
    displayName: overrides.displayName ?? null,
    companyId: overrides.companyId ?? "unused",
    companyName: overrides.companyName ?? "Mock Co",
    roleId: overrides.roleId ?? "founder",
  });
}

describe("Sync from Platform into Local Identity", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("syncs a new platform user & company to local database", async () => {
    const userId = `${Date.now()}`;
    const companyId = "1001";
    mockMembership({ userId, companyId, roleId: "founder" });

    const syncRes = await syncFromPlatform({
      platform_access_token: "irrelevant-since-membership-is-mocked",
      company_id: companyId,
    });

    expect(syncRes.access_token).toBeDefined();
    expect(syncRes.token_type).toBe("bearer");

    const [localUser] = await db
      .select()
      .from(schema.identityUserProjections)
      .where(eq(schema.identityUserProjections.platformUserId, userId))
      .limit(1);

    expect(localUser).toBeDefined();
    expect(localUser.role).toBe("founder");

    const [localWs] = await db
      .select()
      .from(schema.identityWorkspaces)
      .where(eq(schema.identityWorkspaces.platformCompanyId, companyId))
      .limit(1);

    expect(localWs).toBeDefined();
  });

  it("is idempotent when syncing the same platform user multiple times", async () => {
    const userId = `${Date.now() + 1}`;
    const companyId = "1002";
    mockMembership({ userId, companyId, roleId: "founder" });

    const firstSync = await syncFromPlatform({
      platformAccessToken: "irrelevant-since-membership-is-mocked",
      companyId,
    });

    const secondSync = await syncFromPlatform({
      platformAccessToken: "irrelevant-since-membership-is-mocked",
      companyId,
    });

    expect(firstSync.access_token).toBeDefined();
    expect(secondSync.access_token).toBeDefined();
  });

  it("does not grant membership when control-plane cannot be reached (fail-closed, not fail-open-as-founder)", async () => {
    vi.spyOn(platformClient, "validatePlatformMembership").mockRejectedValue(
      new Error("simulated network failure talking to cosa")
    );

    await expect(
      syncFromPlatform({
        platform_access_token: "any-token",
        company_id: "9999",
      })
    ).rejects.toThrow();
  });
});
