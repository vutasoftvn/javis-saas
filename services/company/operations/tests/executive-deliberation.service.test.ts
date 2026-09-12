import { describe, it, expect, beforeEach } from "vitest";
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
  makeTestTenantContext,
} from "./_helpers";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  createDraftDeliberation,
  frameDeliberation,
  cancelDeliberation,
  appendFounderDecision,
  getDeliberation,
} from "../services/executive-deliberation.service";
import {
  activateExecutiveRole,
} from "../services/executive-role-activation.service";
import {
  activateProjectStartupTeamMember,
} from "../services/project-startup-team.service";
import { AGENT_PROFILE_SPEC_HASH } from "../services/ai-member.service";

const { eventOutbox } = schema;

describe("Executive Deliberation Service", () => {
  let founderCtx: TenantContext;
  let memberCtx: TenantContext;
  let projectId: string;
  let foreignProjectId: string;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    projectId = ws.projectId;
    founderCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "founder",
      isAiAgent: false,
    });

    const member = await addMemberToWorkspace(ws.workspaceId, "member");
    memberCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: member.userId,
      workforceMemberId: member.userId,
      membershipRole: "member",
      isAiAgent: false,
    });

    const secondWs = await createSecondWorkspace();
    foreignProjectId = secondWs.projectId;

    // Activate finance, marketing, and customer_support in startup team, then activate CFO, CMO, and CCO
    await activateProjectStartupTeamMember(founderCtx, projectId, "finance", { expectedVersion: 1 });
    await activateProjectStartupTeamMember(founderCtx, projectId, "marketing", { expectedVersion: 1 });
    await activateProjectStartupTeamMember(founderCtx, projectId, "customer_support", { expectedVersion: 1 });
    await activateExecutiveRole(founderCtx, projectId, "cfo", { expectedVersion: 1 });
    await activateExecutiveRole(founderCtx, projectId, "cmo", { expectedVersion: 1 });
    await activateExecutiveRole(founderCtx, projectId, "cco", { expectedVersion: 1 });
  });

  it("creates a draft deliberation only with human founder authority", async () => {
    await expect(
      createDraftDeliberation(memberCtx, projectId, { title: "Q3 Strategy" })
    ).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED|FOUNDER_AUTHORIZATION_REQUIRED/);

    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Q3 Strategy",
    });
    expect(draft.id).toBeDefined();
    expect(draft.state).toBe("DRAFT");
    expect(draft.version).toBe(1);
  });

  it("frames only active roles and atomically writes the outbox", async () => {
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Runway & Growth Deliberation",
    });

    const framed = await frameDeliberation(founderCtx, projectId, draft.id, {
      expectedVersion: 1,
      question: "Should we increase paid acquisition budget by 20% given Q3 cash runway?",
      roleKeys: ["cfo", "cmo"],
      idempotencyKey: "frame-test-1",
    });

    expect(framed.state).toBe("ANALYSIS_QUEUED");
    expect(framed.activeFrameVersion).toBe(1);

    // Verify outbox has executive.deliberation.framed.v1 event
    const outboxRows = await db
      .select()
      .from(eventOutbox)
      .where(
        and(
          eq(eventOutbox.workspaceId, founderCtx.workspaceId),
          eq(eventOutbox.eventType, "executive.deliberation.framed.v1"),
          eq(eventOutbox.aggregateId, draft.id)
        )
      );
    expect(outboxRows).toHaveLength(1);
    expect(outboxRows[0].status).toBe("pending");
  });

  it("frames cco alongside cfo and atomically writes the outbox", async () => {
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Pricing Strategy",
    });
    const framed = await frameDeliberation(founderCtx, projectId, draft.id, {
      expectedVersion: 1,
      roleKeys: ["cfo", "cco"],
      question: "Có nên tăng giá gói Pro không?",
    });
    expect(framed.state).toBe("ANALYSIS_QUEUED");

    const outboxRows = await db
      .select()
      .from(eventOutbox)
      .where(
        and(
          eq(eventOutbox.workspaceId, founderCtx.workspaceId),
          eq(eventOutbox.eventType, "executive.deliberation.framed.v1"),
          eq(eventOutbox.aggregateId, draft.id)
        )
      );
    expect(outboxRows).toHaveLength(1);
    const envelope = outboxRows[0].envelope as { payload: { selectedRoles: Array<{ roleKey: string }> } };
    expect(envelope.payload.selectedRoles.map((r) => r.roleKey).sort()).toEqual(["cco", "cfo"]);
  });

  it("refuses framing when a requested role is not ACTIVE", async () => {
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Unready Role Test",
    });

    // coo is not active
    await expect(
      frameDeliberation(founderCtx, projectId, draft.id, {
        expectedVersion: 1,
        question: "Operations question",
        roleKeys: ["cfo", "coo"],
      })
    ).rejects.toThrow(/EXECUTIVE_ROLE_NOT_ACTIVE|EXECUTIVE_ROLE_NOT_AVAILABLE/);
  });

  it("enforces CAS versioning on frameDeliberation", async () => {
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "CAS Frame Test",
    });

    await expect(
      frameDeliberation(founderCtx, projectId, draft.id, {
        expectedVersion: 999, // Stale
        question: "Question",
        roleKeys: ["cfo"],
      })
    ).rejects.toThrow(/CAS_CONFLICT|stale/i);
  });

  it("cancels deliberation and prevents further state progression", async () => {
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Cancel Test",
    });

    const framed = await frameDeliberation(founderCtx, projectId, draft.id, {
      expectedVersion: 1,
      question: "Question to cancel",
      roleKeys: ["cfo"],
    });

    const cancelled = await cancelDeliberation(founderCtx, projectId, draft.id, {
      expectedVersion: framed.version,
      reason: "Priorities shifted",
    });
    expect(cancelled.state).toBe("CANCELLED");

    // Cannot append decision on cancelled deliberation
    await expect(
      appendFounderDecision(founderCtx, projectId, draft.id, {
        decisionType: "APPROVE",
        expectedVersion: cancelled.version,
      })
    ).rejects.toThrow(/CANNOT_DECIDE_CANCELLED|INVALID_STATE/);
  });

  it("appends founder decision and forbids duplicate decision", async () => {
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Decision Test",
    });

    const framed = await frameDeliberation(founderCtx, projectId, draft.id, {
      expectedVersion: 1,
      question: "Final decision test",
      roleKeys: ["cfo"],
    });

    const decision = await appendFounderDecision(founderCtx, projectId, draft.id, {
      decisionType: "APPROVE",
      expectedVersion: framed.version,
      notes: "Approved runway plan",
    });
    expect(decision.decisionType).toBe("APPROVE");

    const delib = await getDeliberation(founderCtx, projectId, draft.id);
    expect(delib.state).toBe("DECIDED");

    // Duplicate decision rejected
    await expect(
      appendFounderDecision(founderCtx, projectId, draft.id, {
        decisionType: "APPROVE",
        expectedVersion: delib.version,
      })
    ).rejects.toThrow(/EXECUTIVE_DECISION_ALREADY_RECORDED/);
  });

  it("frames chief_of_staff and coo with exact operations spec and role-specific pins", async () => {
    // 1. Activate operations profile in startup team
    await activateProjectStartupTeamMember(founderCtx, projectId, "operations", { expectedVersion: 1 });

    // 2. Activate chief_of_staff and coo
    await activateExecutiveRole(founderCtx, projectId, "chief_of_staff", { expectedVersion: 1 });
    await activateExecutiveRole(founderCtx, projectId, "coo", { expectedVersion: 1 });

    // 3. Create draft and frame with chief_of_staff and coo
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Operations & Execution Cadence",
    });

    const framed = await frameDeliberation(founderCtx, projectId, draft.id, {
      expectedVersion: 1,
      roleKeys: ["chief_of_staff", "coo"],
      question: "Làm sao để thiết lập nhịp vận hành hàng tuần giữa các team?",
    });

    expect(framed.state).toBe("ANALYSIS_QUEUED");

    // 4. Verify outbox event carries exact operations spec, hash, and role-specific pins
    const outboxRows = await db
      .select()
      .from(eventOutbox)
      .where(
        and(
          eq(eventOutbox.workspaceId, founderCtx.workspaceId),
          eq(eventOutbox.eventType, "executive.deliberation.framed.v1"),
          eq(eventOutbox.aggregateId, draft.id)
        )
      );
    expect(outboxRows).toHaveLength(1);

    interface SelectedRolePinPayload {
      roleKey: string;
      assignmentId: string;
      specId: string;
      specVersion: string;
      specHash: string;
      skillPins: string[];
    }
    const envelope = outboxRows[0].envelope as { payload: { selectedRoles: SelectedRolePinPayload[] } };
    const selectedRoles = envelope.payload.selectedRoles;
    expect(selectedRoles).toHaveLength(2);

    const cosRole = selectedRoles.find((r) => r.roleKey === "chief_of_staff");
    expect(cosRole).toBeDefined();
    expect(cosRole?.specId).toBe("cosa.agents.operations");
    expect(cosRole?.specVersion).toBe("1.3.0");
    expect(cosRole?.specHash).toBe(AGENT_PROFILE_SPEC_HASH.operations);
    expect(cosRole?.skillPins).toEqual([
      "skillpack:executive/board-protocol@1.0.0",
      "skillpack:executive/chief-of-staff@1.0.0",
    ]);

    const cooRole = selectedRoles.find((r) => r.roleKey === "coo");
    expect(cooRole).toBeDefined();
    expect(cooRole?.specId).toBe("cosa.agents.operations");
    expect(cooRole?.specVersion).toBe("1.3.0");
    expect(cooRole?.specHash).toBe(AGENT_PROFILE_SPEC_HASH.operations);
    expect(cooRole?.skillPins).toEqual([
      "skillpack:executive/coo-advisor@1.0.0",
    ]);
  });
});
