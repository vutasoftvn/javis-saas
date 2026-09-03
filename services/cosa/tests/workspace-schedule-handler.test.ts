import jwt from "jsonwebtoken";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  createScheduleEndpoint,
  listSchedulesEndpoint,
  runScheduleNowEndpoint,
  getScheduleExecutionEndpoint,
} from "../handlers/workspace-schedule.handler";
import { signPlatformToken, signWorkerServiceToken } from "../services/token.service";
import { db, schema } from "../models/db";
import * as scheduleSvc from "../services/workspace-schedule.service";

const { workspaceScheduleDefinitions, workspaceScheduleExecutions } = schema;

const TEST_CONTROL_DELEGATION_SECRET = "test-control-delegation-secret-min-32-chars";

function signControlDelegation(opts: { sub: string; workspaceId: string; role?: string }): string {
  // Claim JWT thô là workspace_id (snake_case) — cùng convention với
  // mint_control_plane_delegation (apps/cosa/auth/jwt.py) qua wire thật.
  return jwt.sign(
    { sub: opts.sub, workspace_id: opts.workspaceId, role: opts.role ?? "member" },
    TEST_CONTROL_DELEGATION_SECRET,
    { audience: "cosa_control", issuer: "cosa_apps", expiresIn: "10m" }
  );
}

