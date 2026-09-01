import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db } from "../models/db";
import * as schema from "../../shared/db/schema/strategy";
import { eventOutbox } from "../../shared/db/schema/integration";
import { createProject, getProject } from "../handlers/project.handler";
import {
  getProjectOperatingSetupEndpoint,
  putProjectOperatingSetupEndpoint,
  activateProjectOperatingSetupEndpoint,
} from "../strategy/handlers/project-operating-setup.handler";
import { listProjectStageTransitions } from "../strategy/services/project-stage-lifecycle.service";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";

describe("Project Operating Setup Database Contract", () => {
  it("stores one operating setup scoped to its project and workspace", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery",
    });

    await db.insert(schema.projectOperatingSetups).values({
      projectId: BigInt(project.id),
      workspaceId: BigInt(ws.workspaceId),
      status: "IN_PROGRESS",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      firstWeekActions: [],
    });

    const rows = await db
      .select()
      .from(schema.projectOperatingSetups);

    const projectRows = rows.filter((r) => r.projectId.toString() === project.id);
    expect(projectRows).toHaveLength(1);
    expect(projectRows[0]?.projectId.toString()).toBe(project.id);
    expect(projectRows[0]?.workspaceId.toString()).toBe(ws.workspaceId);

    // Assert second insert with duplicate primary key fails
    await expect(
      db.insert(schema.projectOperatingSetups).values({
        projectId: BigInt(project.id),
        workspaceId: BigInt(ws.workspaceId),
        status: "ACTIVE",
        evidenceLevel: "NONE",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
        firstWeekActions: [],
      })
    ).rejects.toThrow();
  });
});

