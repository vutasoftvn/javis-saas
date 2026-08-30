import { describe, it, expect } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../models/db";
import { identityWorkspaces } from "../../shared/db/schema/identity";
import { projects } from "../../shared/db/schema/operations";
import {
  projectStageTransitionPolicies,
  projectStageTransitions,
} from "../../shared/db/schema/strategy";
import { eventOutbox } from "../../shared/db/schema/integration";
import { transitionProjectStage } from "../strategy/services/project-stage-lifecycle.service";
import { transitionVentureStage } from "../strategy/services/stage-lifecycle.service";
import {
  getStageContext,
  transitionProjectStageEndpoint,
} from "../strategy/handlers/project-stage.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import { generateSnowflake } from "../../shared/services/snowflake.service";

async function makeProject(workspaceId: bigint, stage = "P0_DISCOVERY"): Promise<bigint> {
  const id = generateSnowflake();
  await db.insert(projects).values({
    id,
    workspaceId,
    title: "Test Project",
    lifecycleStage: stage,
    stageEnteredAt: new Date(),
  });
  return id;
}

describe("project stage lifecycle (M4 §3)", () => {
  it("default lifecycle_stage là P0_DISCOVERY, độc lập stage_version", async () => {
    const fx = await createTestWorkspaceWithMember();
    const pid = await makeProject(BigInt(fx.workspaceId));
    const [row] = await db.select().from(projects).where(eq(projects.id, pid));
    expect(row.lifecycleStage).toBe("P0_DISCOVERY");
    expect(row.stageVersion).toBe(0);
  });

  it("same-stage ⇒ no-op, không ghi journal", async () => {
    const fx = await createTestWorkspaceWithMember();
    const pid = await makeProject(BigInt(fx.workspaceId));

    const r = await transitionProjectStage({
      workspaceId: BigInt(fx.workspaceId),
      projectId: pid,
      toStage: "P0_DISCOVERY",
      reason: "noop",
      actorRole: "founder",
    });
    expect(r.noop).toBe(true);
    const jr = await db
      .select()
      .from(projectStageTransitions)
      .where(eq(projectStageTransitions.projectId, pid));
    expect(jr.length).toBe(0);
  });

  it("thiếu policy ⇒ chặn autonomous; founder đi tiếp + ghi provenance + bump version + outbox", async () => {
    const fx = await createTestWorkspaceWithMember();
    const pid = await makeProject(BigInt(fx.workspaceId));
    const wsId = BigInt(fx.workspaceId);

    await expect(
      transitionProjectStage({
        workspaceId: wsId,
        projectId: pid,
        toStage: "P1_PROBLEM_VALIDATION",
        reason: "agent",
        actorRole: "founder",
        isAutonomous: true,
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });

    const r = await transitionProjectStage({
      workspaceId: wsId,
      projectId: pid,
      toStage: "P1_PROBLEM_VALIDATION",
      reason: "founder ready",
      actorRole: "founder",
    });
    expect(r.noop).toBe(false);
    expect(r.stageVersion).toBe(1);

    const [jr] = await db
      .select()
      .from(projectStageTransitions)
      .where(eq(projectStageTransitions.projectId, pid));
    expect(jr.fromStage).toBe("P0_DISCOVERY");
    expect(jr.toStage).toBe("P1_PROBLEM_VALIDATION");
    expect(jr.stageVersionFrom).toBe(0);
    expect(jr.source).toBe("manual");

    const ob = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, pid.toString()));
    expect(ob.some((e) => e.eventType.startsWith("project.phase.changed"))).toBe(true);
  });

  it("policy allowed=false ⇒ chặn; founder override ⇒ qua, ghi overrideFlag", async () => {
    const fx = await createTestWorkspaceWithMember();
    const pid = await makeProject(BigInt(fx.workspaceId));
    const wsId = BigInt(fx.workspaceId);

    await db.insert(projectStageTransitionPolicies).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      fromStage: "P0_DISCOVERY",
      toStage: "P1_PROBLEM_VALIDATION",
      allowed: false,
    });

    await expect(
      transitionProjectStage({
        workspaceId: wsId,
        projectId: pid,
        toStage: "P1_PROBLEM_VALIDATION",
        reason: "no override",
        actorRole: "founder",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });

    await expect(
      transitionProjectStage({
        workspaceId: wsId,
        projectId: pid,
        toStage: "P1_PROBLEM_VALIDATION",
        reason: "override without ref",
        actorRole: "founder",
        override: true,
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });

    const ok = await transitionProjectStage({
      workspaceId: wsId,
      projectId: pid,
      toStage: "P1_PROBLEM_VALIDATION",
      reason: "founder override",
      actorRole: "founder",
      override: true,
      overrideApprovalRef: "APPROVAL-REF-001",
    });
    expect(ok.overrideApplied).toBe(true);
    const [jr] = await db
      .select()
      .from(projectStageTransitions)
      .where(eq(projectStageTransitions.projectId, pid));
    expect(jr.overrideFlag).toBe(true);
    expect(jr.overrideApprovalRef).toBe("APPROVAL-REF-001");
    expect(jr.policyVersion).toBe("v1");
  });

  it("independence: đổi project stage KHÔNG đổi workspace lifecycle_stage và ngược lại", async () => {
    const fx = await createTestWorkspaceWithMember();
    const wsId = BigInt(fx.workspaceId);
    const pid = await makeProject(wsId);

    // Workspace vẫn W0_IDEA ban đầu.
    let [ws] = await db.select().from(identityWorkspaces).where(eq(identityWorkspaces.id, wsId));
    expect(ws.lifecycleStage).toBe("W0_IDEA");

    // Đẩy project lên P1.
    await transitionProjectStage({
      workspaceId: wsId,
      projectId: pid,
      toStage: "P1_PROBLEM_VALIDATION",
      reason: "x",
      actorRole: "founder",
    });
    [ws] = await db.select().from(identityWorkspaces).where(eq(identityWorkspaces.id, wsId));
    expect(ws.lifecycleStage).toBe("W0_IDEA"); // workspace KHÔNG đổi

    // Đẩy workspace lên W1 (thiếu policy ⇒ founder được đi tiếp).
    await transitionVentureStage({
      workspaceId: wsId,
      toStage: "W1_PROBLEM_VALIDATION",
      reason: "y",
      actorRole: "founder",
    });
    const [p] = await db.select().from(projects).where(eq(projects.id, pid));
    expect(p.lifecycleStage).toBe("P1_PROBLEM_VALIDATION"); // project KHÔNG đổi theo workspace
  });

  it("§4/§6: GET stage-context trả cả workspace + project stage độc lập", async () => {
    const fx = await createTestWorkspaceWithMember();
    const wsId = BigInt(fx.workspaceId);
    const pid = await makeProject(wsId);

    await transitionProjectStage({
      workspaceId: wsId,
      projectId: pid,
      toStage: "P1_PROBLEM_VALIDATION",
      reason: "x",
      actorRole: "founder",
    });

    const ctx = await getStageContext({
      authorization: fx.bearerToken,
      workspaceId: fx.workspaceId,
      projectId: pid.toString(),
    });
    expect(ctx.workspace.lifecycleStage).toBe("W0_IDEA");
    expect(ctx.project?.lifecycleStage).toBe("P1_PROBLEM_VALIDATION");
    expect(ctx.project?.stageVersion).toBe(1);

    const noProj = await getStageContext({
      authorization: fx.bearerToken,
      workspaceId: fx.workspaceId,
    });
    expect(noProj.project).toBeNull();
  });

  it("§4: POST /projects/:id/stage endpoint chuyển stage (người thao tác, founder)", async () => {
    const fx = await createTestWorkspaceWithMember();
    const wsId = BigInt(fx.workspaceId);
    const pid = await makeProject(wsId);

    const r = await transitionProjectStageEndpoint({
      authorization: fx.bearerToken,
      workspaceId: fx.workspaceId,
      id: pid.toString(),
      toStage: "P1_PROBLEM_VALIDATION",
      reason: "endpoint transition",
    });
    expect(r.noop).toBe(false);
    expect(r.toStage).toBe("P1_PROBLEM_VALIDATION");
  });

  it("CAS predicate: UPDATE projects với stage_version cũ khớp 0 row", async () => {
    const fx = await createTestWorkspaceWithMember();
    const wsId = BigInt(fx.workspaceId);
    const pid = await makeProject(wsId);

    await transitionProjectStage({
      workspaceId: wsId,
      projectId: pid,
      toStage: "P1_PROBLEM_VALIDATION",
      reason: "bump",
      actorRole: "founder",
    });

    const stale = await db
      .update(projects)
      .set({ lifecycleStage: "P2_SOLUTION_VALIDATION", stageVersion: 1 })
      .where(and(eq(projects.id, pid), eq(projects.stageVersion, 0)))
      .returning({ id: projects.id });
    expect(stale.length).toBe(0);
  });
});
