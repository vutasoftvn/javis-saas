import { describe, expect, it, beforeEach } from "vitest";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import {
  setEscalationRoute,
  resolveEscalationRoute,
  assertRouteBound,
} from "../../services/customer-engagement/escalation.service";
import { APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";

const { engagementEscalationRoutes } = schema;

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  const authorization = `Bearer ${user.accessToken}`;
  const ctx = await requireWorkspaceAccess(authorization, user.workspaceId);
  return { workspaceId: user.workspaceId, authorization, ctx, user };
}

describe("escalation.service", () => {
  it("rejects a route whose workspace does not match the authenticated context", async () => {
    const { ctx } = await makeAuthedWorkspace("route-workspace-mismatch");

    await expect(setEscalationRoute({
      workspaceId: String(generateSnowflake()),
      routeKey: "support-oncall",
      role: "primary",
      workforceMemberId: String(generateSnowflake()),
    }, ctx)).rejects.toThrow(/workspace mismatch/i);
  });

  describe("setEscalationRoute", () => {
    it("inserts a new escalation route for a role", async () => {
      const ws = await makeAuthedWorkspace("Escalation Route Test 1");
      const memberId = BigInt(generateSnowflake());

      await setEscalationRoute(
        {
          workspaceId: ws.workspaceId,
          routeKey: "support-oncall",
          role: "primary",
          workforceMemberId: String(memberId),
        },
        ws.ctx
      );

      const rows = await db
        .select()
        .from(engagementEscalationRoutes)
        .where(
          and(
            eq(engagementEscalationRoutes.workspaceId, BigInt(ws.workspaceId)),
            eq(engagementEscalationRoutes.routeKey, "support-oncall"),
            eq(engagementEscalationRoutes.role, "primary")
          )
        );

      expect(rows.length).toBeGreaterThan(0);
      expect(rows[0].workforceMemberId).toBe(memberId);
      expect(rows[0].activeUntil).toBeNull();
    });

    it("upserts: closes old active route and inserts new one for same role", async () => {
      const ws = await makeAuthedWorkspace("Escalation Route Upsert Test");
      const member1 = BigInt(generateSnowflake());
      const member2 = BigInt(generateSnowflake());

      // Set first route
      await setEscalationRoute(
        {
          workspaceId: ws.workspaceId,
          routeKey: "support-oncall",
          role: "primary",
          workforceMemberId: String(member1),
        },
        ws.ctx
      );

      // Set second route (should close first)
      await setEscalationRoute(
        {
          workspaceId: ws.workspaceId,
          routeKey: "support-oncall",
          role: "primary",
          workforceMemberId: String(member2),
        },
        ws.ctx
      );

      const rows = await db
        .select()
        .from(engagementEscalationRoutes)
        .where(
          and(
            eq(engagementEscalationRoutes.workspaceId, BigInt(ws.workspaceId)),
            eq(engagementEscalationRoutes.routeKey, "support-oncall"),
            eq(engagementEscalationRoutes.role, "primary")
          )
        );

      // Should have 2 rows: one closed (member1), one active (member2)
      expect(rows.length).toBeGreaterThanOrEqual(2);
      const activeRows = rows.filter((r) => r.activeUntil === null);
      const closedRows = rows.filter((r) => r.activeUntil !== null);

      expect(activeRows.length).toBe(1);
      expect(activeRows[0].workforceMemberId).toBe(member2);
      expect(closedRows.some((r) => r.workforceMemberId === member1)).toBe(true);
    });

    it("sets activeUntil if provided", async () => {
      const ws = await makeAuthedWorkspace("Escalation Route Until Test");
      const memberId = BigInt(generateSnowflake());
      const now = new Date();
      const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);

      await setEscalationRoute(
        {
          workspaceId: ws.workspaceId,
          routeKey: "support-backup",
          role: "backup",
          workforceMemberId: String(memberId),
          activeUntil: tomorrow,
        },
        ws.ctx
      );

      const rows = await db
        .select()
        .from(engagementEscalationRoutes)
        .where(
          and(
            eq(engagementEscalationRoutes.workspaceId, BigInt(ws.workspaceId)),
            eq(engagementEscalationRoutes.routeKey, "support-backup"),
            eq(engagementEscalationRoutes.role, "backup")
          )
        );

      expect(rows.length).toBeGreaterThan(0);
      // Find the row with activeUntil set
      const rowWithUntil = rows.find((r) => r.activeUntil !== null);
      expect(rowWithUntil).toBeDefined();
      expect(rowWithUntil?.activeUntil?.getTime()).toBeCloseTo(tomorrow.getTime(), -3);
    });
  });

  describe("resolveEscalationRoute", () => {
    it("resolves level 1 to primary role", async () => {
      const ws = await makeAuthedWorkspace("Resolve Level 1 Test");
      const memberId = String(generateSnowflake());

      await setEscalationRoute(
        {
          workspaceId: ws.workspaceId,
          routeKey: "support-oncall",
          role: "primary",
          workforceMemberId: memberId,
        },
        ws.ctx
      );

      const result = await resolveEscalationRoute("support-oncall", 1, ws.ctx);
      expect(result.role).toBe("primary");
      expect(result.workforceMemberId).toBe(memberId);
    });

    it("resolves level 2 to backup role", async () => {
      const ws = await makeAuthedWorkspace("Resolve Level 2 Test");
      const backupMemberId = String(generateSnowflake());

      await setEscalationRoute(
        {
          workspaceId: ws.workspaceId,
          routeKey: "support-oncall",
          role: "primary",
          workforceMemberId: String(generateSnowflake()),
        },
        ws.ctx
      );

      await setEscalationRoute(
        {
          workspaceId: ws.workspaceId,
          routeKey: "support-oncall",
          role: "backup",
          workforceMemberId: backupMemberId,
        },
        ws.ctx
      );

      const result = await resolveEscalationRoute("support-oncall", 2, ws.ctx);
      expect(result.role).toBe("backup");
      expect(result.workforceMemberId).toBe(backupMemberId);
    });

    it("resolves level 3 and higher to duty_manager role", async () => {
      const ws = await makeAuthedWorkspace("Resolve Level 3 Test");
      const managerMemberId = String(generateSnowflake());

      await setEscalationRoute(
        {
          workspaceId: ws.workspaceId,
          routeKey: "support-oncall",
          role: "primary",
          workforceMemberId: String(generateSnowflake()),
        },
        ws.ctx
      );

      await setEscalationRoute(
        {
          workspaceId: ws.workspaceId,
          routeKey: "support-oncall",
          role: "duty_manager",
          workforceMemberId: managerMemberId,
        },
        ws.ctx
      );

      const result3 = await resolveEscalationRoute("support-oncall", 3, ws.ctx);
      expect(result3.role).toBe("duty_manager");
      expect(result3.workforceMemberId).toBe(managerMemberId);

      const result5 = await resolveEscalationRoute("support-oncall", 5, ws.ctx);
      expect(result5.role).toBe("duty_manager");
      expect(result5.workforceMemberId).toBe(managerMemberId);
    });

    it("throws failedPrecondition if no active route for role", async () => {
      const ws = await makeAuthedWorkspace("Resolve Unbound Test");

      await expect(resolveEscalationRoute("support-oncall", 1, ws.ctx)).rejects.toThrow(
        /failedPrecondition|no active/i
      );
    });

    it("ignores expired routes (activeUntil in past)", async () => {
      const ws = await makeAuthedWorkspace("Resolve Expired Test");
      const now = new Date();
      const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);

      // Insert expired route
      await db.insert(engagementEscalationRoutes).values({
        id: BigInt(generateSnowflake()),
        workspaceId: BigInt(ws.workspaceId),
        routeKey: "support-oncall",
        role: "primary",
        workforceMemberId: BigInt(generateSnowflake()),
        activeFrom: yesterday,
        activeUntil: yesterday,
        createdAt: new Date(),
      });

      // Should throw because primary is expired
      await expect(resolveEscalationRoute("support-oncall", 1, ws.ctx)).rejects.toThrow(
        /failedPrecondition|no active/i
      );
    });

    it("only returns routes for the requesting workspace", async () => {
      const wsA = await makeAuthedWorkspace("Resolve Workspace Isolation A");
      const wsB = await makeAuthedWorkspace("Resolve Workspace Isolation B");

      const memberA = String(generateSnowflake());
      const memberB = String(generateSnowflake());

      // Setup route in wsA
      await setEscalationRoute(
        {
          workspaceId: wsA.workspaceId,
          routeKey: "support-oncall",
          role: "primary",
          workforceMemberId: memberA,
        },
        wsA.ctx
      );

      // Setup different route in wsB
      await setEscalationRoute(
        {
          workspaceId: wsB.workspaceId,
          routeKey: "support-oncall",
          role: "primary",
          workforceMemberId: memberB,
        },
        wsB.ctx
      );

      // wsA should see only memberA
      const resultA = await resolveEscalationRoute("support-oncall", 1, wsA.ctx);
      expect(resultA.workforceMemberId).toBe(memberA);

      // wsB should see only memberB
      const resultB = await resolveEscalationRoute("support-oncall", 1, wsB.ctx);
      expect(resultB.workforceMemberId).toBe(memberB);
    });
  });

  describe("assertRouteBound", () => {
    it("succeeds if primary route is active and bound", async () => {
      const ws = await makeAuthedWorkspace("Assert Bound Test");
      const memberId = String(generateSnowflake());

      await setEscalationRoute(
        {
          workspaceId: ws.workspaceId,
          routeKey: "support-oncall",
          role: "primary",
          workforceMemberId: memberId,
        },
        ws.ctx
      );

      // Should not throw
      await assertRouteBound("support-oncall", ws.ctx);
    });

    it("throws failedPrecondition if route has no primary", async () => {
      const ws = await makeAuthedWorkspace("Assert Unbound Test");

      // Set backup but not primary
      await setEscalationRoute(
        {
          workspaceId: ws.workspaceId,
          routeKey: "support-oncall",
          role: "backup",
          workforceMemberId: String(generateSnowflake()),
        },
        ws.ctx
      );

      await expect(assertRouteBound("support-oncall", ws.ctx)).rejects.toThrow(
        /failedPrecondition|no active.*primary/i
      );
    });

    it("throws failedPrecondition if primary route is expired", async () => {
      const ws = await makeAuthedWorkspace("Assert Expired Primary Test");
      const now = new Date();
      const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);

      // Insert expired primary route
      await db.insert(engagementEscalationRoutes).values({
        id: BigInt(generateSnowflake()),
        workspaceId: BigInt(ws.workspaceId),
        routeKey: "support-oncall",
        role: "primary",
        workforceMemberId: BigInt(generateSnowflake()),
        activeFrom: yesterday,
        activeUntil: yesterday,
        createdAt: new Date(),
      });

      await expect(assertRouteBound("support-oncall", ws.ctx)).rejects.toThrow(
        /failedPrecondition|no active.*primary/i
      );
    });

    it("only checks workspace scope", async () => {
      const wsA = await makeAuthedWorkspace("Assert Scope A");
      const wsB = await makeAuthedWorkspace("Assert Scope B");

      // Setup route only in wsB
      await setEscalationRoute(
        {
          workspaceId: wsB.workspaceId,
          routeKey: "support-oncall",
          role: "primary",
          workforceMemberId: String(generateSnowflake()),
        },
        wsB.ctx
      );

      // wsA should not see it
      await expect(assertRouteBound("support-oncall", wsA.ctx)).rejects.toThrow(
        /no active.*primary/i
      );

      // wsB should see it
      await assertRouteBound("support-oncall", wsB.ctx);
    });
  });
});