describe("Project Operating Setup Endpoints and Lifecycle", () => {
  it("returns NOT_STARTED without inserting, then resumes a saved draft", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery Project",
    });

    // 1. Initial GET
    const initial = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(initial.status).toBe("NOT_STARTED");
    expect(initial.projectId).toBe(project.id);
    expect(initial.targetCustomer).toBeNull();

    // Verify nothing inserted in DB yet
    const dbRows = await db
      .select()
      .from(schema.projectOperatingSetups)
      .where(eq(schema.projectOperatingSetups.projectId, BigInt(project.id)));
    expect(dbRows).toHaveLength(0);

    // 2. PUT to save draft
    const saved = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "Finance teams",
      problemStatement: "Month-end takes days",
      evidenceLevel: "ONE_TO_FOUR_INTERVIEWS",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Interview 3 controllers",
      firstWeekActions: [{ title: "Prepare script" }],
    });
    expect(saved.status).toBe("IN_PROGRESS");
    expect(saved.targetCustomer).toBe("Finance teams");
    expect(saved.recommendedStage).toBe("P0_DISCOVERY");
    expect(saved.firstWeekActions).toHaveLength(1);

    // 3. Resumed GET
    const resumed = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(resumed.status).toBe("IN_PROGRESS");
    expect(resumed.targetCustomer).toBe("Finance teams");
    expect(resumed.problemStatement).toBe("Month-end takes days");
    expect(resumed.stageDurationWeeks).toBe(2);
    expect(resumed.stageTargetDate).toBeDefined();
  });

  it("activates P1 via lifecycle journal and persists commitment", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "P1 Validation Target",
    });

    const result = await activateProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "B2B finance leads",
      problemStatement: "Reconciliation is slow",
      evidenceLevel: "FIVE_PLUS_INTERVIEWS",
      selectedStage: "P1_PROBLEM_VALIDATION",
      stageDurationWeeks: 4,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Complete five interviews",
      firstWeekActions: [{ title: "List ten prospects" }],
    });

    expect(result.setup.status).toBe("ACTIVE");
    expect(result.setup.selectedStage).toBe("P1_PROBLEM_VALIDATION");
    expect(result.setup.recommendedStage).toBe("P1_PROBLEM_VALIDATION");
    expect(result.project.lifecycleStage).toBe("P1_PROBLEM_VALIDATION");

    const transitions = await listProjectStageTransitions(
      BigInt(ws.workspaceId),
      BigInt(project.id)
    );
    expect(transitions.map((row) => row.toStage)).toContain("P1_PROBLEM_VALIDATION");

    // Outbox event check
    const outboxRows = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.workspaceId, ws.workspaceId));
    const setupEvents = outboxRows.filter(
      (e) => e.eventType === "project.operating_setup.activated.v1"
    );
    expect(setupEvents).toHaveLength(1);
    expect(setupEvents[0]?.aggregateId).toBe(project.id);
  });

  it("rejects cross-workspace access with not_found or permission_denied", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    const projectA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Isolated Project",
    });

    // wsB tries to access wsA's project
    await expect(
      getProjectOperatingSetupEndpoint({
        authorization: wsA.bearerToken,
        workspaceId: wsB.workspaceId,
        id: projectA.id,
      })
    ).rejects.toThrow();

    await expect(
      putProjectOperatingSetupEndpoint({
        authorization: wsA.bearerToken,
        workspaceId: wsB.workspaceId,
        id: projectA.id,
        targetCustomer: "Hacker",
      })
    ).rejects.toThrow();
  });

  it("rejects invalid activations and rolls back cleanly without side effects", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Validation Project",
    });

    const initialOutbox = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.workspaceId, ws.workspaceId));
    const initialOutboxCount = initialOutbox.length;

    // 1. P1 with NONE evidence
    await expect(
      activateProjectOperatingSetupEndpoint({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: project.id,
        targetCustomer: "Cust",
        problemStatement: "Prob",
        evidenceLevel: "NONE",
        selectedStage: "P1_PROBLEM_VALIDATION",
        stageDurationWeeks: 4,
        weeklyReviewWeekday: 5,
        weeklyReviewTime: "16:00",
        firstWeekOutcome: "Outcome",
        firstWeekActions: [{ title: "Action 1" }],
      })
    ).rejects.toThrow(/P1 requires founder-confirmed qualifying evidence/i);

    // 2. P0 with duration 3
    await expect(
      activateProjectOperatingSetupEndpoint({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: project.id,
        targetCustomer: "Cust",
        problemStatement: "Prob",
        evidenceLevel: "NONE",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 3,
        weeklyReviewWeekday: 5,
        weeklyReviewTime: "16:00",
        firstWeekOutcome: "Outcome",
        firstWeekActions: [{ title: "Action 1" }],
      })
    ).rejects.toThrow(/stageDurationWeeks/i);

    // 3. 4 actions (over max 3)
    await expect(
      activateProjectOperatingSetupEndpoint({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: project.id,
        targetCustomer: "Cust",
        problemStatement: "Prob",
        evidenceLevel: "NONE",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
        weeklyReviewWeekday: 5,
        weeklyReviewTime: "16:00",
        firstWeekOutcome: "Outcome",
        firstWeekActions: [
          { title: "A1" },
          { title: "A2" },
          { title: "A3" },
          { title: "A4" },
        ],
      })
    ).rejects.toThrow(/firstWeekActions/i);

    // 4. Malformed review time
    await expect(
      activateProjectOperatingSetupEndpoint({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: project.id,
        targetCustomer: "Cust",
        problemStatement: "Prob",
        evidenceLevel: "NONE",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
        weeklyReviewWeekday: 5,
        weeklyReviewTime: "25:99",
        firstWeekOutcome: "Outcome",
        firstWeekActions: [{ title: "A1" }],
      })
    ).rejects.toThrow(/weeklyReviewTime/i);

    // Check that state was not modified / rolled back
    const currentSetup = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(currentSetup.status).toBe("NOT_STARTED");

    const currentProject = await getProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(currentProject.lifecycleStage).toBe("P0_DISCOVERY");

    const afterOutbox = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.workspaceId, ws.workspaceId));
    expect(afterOutbox.length).toBe(initialOutboxCount);
  });
});
