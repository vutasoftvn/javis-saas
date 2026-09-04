import { describe, it, expect } from "vitest";
import { and, eq } from "drizzle-orm";
import { db } from "../models/db";
import * as schema from "../../shared/db/schema/strategy";
import { projects } from "../../shared/db/schema/operations";
import { eventOutbox } from "../../shared/db/schema/integration";
import { generateSnowflake } from "../../shared/services/snowflake.service";
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

  it("clears stageTargetDate when a draft explicitly clears stageDurationWeeks", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Clear draft duration",
    });
    const initial = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
    });
    expect(initial.stageTargetDate).not.toBeNull();

    const cleared = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      stageDurationWeeks: null,
    });

    expect(cleared.stageDurationWeeks).toBeNull();
    expect(cleared.stageTargetDate).toBeNull();
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

  it("prioritizes the target project's policy and ignores another project's policy", async () => {
    const ws = await createTestWorkspaceWithMember();
    const projectB = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Project with an allow policy",
    });
    const projectA = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Later project with blocking policy",
    });
    await db.insert(schema.projectStageTransitionPolicies).values([
      {
        id: generateSnowflake(),
        workspaceId: BigInt(ws.workspaceId),
        projectId: null,
        fromStage: "P0_DISCOVERY",
        toStage: "P1_PROBLEM_VALIDATION",
        allowed: false,
        policyVersion: "workspace-block-v7",
      },
      {
        id: generateSnowflake(),
        workspaceId: BigInt(ws.workspaceId),
        projectId: BigInt(projectB.id),
        fromStage: "P0_DISCOVERY",
        toStage: "P1_PROBLEM_VALIDATION",
        allowed: true,
        policyVersion: "project-b-allow-v4",
      },
      {
        id: generateSnowflake(),
        workspaceId: BigInt(ws.workspaceId),
        projectId: BigInt(projectA.id),
        fromStage: "P0_DISCOVERY",
        toStage: "P1_PROBLEM_VALIDATION",
        allowed: false,
        policyVersion: "project-a-block-v3",
      },
    ]);

    const result = await activateProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: projectB.id,
      targetCustomer: "Finance controllers",
      problemStatement: "Close reporting is slow",
      evidenceLevel: "FIVE_PLUS_INTERVIEWS",
      selectedStage: "P1_PROBLEM_VALIDATION",
      stageDurationWeeks: 3,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "15:00",
      firstWeekOutcome: "Validate the close workflow",
      firstWeekActions: [{ title: "Interview two controllers" }],
    });

    expect(result.project.lifecycleStage).toBe("P1_PROBLEM_VALIDATION");
    const [journal] = await listProjectStageTransitions(
      BigInt(ws.workspaceId),
      BigInt(projectB.id),
    );
    expect(journal?.policyVersion).toBe("project-b-allow-v4");
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

describe("roundStartDate + stageTargetDate", () => {
  it("activate không có roundStartDate -> mặc định Thứ Hai kế tiếp, target = start + weeks*7d", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Round start default",
    });

    const res = await activateProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "CFOs",
      problemStatement: "Reconciliation pain",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to 5 CFOs",
      firstWeekActions: [{ title: "List 10 prospects" }],
    });

    const start = new Date(res.setup.roundStartDate!);
    expect(start.getUTCDay()).toBe(1); // Monday
    const target = new Date(res.setup.stageTargetDate!);
    expect(target.getTime() - start.getTime()).toBe(2 * 7 * 24 * 60 * 60 * 1000);
  });

  it("activate với roundStartDate rõ ràng -> giữ nguyên (đầu ngày UTC)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Round start explicit",
    });

    const res = await activateProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "CFOs",
      problemStatement: "Reconciliation pain",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 1,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to 5 CFOs",
      firstWeekActions: [{ title: "List 10 prospects" }],
      roundStartDate: futureIsoDate(21, "09:30:00.000"),
    });

    expect(res.setup.roundStartDate).toBe(futureIsoDate(21, "00:00:00.000"));
  });

  it("roundStartDate ngoài cửa sổ [hôm nay-1d, hôm nay+60d] -> invalidArgument", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Round start out of window",
    });

    await expect(
      activateProjectOperatingSetupEndpoint({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: project.id,
        targetCustomer: "CFOs",
        problemStatement: "x",
        evidenceLevel: "NONE",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
        weeklyReviewWeekday: 5,
        weeklyReviewTime: "16:00",
        firstWeekOutcome: "y",
        firstWeekActions: [{ title: "z" }],
        roundStartDate: "2020-01-01T00:00:00.000Z",
      })
    ).rejects.toThrow(/roundStartDate/);
  });
});

