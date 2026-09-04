import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  createExecutionPlanService,
  listExecutionPlansService,
  getExecutionPlanService,
  patchExecutionPlanItemService,
  CreatePlanItemInput,
} from "../services/execution-plan.service";
import { setWeeklyGoalService } from "../strategy/services/weekly-goal.service";

const { executionPlans } = schema;

async function seedProject() {
  const ws = await createTestWorkspaceWithMember();
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "WGA plan CRUD project",
  });
  return { workspaceId: ws.workspaceId, projectId: project.id, auth: ws.bearerToken };
}

function item(over: Partial<CreatePlanItemInput> = {}): CreatePlanItemInput {
  return {
    title: over.title ?? "Soạn SOP onboarding",
    decisionReason: over.decisionReason ?? "Chuẩn hoá quy trình onboarding tuần đầu",
    evidenceRefs: over.evidenceRefs ?? ["note-1"],
    suggestedDomain: over.suggestedDomain ?? "operations",
    expectedCapability:
      over.expectedCapability === undefined ? "operations.sop.draft" : over.expectedCapability,
    capabilityRisk: over.capabilityRisk ?? "LOW",
    tenantPolicyDecision: over.tenantPolicyDecision ?? null,
    dependsOnTitles: over.dependsOnTitles ?? [],
    priority: over.priority,
  };
}

function base(ctx: { workspaceId: string; projectId: string }) {
  return {
    workspaceId: ctx.workspaceId,
    projectId: ctx.projectId,
    weeklyPlanId: null,
    goalText: "Chốt 3 phỏng vấn khách hàng",
    origin: "command_center" as const,
    originRef: null,
    runId: null,
  };
}

describe("createExecutionPlanService", () => {
  it("classifies a LOW read/draft item as AUTO by default", async () => {
    const ctx = await seedProject();
    const plan = await createExecutionPlanService({ ...base(ctx), items: [item()] }, ctx.auth);
    expect(plan.status).toBe("draft");
    expect(plan.items[0]!.autonomyClass).toBe("AUTO");
    expect(plan.items[0]!.ownerAgentProfile).toBe("operations");
  });

  it("classifies a no-capability item as FOUNDER_ONLY", async () => {
    const ctx = await seedProject();
    const plan = await createExecutionPlanService(
      { ...base(ctx), items: [item({ title: "Phỏng vấn 3 khách hàng", expectedCapability: null })] },
      ctx.auth
    );
    expect(plan.items[0]!.autonomyClass).toBe("FOUNDER_ONLY");
    expect(plan.items[0]!.ownerAgentProfile).toBeNull();
  });

  it("classifies a forbidden capability as NEEDS_APPROVAL even with ALLOW policy", async () => {
    const ctx = await seedProject();
    const plan = await createExecutionPlanService(
      {
        ...base(ctx),
        items: [
          item({
            title: "Gửi email cho khách",
            expectedCapability: "engagement.message.send",
            capabilityRisk: "MEDIUM",
            tenantPolicyDecision: "ALLOW",
          }),
        ],
      },
      ctx.auth
    );
    expect(plan.items[0]!.autonomyClass).toBe("NEEDS_APPROVAL");
  });

  it("resolves dependsOnTitles to sibling item ids", async () => {
    const ctx = await seedProject();
    const plan = await createExecutionPlanService(
      {
        ...base(ctx),
        items: [item({ title: "A" }), item({ title: "B", dependsOnTitles: ["A"] })],
      },
      ctx.auth
    );
    const a = plan.items.find((i) => i.title === "A")!;
    const b = plan.items.find((i) => i.title === "B")!;
    expect(b.dependsOnItemIds).toEqual([a.id]);
  });

  it("supersedes an existing draft plan for the same weeklyPlanId", async () => {
    const ctx = await seedProject();
    const goal = await setWeeklyGoalService(
      {
        projectId: ctx.projectId,
        workspaceId: ctx.workspaceId,
        focus: "Goal",
        triggerDecomposition: false,
        origin: "command_center",
      },
      ctx.auth
    );
    const p1 = await createExecutionPlanService(
      { ...base(ctx), weeklyPlanId: goal.weeklyPlanId, items: [item()] },
      ctx.auth
    );
    const p2 = await createExecutionPlanService(
      { ...base(ctx), weeklyPlanId: goal.weeklyPlanId, items: [item()] },
      ctx.auth
    );
    const [old] = await db.select().from(executionPlans).where(eq(executionPlans.id, BigInt(p1.id)));
    expect(old!.status).toBe("superseded");
    expect(p2.status).toBe("draft");
  });

  it("rejects a plan with no items", async () => {
    const ctx = await seedProject();
    await expect(
      createExecutionPlanService({ ...base(ctx), items: [] }, ctx.auth)
    ).rejects.toThrow();
  });
});

