import { describe, it, expect, beforeEach, vi } from "vitest";
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
  makeTestTenantContext,
  deployWorkspaceAgentForProfile,
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
  activateWorkspaceExecutiveRole,
} from "../services/workspace-executive-role-activation.service";
import { createProjectService } from "../services/project.service";
import { transitionProjectLifecycle } from "../services/project-lifecycle.service";
import { AGENT_PROFILE_SPEC_HASH } from "../services/ai-member.service";
import { completeAllAnalyses } from "./_deliberation-helpers";

import { ADVISOR_OVERLAY_CATALOG } from "../../shared/contracts/executive-advisor-overlays.generated";
import { fetchAdvisorOverlayIdentity } from "../services/advisor-overlay.client";

// COSA Control Plane là process/app khác — tại đây chỉ giả lập phản hồi HTTP của nó bằng
// đúng catalog generated; hợp đồng HTTP thật do services/cosa/tests/advisor-overlay.test.ts phủ.
vi.mock("../services/advisor-overlay.client", () => ({
  fetchAdvisorOverlayIdentity: vi.fn(async (_ws: string, roleKey: string) => {
    const { ADVISOR_OVERLAY_CATALOG: catalog } = await import(
      "../../shared/contracts/executive-advisor-overlays.generated"
    );
    return catalog[roleKey];
  }),
}));