describe("Workspace Schedule Handler Authorization (Gate 0)", () => {
  beforeEach(async () => {
    // Mock fetch for workspace membership verification
    vi.stubGlobal("fetch", vi.fn(async (url: string, opts?: any) => {
      // Default: user is NOT a member of workspace B (403)
      if (url.includes("/workspaces/ws_b/")) {
        return {
          status: 403,
          ok: false,
          json: async () => ({}),
        } as any;
      }
      // User IS a member of workspace A (200)
      return {
        status: 200,
        ok: true,
        json: async () => ({
          platformCompanyId: "1",
          membershipRole: "member",
        }),
      } as any;
    }));

    // Clean up test data
    await db.delete(workspaceScheduleExecutions);
    await db.delete(workspaceScheduleDefinitions);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("rejects createSchedule when caller is not a member of workspace", async () => {
    const tokenUserA = signPlatformToken("user_a");
    const authHeader = `Bearer ${tokenUserA}`;

    // Try to create schedule in workspace B (where user_a is not a member)
    await expect(
      createScheduleEndpoint({
        authorization: authHeader,
        workspaceId: "ws_b",
        scheduleKind: "daily",
        hour: 9,
        minute: 0,
        promptTemplate: "Daily report",
      })
    ).rejects.toThrow(/workspace/i);
  });

  it("rejects listSchedules when caller is not a member of workspace", async () => {
    const tokenUserA = signPlatformToken("user_a");
    const authHeader = `Bearer ${tokenUserA}`;

    // Try to list schedules in workspace B (where user_a is not a member)
    await expect(
      listSchedulesEndpoint({
        authorization: authHeader,
        workspaceId: "ws_b",
      })
    ).rejects.toThrow(/workspace/i);
  });

  it("rejects runScheduleNow when caller is not a member of workspace", async () => {
    // First create a schedule in workspace A (where user_a is a member)
    const tokenUserA = signPlatformToken("user_a");
    const schedule = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_a",
      createdBy: "user_a",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Daily scan",
    });

    // Now try to run it from workspace B context (user_a is not a member)
    const authHeader = `Bearer ${tokenUserA}`;
    await expect(
      runScheduleNowEndpoint({
        authorization: authHeader,
        scheduleId: schedule.id,
        workspaceId: "ws_b",
      })
    ).rejects.toThrow(/workspace/i);
  });

  it("calls verifyWorkspaceMembership with correct params for create", async () => {
    const tokenUserA = signPlatformToken("user_a");
    const authHeader = `Bearer ${tokenUserA}`;
    const mockFetch = vi.fn(async (url: string, opts?: any) => {
      return {
        status: 200,
        ok: true,
        json: async () => ({
          platformCompanyId: "1",
          membershipRole: "member",
        }),
      } as any;
    });
    vi.stubGlobal("fetch", mockFetch);

    await createScheduleEndpoint({
      authorization: authHeader,
      workspaceId: "ws_a",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Daily report",
    });

    // Verify fetch was called with correct workspace
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("ws_a"),
      expect.any(Object)
    );
  });

  it("calls verifyWorkspaceMembership with correct params for list", async () => {
    const tokenUserA = signPlatformToken("user_a");
    const authHeader = `Bearer ${tokenUserA}`;
    const mockFetch = vi.fn(async (url: string, opts?: any) => {
      return {
        status: 200,
        ok: true,
        json: async () => ({
          platformCompanyId: "1",
          membershipRole: "member",
        }),
      } as any;
    });
    vi.stubGlobal("fetch", mockFetch);

    await listSchedulesEndpoint({
      authorization: authHeader,
      workspaceId: "ws_a",
    });

    // Verify fetch was called with correct workspace
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("ws_a"),
      expect.any(Object)
    );
  });

  it("calls verifyWorkspaceMembership with correct params for run-now", async () => {
    const tokenUserA = signPlatformToken("user_a");
    const schedule = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_a",
      createdBy: "user_a",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Daily scan",
    });

    const authHeader = `Bearer ${tokenUserA}`;
    const mockFetch = vi.fn(async (url: string, opts?: any) => {
      return {
        status: 200,
        ok: true,
        json: async () => ({
          platformCompanyId: "1",
          membershipRole: "member",
        }),
      } as any;
    });
    vi.stubGlobal("fetch", mockFetch);

    await runScheduleNowEndpoint({
      authorization: authHeader,
      scheduleId: schedule.id,
      workspaceId: "ws_a",
    });

    // Verify fetch was called with correct workspace
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("ws_a"),
      expect.any(Object)
    );
  });

  it("allows successful create when caller is workspace member", async () => {
    const tokenUserA = signPlatformToken("user_a");
    const authHeader = `Bearer ${tokenUserA}`;

    const result = await createScheduleEndpoint({
      authorization: authHeader,
      workspaceId: "ws_a",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Daily report",
    });

    expect(result.id).toBeDefined();
    expect(result.workspaceId).toBe("ws_a");
    expect(result.state).toBe("enabled");
  });

  it("allows successful list when caller is workspace member", async () => {
    const tokenUserA = signPlatformToken("user_a");
    const authHeader = `Bearer ${tokenUserA}`;

    // Create a schedule first
    await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_a",
      createdBy: "user_a",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Daily scan",
    });

    const result = await listSchedulesEndpoint({
      authorization: authHeader,
      workspaceId: "ws_a",
    });

    expect(result.items).toBeDefined();
    expect(result.total).toBe(1);
  });

  it("allows successful run-now when caller is workspace member", async () => {
    const tokenUserA = signPlatformToken("user_a");
    const schedule = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_a",
      createdBy: "user_a",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Daily scan",
    });

    const authHeader = `Bearer ${tokenUserA}`;
    const result = await runScheduleNowEndpoint({
      authorization: authHeader,
      scheduleId: schedule.id,
      workspaceId: "ws_a",
    });

    expect(result.id).toBeDefined();
    expect(result.state).toBe("queued");
  });

  it("normalizes invalid input as APIError.invalidArgument", async () => {
    const tokenUserA = signPlatformToken("user_a");
    const authHeader = `Bearer ${tokenUserA}`;

    await expect(
      createScheduleEndpoint({
        authorization: authHeader,
        workspaceId: "ws_a",
        scheduleKind: "daily",
        timezone: "Invalid/Timezone",
        hour: 9,
        minute: 0,
        promptTemplate: "Scan",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });

    await expect(
      createScheduleEndpoint({
        authorization: authHeader,
        workspaceId: "ws_a",
        scheduleKind: "daily",
        hour: 9,
        minute: 0,
        promptTemplate: "   ",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("normalizes missing execution as APIError.notFound", async () => {
    const tokenWorker = signWorkerServiceToken("worker_1");
    const authHeader = `Bearer ${tokenWorker}`;

    await expect(
      getScheduleExecutionEndpoint({
        authorization: authHeader,
        executionId: "non_existent_exec_999",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });
});

describe("Workspace Schedule Service", () => {
  beforeEach(async () => {
    // Clean up test data
    await db.delete(workspaceScheduleExecutions);
    await db.delete(workspaceScheduleDefinitions);
  });

  it("listWorkspaceSchedules returns schedules for workspace", async () => {
    const created = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_a",
      createdBy: "user_a",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Daily report",
    });

    const result = await scheduleSvc.listWorkspaceSchedules("ws_a");
    expect(result.items).toContainEqual(
      expect.objectContaining({ id: created.id })
    );
  });

  it("getScheduleExecution returns execution by ID", async () => {
    const schedule = await scheduleSvc.createWorkspaceSchedule({
      workspaceId: "ws_a",
      createdBy: "user_a",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Scan",
    });

    const execution = await scheduleSvc.runScheduleNow({
      scheduleId: schedule.id,
      workspaceId: "ws_a",
      principalId: "user_a",
    });

    const result = await scheduleSvc.getScheduleExecution(execution.id);
    expect(result.id).toBe(execution.id);
  });

  it("getScheduleExecution throws notFound when execution missing", async () => {
    await expect(
      scheduleSvc.getScheduleExecution("nonexistent_exec_999")
    ).rejects.toMatchObject({ code: "not_found" });
  });
});

describe("Workspace Schedule Handler — B5 control-plane delegation", () => {
  const originalSecret = process.env.COSA_CONTROL_DELEGATION_SECRET;

  beforeEach(async () => {
    process.env.COSA_CONTROL_DELEGATION_SECRET = TEST_CONTROL_DELEGATION_SECRET;
    await db.delete(workspaceScheduleExecutions);
    await db.delete(workspaceScheduleDefinitions);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    process.env.COSA_CONTROL_DELEGATION_SECRET = originalSecret;
  });

  it("create/list/run-now qua delegation KHÔNG round-trip sang services/company", async () => {
    const fetchSpy = vi.fn(() => {
      throw new Error("must not call services/company when using control-plane delegation");
    });
    vi.stubGlobal("fetch", fetchSpy);

    const delegation = signControlDelegation({ sub: "user_a", workspaceId: "ws_a" });
    const authHeader = `Bearer ${delegation}`;

    const created = await createScheduleEndpoint({
      authorization: authHeader,
      workspaceId: "ws_a",
      scheduleKind: "daily",
      hour: 9,
      minute: 0,
      promptTemplate: "Daily report",
    });
    expect(created.workspaceId).toBe("ws_a");

    const listed = await listSchedulesEndpoint({ authorization: authHeader, workspaceId: "ws_a" });
    expect(listed.total).toBe(1);

    const ran = await runScheduleNowEndpoint({
      authorization: authHeader,
      scheduleId: created.id,
      workspaceId: "ws_a",
    });
    expect(ran.state).toBe("queued");

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("từ chối delegation scoped cho workspace khác", async () => {
    const delegation = signControlDelegation({ sub: "user_a", workspaceId: "ws_b" });

    await expect(
      createScheduleEndpoint({
        authorization: `Bearer ${delegation}`,
        workspaceId: "ws_a",
        scheduleKind: "daily",
        hour: 9,
        minute: 0,
        promptTemplate: "Daily report",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });
});
