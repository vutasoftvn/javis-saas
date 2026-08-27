import { describe, it, expect } from "vitest";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { createProject, listProjects } from "../../handlers/project.handler";
import { createInitiative, getInitiative } from "../../handlers/initiative.handler";
import { createOkrCycle, createObjective, addKeyResult, getObjectiveProgress } from "../../handlers/okr.handler";
import {
  createCycle,
  listCycles,
  createWeeklyPlan,
  createWeeklyCommitment,
} from "../../handlers/twelve-week-year.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("Phase 2e: Execution & Planning Chain Integration Test", () => {
  it("executes the full chain: project → initiative → OKR cycle → 12-week plan → weekly plan without linkage error", async () => {
    // 1. Setup Workspace
    const { workspaceId, authorization } = await makeAuthedWorkspace("COSA Execution Inc");

    // 2. Project
    const project = await createProject({
      authorization,
      workspaceId,
      title: "Core Platform Launch",
      description: "MVP to PMF strategic journey",
      phase: "S3_MVP_BUILD",
      strategicPriority: "P0",
    });
    expect(project.id).toBeDefined();
    expect(project.title).toBe("Core Platform Launch");

    // 3. Initiative
    const initiative = await createInitiative({
      authorization,
      workspaceId,
      title: "Self-Serve Billing & Onboarding",
    });
    expect(initiative.id).toBeDefined();

    // 4. OKR Cycle & Objectives
    const okrCycle = await createOkrCycle({
      authorization,
      workspaceId,
      name: "2026-Q3 Growth & Launch",
    });
    expect(okrCycle.id).toBeDefined();

    const objective = await createObjective({
      authorization,
      workspaceId,
      cycleId: okrCycle.id,
      title: "Achieve Initial Product-Market Fit with 50 paying teams",
    });
    expect(objective.id).toBeDefined();

    const keyResult = await addKeyResult({
      authorization,
      workspaceId,
      objectiveId: objective.id,
      title: "50 active paying customers onboarded",
      targetValue: 50,
      unit: "customers",
    });
    expect(keyResult.id).toBeDefined();
    expect(keyResult.targetValue).toBe(50);

    // 5. 12-Week Year Cycle
    const twelveWeek = await createCycle({
      authorization,
      workspaceId,
      projectId: project.id,
      theme: "Sprint to 50 Customers",
      visionStatement: "Make COSA the indispensable AI co-founder for 50 visionary founders",
      stageAtStart: "S3_MVP_BUILD",
      durationWeeks: 12,
    });
    expect(twelveWeek.id).toBeDefined();
    expect(twelveWeek.projectId).toBe(project.id);

    // 6. Weekly Plan & Weekly Commitment
    const weeklyPlan = await createWeeklyPlan({
      authorization,
      workspaceId,
      cycleId: twelveWeek.id,
      weekNo: 1,
      focus: "Customer Discovery & Conversion Funnel",
      mission: "Conduct 10 interviews and ship self-serve checkout",
    });
    expect(weeklyPlan.id).toBeDefined();
    expect(weeklyPlan.cycleId).toBe(twelveWeek.id);
    expect(weeklyPlan.weekNo).toBe(1);

    const commitment = await createWeeklyCommitment({
      authorization,
      workspaceId,
      weeklyPlanId: weeklyPlan.id,
      initiativeId: initiative.id,
      title: "Deploy Stripe billing gateway and verify webhook reconciliation",
      plannedEffort: "MEDIUM",
    });
    expect(commitment.id).toBeDefined();
    expect(commitment.weeklyPlanId).toBe(weeklyPlan.id);
    expect(commitment.initiativeId).toBe(initiative.id);

    // 7. Verify roundtrip queries across the chain
    const projectList = await listProjects({ authorization, workspaceId });
    expect(projectList.projects.some((p) => p.id === project.id)).toBe(true);

    const fetchedInitiative = await getInitiative({ authorization, workspaceId, id: initiative.id });
    expect(fetchedInitiative.id).toBe(initiative.id);

    const progress = await getObjectiveProgress({ authorization, workspaceId, objectiveId: objective.id });
    expect(progress.objectiveId).toBe(objective.id);
    expect(progress.keyResults).toHaveLength(1);

    const cycleList = await listCycles({ authorization, workspaceId });
    expect(cycleList.cycles.some((c) => c.id === twelveWeek.id)).toBe(true);
  });
});