describe("activate populates projects.start_date", () => {
  it("set start_date = roundStartDate khi project chưa có start_date", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Start date backfill",
    });

    const res = await activateProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "CFOs",
      problemStatement: "pain",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to 5 CFOs",
      firstWeekActions: [{ title: "List 10 prospects" }],
    });

    expect(res.project.startDate).toBe(res.setup.roundStartDate);
  });

  it("không ghi đè start_date đã có", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Start date preserved",
    });

    // createProject không nhận start_date; preset trực tiếp cho fixture.
    await db
      .update(projects)
      .set({ startDate: new Date("2026-01-01T00:00:00.000Z") })
      .where(
        and(
          eq(projects.id, BigInt(project.id)),
          eq(projects.workspaceId, BigInt(ws.workspaceId))
        )
      );

    const res = await activateProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "CFOs",
      problemStatement: "pain",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to 5 CFOs",
      firstWeekActions: [{ title: "List 10 prospects" }],
    });

    expect(res.project.startDate).toBe("2026-01-01T00:00:00.000Z");
  });
});

describe("saveProjectOperatingSetup roundStartDate (PUT save path)", () => {
  it("bỏ qua roundStartDate -> giữ mốc đã lưu và tính lại stageTargetDate từ mốc đó", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "PUT keep round start",
    });

    const anchorIso = futureIsoDate(14, "00:00:00.000");
    const first = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      roundStartDate: anchorIso,
    });
    expect(first.roundStartDate).toBe(anchorIso);

    // Lần lưu sau không gửi roundStartDate -> mốc giữ nguyên; target neo lại
    // vào chính mốc đó (mốc + 1 tuần cho durationWeeks = 1).
    const next = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      stageDurationWeeks: 1,
    });
    expect(next.roundStartDate).toBe(anchorIso);
    const start = new Date(next.roundStartDate!);
    const target = new Date(next.stageTargetDate!);
    expect(target.getTime() - start.getTime()).toBe(7 * 24 * 60 * 60 * 1000);
  });

  it("gửi lại đúng mốc đã lưu vẫn được chấp nhận kể cả khi mốc nằm ngoài cửa sổ 60 ngày", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "PUT resume out of window",
    });

    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      roundStartDate: futureIsoDate(10, "00:00:00.000"),
    });

    // Giả lập setup dở dang được resume sau >60 ngày: đẩy mốc đã lưu về quá khứ xa.
    const staleAnchor = new Date("2020-01-06T00:00:00.000Z");
    await db
      .update(schema.projectOperatingSetups)
      .set({ roundStartDate: staleAnchor })
      .where(
        and(
          eq(schema.projectOperatingSetups.projectId, BigInt(project.id)),
          eq(schema.projectOperatingSetups.workspaceId, BigInt(ws.workspaceId))
        )
      );

    // Gửi lại ĐÚNG mốc đã lưu (cùng đầu ngày UTC) -> không ném, giá trị giữ nguyên.
    const resumed = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      roundStartDate: "2020-01-06T09:30:00.000Z",
      stageDurationWeeks: 2,
    });
    expect(resumed.roundStartDate).toBe("2020-01-06T00:00:00.000Z");
  });

  it("mốc mới thực sự nằm ngoài cửa sổ 60 ngày -> vẫn invalidArgument", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "PUT new out of window rejects",
    });

    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      roundStartDate: futureIsoDate(10, "00:00:00.000"),
    });

    await expect(
      putProjectOperatingSetupEndpoint({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: project.id,
        roundStartDate: "2020-01-01T00:00:00.000Z",
      })
    ).rejects.toThrow(/roundStartDate/);
  });
});

describe("aiSuggestion fields on ProjectOperatingSetupView", () => {
  it("trả về null cho aiSuggestionStatus/aiSuggestedOutcome/aiSuggestedActions khi chưa từng gọi AI suggestion", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery",
    });

    const view = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });

    expect(view.aiSuggestionStatus).toBeNull();
    expect(view.aiSuggestedOutcome).toBeNull();
    expect(view.aiSuggestedActions).toBeNull();
  });
});

// Tạo ISO string ở đầu ngày UTC + `offsetDays` ngày so với hôm nay, gắn giờ tuỳ ý.
// Dùng offset động để test không phụ thuộc ngày chạy (cửa sổ hợp lệ là +60 ngày).
function futureIsoDate(offsetDays: number, time: string): string {
  const now = new Date();
  const day = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + offsetDays)
  );
  return `${day.toISOString().slice(0, 10)}T${time}Z`;
}