const { eventOutbox, projectExecutiveDeliberationFrames } = schema;

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
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "finance");
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "marketing");
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "customer_support");
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "product");
    await activateWorkspaceExecutiveRole(founderCtx, "cfo", {});
    await activateWorkspaceExecutiveRole(founderCtx, "cmo", {});
    await activateWorkspaceExecutiveRole(founderCtx, "cco", {});
    await activateWorkspaceExecutiveRole(founderCtx, "cpo", {});
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

  it("frames cpo alongside cfo and atomically writes the outbox", async () => {
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Pricing Strategy",
    });
    const framed = await frameDeliberation(founderCtx, projectId, draft.id, {
      expectedVersion: 1,
      roleKeys: ["cfo", "cpo"],
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
    expect(envelope.payload.selectedRoles.map((r) => r.roleKey).sort()).toEqual(["cfo", "cpo"]);
  });

  it("refuses framing when a requested role is not ACTIVE", async () => {
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Unready Role Test",
    });

    // coo office chưa bật → EXECUTIVE_ROLE_OFFICE_DISABLED.
    await expect(
      frameDeliberation(founderCtx, projectId, draft.id, {
        expectedVersion: 1,
        question: "Operations question",
        roleKeys: ["cfo", "coo"],
      })
    ).rejects.toThrow(/EXECUTIVE_ROLE_OFFICE_DISABLED|EXECUTIVE_ROLE_NOT_ACTIVE|EXECUTIVE_ROLE_NOT_AVAILABLE/);
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

    await frameDeliberation(founderCtx, projectId, draft.id, {
      expectedVersion: 1,
      question: "Final decision test",
      roleKeys: ["cfo"],
    });
    await completeAllAnalyses(founderCtx, projectId, draft.id);
    const awaiting = await getDeliberation(founderCtx, projectId, draft.id);
    expect(awaiting.state).toBe("AWAITING_FOUNDER");

    const decision = await appendFounderDecision(founderCtx, projectId, draft.id, {
      decisionType: "APPROVE",
      expectedVersion: awaiting.version,
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
    // 1. Deploy operations profile (V2) và kích hoạt office chief_of_staff + coo.
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "operations");
    await activateWorkspaceExecutiveRole(founderCtx, "chief_of_staff", {});
    await activateWorkspaceExecutiveRole(founderCtx, "coo", {});

    // 2. coo chỉ eligible từ P2 — chuyển Project sang P2 trước khi frame
    // (stage policy chặn role non-persistent ở stage không phù hợp).
    await transitionProjectLifecycle(founderCtx, projectId, {
      toStage: "P1_PROBLEM_VALIDATION",
      expectedStageVersion: 0,
    });
    await transitionProjectLifecycle(founderCtx, projectId, {
      toStage: "P2_SOLUTION_VALIDATION",
      expectedStageVersion: 1,
    });

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

    interface FramedPinPayload {
      roleKey: string;
      deployment: {
        projectAgentDeploymentId: string;
        profileKey: string;
        specId: string;
        specVersion: string;
        specHash: string;
      };
      overlay: {
        roleKey: string;
        overlaySpecId: string;
        overlaySpecVersion: string;
        overlaySpecHash: string;
        skillPins: Array<{ skillId: string; version: string; definitionHash: string }>;
      };
    }
    const envelope = outboxRows[0].envelope as { payload: { selectedRoles: FramedPinPayload[] } };
    const selectedRoles = envelope.payload.selectedRoles;
    expect(selectedRoles).toHaveLength(2);

    for (const roleKey of ["chief_of_staff", "coo"]) {
      const pin = selectedRoles.find((r) => r.roleKey === roleKey);
      expect(pin).toBeDefined();
      // Deployment pin: đúng profile operations của Project.
      expect(pin?.deployment.profileKey).toBe("operations");
      expect(pin?.deployment.specId).toBe("cosa.agents.operations");
      expect(pin?.deployment.specVersion).toBe("1.3.0");
      expect(pin?.deployment.specHash).toBe(AGENT_PROFILE_SPEC_HASH.operations);
      expect(pin?.deployment.projectAgentDeploymentId).toBeTruthy();
      // Overlay pin: exact identity từ catalog, tách biệt với deployment.
      const expected = ADVISOR_OVERLAY_CATALOG[roleKey];
      expect(pin?.overlay.overlaySpecId).toBe(expected.overlaySpecId);
      expect(pin?.overlay.overlaySpecVersion).toBe(expected.overlaySpecVersion);
      expect(pin?.overlay.overlaySpecHash).toBe(expected.overlayDefinitionHash);
      expect(pin?.overlay.skillPins).toEqual(expected.skillPins);
    }
    expect(
      selectedRoles.find((r) => r.roleKey === "chief_of_staff")?.overlay.skillPins.map((p) => p.skillId)
    ).toEqual(["executive.board-protocol", "executive.chief-of-staff"]);

    // Frame persist cùng pin với outbox.
    const [frameRow] = await db
      .select()
      .from(projectExecutiveDeliberationFrames)
      .where(eq(projectExecutiveDeliberationFrames.deliberationId, BigInt(draft.id)));
    expect(frameRow.selectedRoles).toEqual(selectedRoles);
  });

  it("does not write a frame or outbox event when COSA cannot return the overlay", async () => {
    vi.mocked(fetchAdvisorOverlayIdentity).mockRejectedValueOnce(
      APIError.unavailable("ADVISOR_OVERLAY_UNAVAILABLE: down")
    );
    const draft = await createDraftDeliberation(founderCtx, projectId, { title: "Overlay outage" });

    await expect(
      frameDeliberation(founderCtx, projectId, draft.id, {
        expectedVersion: 1,
        question: "Runway?",
        roleKeys: ["cfo"],
      })
    ).rejects.toThrow(/ADVISOR_OVERLAY_UNAVAILABLE/);

    const frames = await db
      .select()
      .from(projectExecutiveDeliberationFrames)
      .where(eq(projectExecutiveDeliberationFrames.deliberationId, BigInt(draft.id)));
    const outbox = await db
      .select()
      .from(eventOutbox)
      .where(and(eq(eventOutbox.eventType, "executive.deliberation.framed.v1"), eq(eventOutbox.aggregateId, draft.id)));
    expect(frames).toHaveLength(0);
    expect(outbox).toHaveLength(0);
  });

  it("rejects an overlay identity that does not match the role catalog", async () => {
    vi.mocked(fetchAdvisorOverlayIdentity).mockResolvedValueOnce({
      ...ADVISOR_OVERLAY_CATALOG.coo,
      roleKey: "cfo",
    });
    const draft = await createDraftDeliberation(founderCtx, projectId, { title: "Wrong overlay" });

    await expect(
      frameDeliberation(founderCtx, projectId, draft.id, {
        expectedVersion: 1,
        question: "Runway?",
        roleKeys: ["cfo"],
      })
    ).rejects.toThrow(/ADVISOR_OVERLAY_MISMATCH/);
  });

  it("frame deliberation for Project B fails EXECUTIVE_ROLE_PROJECT_DEPLOYMENT_INACTIVE when agent is only deployed to Project A", async () => {
    // finance Agent chỉ deploy vào Project A (projectId); Project B chưa có deployment.
    const projectB = await createProjectService(founderCtx, {
      title: "Deliberation Project B",
      creationMode: "ONBOARD_EXISTING",
      initialLifecycleStage: "P0_DISCOVERY",
      initializationRationale: "Test Project B deliberately has no P0 Core bootstrap",
    });

    const draft = await createDraftDeliberation(founderCtx, projectB.id, {
      title: "Project B Runway Review",
    });

    await expect(
      frameDeliberation(founderCtx, projectB.id, draft.id, {
        expectedVersion: 1,
        question: "Should Project B extend runway?",
        roleKeys: ["cfo"],
      })
    ).rejects.toThrow(/EXECUTIVE_ROLE_PROJECT_DEPLOYMENT_INACTIVE/);
  });

  it("frame deliberation fails EXECUTIVE_ROLE_STAGE_FORBIDDEN for a non-persistent role at a disallowed stage", async () => {
    // cco office ACTIVE + customer_support deployed, nhưng Project vẫn ở P0
    // (cco chỉ eligible từ P4) → stage policy chặn.
    const draft = await createDraftDeliberation(founderCtx, projectId, {
      title: "Customer Advisory at P0",
    });

    await expect(
      frameDeliberation(founderCtx, projectId, draft.id, {
        expectedVersion: 1,
        question: "How should we support early users?",
        roleKeys: ["cco"],
      })
    ).rejects.toThrow(/EXECUTIVE_ROLE_STAGE_FORBIDDEN/);
  });
});
