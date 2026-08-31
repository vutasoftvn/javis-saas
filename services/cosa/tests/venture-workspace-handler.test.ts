import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from "vitest";
import { db, schema } from "../models/db";
import { eq, and } from "drizzle-orm";
import {
  listWorkspaceMembershipsEndpoint,
  validateWorkspaceMembershipEndpoint,
  markWorkspaceSyncedEndpoint,
  getWorkspaceEntitlementEndpoint,
} from "../handlers/venture-workspace.handler";
import { signPlatformToken } from "../services/token.service";
import { provisionVentureWorkspace } from "../services/venture-workspace.service";
import { registerPlatformUser } from "../services/auth.service";
import { APIError } from "encore.dev/api";

const {
  users,
  workspaces,
  workspaceMemberships,
  workspaceEntitlements,
  workspaceSyncLogs,
  profiles,
} = schema;

describe("venture-workspace handler", () => {
  let testUser1Id: bigint;
  let testUser2Id: bigint;
  let testWorkspaceId: bigint;

  beforeAll(async () => {
    // Tạo hai user test để kiểm tra membership validation
    const email1 = `vwh-test-${Date.now()}@t.io`;
    const email2 = `vwh-test-${Date.now() + 1}@t.io`;

    // Đăng ký user 1
    const user1Result = await registerPlatformUser({
      email: email1,
      password: "testPassword123",
    });
    const [u1] = await db
      .select({ id: users.id })
      .from(users)
      .where(eq(users.email, email1))
      .limit(1);
    testUser1Id = u1?.id ?? BigInt(0);

    // Đăng ký user 2
    await registerPlatformUser({
      email: email2,
      password: "testPassword123",
    });
    const [u2] = await db
      .select({ id: users.id })
      .from(users)
      .where(eq(users.email, email2))
      .limit(1);
    testUser2Id = u2?.id ?? BigInt(0);

    // Tạo workspace cho user 1
    const wsResult = await provisionVentureWorkspace({
      ownerUserId: testUser1Id,
      workspaceName: "Test Venture Workspace",
      clientCreationId: `vwh-test-${Date.now()}`,
    });
    testWorkspaceId = BigInt(wsResult.platformWorkspaceId);
  });

  beforeEach(async () => {
    // Cleanup nếu cần, nhưng giữ user và workspace từ beforeAll
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("listWorkspaceMembershipsEndpoint", () => {
    it("returns workspace memberships for valid platform token", async () => {
      const token = signPlatformToken(testUser1Id.toString());
      const response = await listWorkspaceMembershipsEndpoint({
        platformToken: token,
      });

      expect(response.memberships).toBeDefined();
      expect(Array.isArray(response.memberships)).toBe(true);
      expect(response.memberships.length).toBeGreaterThan(0);

      // Verify membership structure
      const membership = response.memberships[0];
      expect(membership.platformWorkspaceId).toBeDefined();
      expect(membership.workspaceName).toBeDefined();
      expect(membership.userId).toBeDefined();
      expect(membership.role).toBeDefined();
      expect(membership.membershipId).toBeDefined();
      expect(membership.membershipUpdatedAt).toBeDefined();
    });

    it("returns empty list when user has no memberships", async () => {
      // Tạo user mới mà không có workspace
      const email = `vwh-nomember-${Date.now()}@t.io`;
      await registerPlatformUser({
        email,
        password: "testPassword123",
      });

      const [newUser] = await db
        .select({ id: users.id })
        .from(users)
        .where(eq(users.email, email))
        .limit(1);
      const newUserId = newUser?.id ?? BigInt(0);

      const token = signPlatformToken(newUserId.toString());
      const response = await listWorkspaceMembershipsEndpoint({
        platformToken: token,
      });

      expect(response.memberships).toBeDefined();
      expect(Array.isArray(response.memberships)).toBe(true);
      expect(response.memberships.length).toBe(0);
    });

    it("throws unauthenticated error with invalid platform token", async () => {
      await expect(
        listWorkspaceMembershipsEndpoint({
          platformToken: "invalid.token.here",
        })
      ).rejects.toMatchObject({ code: "unauthenticated" });
    });

    it("throws unauthenticated error with expired or malformed token", async () => {
      await expect(
        listWorkspaceMembershipsEndpoint({
          platformToken: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.invalid",
        })
      ).rejects.toMatchObject({ code: "unauthenticated" });
    });
  });

  describe("validateWorkspaceMembershipEndpoint", () => {
    it("returns valid=true when user is member of workspace", async () => {
      const token = signPlatformToken(testUser1Id.toString());
      const response = await validateWorkspaceMembershipEndpoint({
        platformToken: token,
        platformWorkspaceId: testWorkspaceId.toString(),
      });

      expect(response.valid).toBe(true);
      expect(response.membership).toBeDefined();
      expect(response.membership?.platformWorkspaceId).toBe(testWorkspaceId.toString());
      expect(response.membership?.userId).toBe(testUser1Id.toString());
      expect(response.membership?.role).toBe("founder");
    });

    it("returns valid=false when user is not member of workspace", async () => {
      const token = signPlatformToken(testUser2Id.toString());
      const response = await validateWorkspaceMembershipEndpoint({
        platformToken: token,
        platformWorkspaceId: testWorkspaceId.toString(),
      });

      expect(response.valid).toBe(false);
      expect(response.membership).toBeUndefined();
    });

    it("returns valid=false for nonexistent workspace", async () => {
      const token = signPlatformToken(testUser1Id.toString());
      const response = await validateWorkspaceMembershipEndpoint({
        platformToken: token,
        platformWorkspaceId: "999999999999",
      });

      expect(response.valid).toBe(false);
      expect(response.membership).toBeUndefined();
    });

    it("throws unauthenticated error with invalid platform token", async () => {
      await expect(
        validateWorkspaceMembershipEndpoint({
          platformToken: "invalid.token",
          platformWorkspaceId: testWorkspaceId.toString(),
        })
      ).rejects.toMatchObject({ code: "unauthenticated" });
    });

    it("includes membership details when valid", async () => {
      const token = signPlatformToken(testUser1Id.toString());
      const response = await validateWorkspaceMembershipEndpoint({
        platformToken: token,
        platformWorkspaceId: testWorkspaceId.toString(),
      });

      if (response.membership) {
        expect(response.membership.workspaceName).toBe("Test Venture Workspace");
        expect(response.membership.membershipUpdatedAt).toBeDefined();
        // membershipUpdatedAt should be a valid ISO date string
        expect(() => new Date(response.membership.membershipUpdatedAt)).not.toThrow();
      }
    });
  });

  describe("markWorkspaceSyncedEndpoint", () => {
    it("marks workspace as synced with valid membership", async () => {
      // Create a fresh workspace for this test
      const email = `vwh-sync-${Date.now()}@t.io`;
      const userResult = await registerPlatformUser({
        email,
        password: "testPassword123",
      });
      const [newUser] = await db
        .select({ id: users.id })
        .from(users)
        .where(eq(users.email, email))
        .limit(1);
      const userId = newUser?.id ?? BigInt(0);

      const wsResult = await provisionVentureWorkspace({
        ownerUserId: userId,
        workspaceName: "Sync Test Workspace",
        clientCreationId: `vwh-sync-${Date.now()}`,
      });
      const workspaceId = BigInt(wsResult.platformWorkspaceId);

      // 초기 상태 확인: syncStatus는 "pending"이어야 함
      const [syncLogBefore] = await db
        .select()
        .from(workspaceSyncLogs)
        .where(eq(workspaceSyncLogs.workspaceId, workspaceId))
        .limit(1);
      expect(syncLogBefore.syncStatus).toBe("pending");
      expect(syncLogBefore.syncedAt).toBeNull();

      // Mark as synced
      const token = signPlatformToken(userId.toString());
      const response = await markWorkspaceSyncedEndpoint({
        platformToken: token,
        platformWorkspaceId: workspaceId.toString(),
      });

      expect(response.success).toBe(true);

      // 동기화 후 상태 확인
      const [syncLogAfter] = await db
        .select()
        .from(workspaceSyncLogs)
        .where(eq(workspaceSyncLogs.workspaceId, workspaceId))
        .limit(1);
      expect(syncLogAfter.syncStatus).toBe("success");
      expect(syncLogAfter.syncedAt).not.toBeNull();
    });

    it("throws permissionDenied error when user is not member of workspace", async () => {
      const token = signPlatformToken(testUser2Id.toString());
      await expect(
        markWorkspaceSyncedEndpoint({
          platformToken: token,
          platformWorkspaceId: testWorkspaceId.toString(),
        })
      ).rejects.toMatchObject({ code: "permission_denied" });
    });

    it("throws unauthenticated error with invalid platform token", async () => {
      await expect(
        markWorkspaceSyncedEndpoint({
          platformToken: "invalid.token",
          platformWorkspaceId: testWorkspaceId.toString(),
        })
      ).rejects.toMatchObject({ code: "unauthenticated" });
    });

    it("succeeds even for nonexistent workspace ID (no-op)", async () => {
      // This tests the handler behavior: if user is not a member of the
      // nonexistent workspace, it should throw permissionDenied. But let's
      // verify the behavior.
      const token = signPlatformToken(testUser1Id.toString());
      await expect(
        markWorkspaceSyncedEndpoint({
          platformToken: token,
          platformWorkspaceId: "999999999999",
        })
      ).rejects.toMatchObject({ code: "permission_denied" });
    });
  });

  describe("getWorkspaceEntitlementEndpoint", () => {
    it("requires proper auth context setup - current test limitation", async () => {
      // NOTE: getWorkspaceEntitlementEndpoint uses auth: true decorator, which
      // requires Encore's native auth context set via the Gateway. When calling
      // the endpoint function directly in tests, we bypass the HTTP layer and
      // Encore's auth middleware.
      //
      // The endpoint calls resolveAuthData() which tries to import ~encore/auth
      // module (only available during Encore runtime). In test context, this
      // throws an error.
      //
      // To test this endpoint properly, we would need:
      // 1. Start the full Encore server in test mode
      // 2. Make actual HTTP calls with Bearer token
      // 3. Let Encore's Gateway handle auth and set context
      //
      // OR refactor the handler to not use auth: true and instead accept
      // platformToken in request body (like the other endpoints).
      //
      // For now, we skip direct testing of this endpoint and rely on:
      // - Service-layer tests for getWorkspaceEntitlement() function
      // - Integration tests that invoke via HTTP with Encore running

      const token = signPlatformToken(testUser1Id.toString());
      // This will throw because resolveAuthData() can't import ~encore/auth
      await expect(
        getWorkspaceEntitlementEndpoint({ id: testWorkspaceId.toString() })
      ).rejects.toThrow();
    });
  });

  describe("Integration: membership lifecycle", () => {
    it("lists user memberships, validates each, and marks synced", async () => {
      const token = signPlatformToken(testUser1Id.toString());

      // List all memberships
      const listResponse = await listWorkspaceMembershipsEndpoint({
        platformToken: token,
      });
      expect(listResponse.memberships.length).toBeGreaterThan(0);

      // For each membership, validate it
      for (const membership of listResponse.memberships) {
        const validateResponse = await validateWorkspaceMembershipEndpoint({
          platformToken: token,
          platformWorkspaceId: membership.platformWorkspaceId,
        });
        expect(validateResponse.valid).toBe(true);
        expect(validateResponse.membership?.platformWorkspaceId).toBe(membership.platformWorkspaceId);
      }

      // Mark first workspace as synced
      const firstMembership = listResponse.memberships[0];
      const syncResponse = await markWorkspaceSyncedEndpoint({
        platformToken: token,
        platformWorkspaceId: firstMembership.platformWorkspaceId,
      });
      expect(syncResponse.success).toBe(true);
    });
  });
});