describe("listExecutionPlansService / getExecutionPlanService", () => {
  it("lists by project and filters by status", async () => {
    const ctx = await seedProject();
    await createExecutionPlanService({ ...base(ctx), items: [item()] }, ctx.auth);
    const drafts = await listExecutionPlansService(
      { workspaceId: ctx.workspaceId, projectId: ctx.projectId, status: "draft" },
      ctx.auth
    );
    expect(drafts.length).toBe(1);
    const accepted = await listExecutionPlansService(
      { workspaceId: ctx.workspaceId, projectId: ctx.projectId, status: "accepted" },
      ctx.auth
    );
    expect(accepted.length).toBe(0);
  });

  it("get returns 404 for a cross-workspace plan id", async () => {
    const ctx = await seedProject();
    const other = await seedProject();
    const plan = await createExecutionPlanService({ ...base(ctx), items: [item()] }, ctx.auth);
    await expect(
      getExecutionPlanService(plan.id, other.workspaceId, other.auth)
    ).rejects.toThrow();
  });
});

describe("patchExecutionPlanItemService", () => {
  it("drop marks the item status as dropped", async () => {
    const ctx = await seedProject();
    const plan = await createExecutionPlanService({ ...base(ctx), items: [item()] }, ctx.auth);
    const r = await patchExecutionPlanItemService(
      plan.id,
      plan.items[0]!.id,
      { drop: true },
      ctx.workspaceId,
      ctx.auth
    );
    expect(r.status).toBe("dropped");
  });

  it("blocks raising a forbidden-capability item to AUTO", async () => {
    const ctx = await seedProject();
    const plan = await createExecutionPlanService(
      {
        ...base(ctx),
        items: [
          item({
            title: "Gửi email",
            expectedCapability: "engagement.message.send",
            capabilityRisk: "MEDIUM",
          }),
        ],
      },
      ctx.auth
    );
    await expect(
      patchExecutionPlanItemService(
        plan.id,
        plan.items[0]!.id,
        { autonomyClass: "AUTO" },
        ctx.workspaceId,
        ctx.auth
      )
    ).rejects.toThrow();
  });

  it("blocks raising to AUTO when the class came from tenant_policy", async () => {
    const ctx = await seedProject();
    const plan = await createExecutionPlanService(
      {
        ...base(ctx),
        items: [item({ expectedCapability: "operations.sop.draft", tenantPolicyDecision: "REQUIRE_APPROVAL" })],
      },
      ctx.auth
    );
    expect(plan.items[0]!.autonomyClass).toBe("NEEDS_APPROVAL");
    await expect(
      patchExecutionPlanItemService(
        plan.id,
        plan.items[0]!.id,
        { autonomyClass: "AUTO" },
        ctx.workspaceId,
        ctx.auth
      )
    ).rejects.toThrow();
  });

  it("allows downgrading to FOUNDER_ONLY and records founder_override source", async () => {
    const ctx = await seedProject();
    const plan = await createExecutionPlanService({ ...base(ctx), items: [item()] }, ctx.auth);
    const r = await patchExecutionPlanItemService(
      plan.id,
      plan.items[0]!.id,
      { autonomyClass: "FOUNDER_ONLY" },
      ctx.workspaceId,
      ctx.auth
    );
    expect(r.autonomyClass).toBe("FOUNDER_ONLY");
    expect(r.autonomyClassSource).toBe("founder_override");
  });
});
