import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { createScheduleEndpoint, listSchedulesEndpoint, runScheduleNowEndpoint } from "../handlers/workspace-schedule.handler";
import { signPlatformToken } from "../services/token.service";
import { db, schema } from "../models/db";
import * as scheduleSvc from "../services/workspace-schedule.service";

const { workspaceScheduleDefinitions, workspaceScheduleExecutions } = schema;

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
});
