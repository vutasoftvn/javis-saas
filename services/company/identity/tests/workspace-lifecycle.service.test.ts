import { describe, expect, it } from "vitest";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { db, schema } from "../models/db";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  transitionWorkspaceLifecycle,
  listWorkspaceLifecycleEvents,
} from "../services/workspace-lifecycle.service";

const { identityWorkspaces } = schema;

function ctxFor(workspaceId: string, membershipRole = "founder"): TenantContext {
  return Object.freeze({
    workspaceId,
    userId: "1",
    workforceMemberId: "1",
    membershipRole,
    permissions: [],
    correlationId: "test-workspace-lifecycle",
    platformUserId: null,
  }) as unknown as TenantContext;
}

async function newWorkspace(): Promise<string> {
  const id = generateSnowflake();
  await db.insert(identityWorkspaces).values({
    id,
    name: `WS ${Date.now()}-${Math.random().toString(36).slice(2)}`,
  });
  return id.toString();
}

describe("workspace lifecycle transition (human-only, no auto progression)", () => {
  it("advances one stage with CAS and appends an immutable event", async () => {
    const wsId = await newWorkspace();
    const ctx = ctxFor(wsId);

    const res = await transitionWorkspaceLifecycle(ctx, wsId, {
      toStage: "W1_PROBLEM_VALIDATION",
      expectedStageVersion: 0,
      rationale: "problem confirmed",
    });
    expect(res).toMatchObject({ lifecycleStage: "W1_PROBLEM_VALIDATION", stageVersion: 1 });

    const events = await listWorkspaceLifecycleEvents(ctx, wsId);
    expect(events.items).toHaveLength(1);
    expect(events.items[0]).toMatchObject({
      fromStage: "W0_IDEA",
      toStage: "W1_PROBLEM_VALIDATION",
      fromStageVersion: 0,
    });
  });

  it("rejects a stale expectedStageVersion", async () => {
    const wsId = await newWorkspace();
    const ctx = ctxFor(wsId);
    await transitionWorkspaceLifecycle(ctx, wsId, {
      toStage: "W1_PROBLEM_VALIDATION",
      expectedStageVersion: 0,
    });
    await expect(
      transitionWorkspaceLifecycle(ctx, wsId, {
        toStage: "W2_SOLUTION_VALIDATION",
        expectedStageVersion: 0,
      })
    ).rejects.toThrow(/changed; reload/i);
  });

  it("rejects skipping more than one stage and denies non-privileged members", async () => {
    const wsId = await newWorkspace();
    await expect(
      transitionWorkspaceLifecycle(ctxFor(wsId), wsId, {
        toStage: "W3_MVP_BUILD",
        expectedStageVersion: 0,
      })
    ).rejects.toThrow(/at most one stage/i);

    await expect(
      transitionWorkspaceLifecycle(ctxFor(wsId, "member"), wsId, {
        toStage: "W1_PROBLEM_VALIDATION",
        expectedStageVersion: 0,
      })
    ).rejects.toThrow(/founder|admin|privilege/i);
  });

  it("refuses to transition a different workspace than the caller's", async () => {
    const wsId = await newWorkspace();
    const otherId = await newWorkspace();
    await expect(
      transitionWorkspaceLifecycle(ctxFor(wsId), otherId, {
        toStage: "W1_PROBLEM_VALIDATION",
        expectedStageVersion: 0,
      })
    ).rejects.toThrow(/another workspace/i);
  });
});
