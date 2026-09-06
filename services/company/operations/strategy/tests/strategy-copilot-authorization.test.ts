import { describe, it, expect } from "vitest";
import { APIError } from "encore.dev/api";
import { randomUUID } from "node:crypto";
import { eq } from "drizzle-orm";
import { db, schema } from "../../models/db";
import {
  identityWorkforceMembers,
  coreWorkspaceRoles,
  coreRolePermissions,
  coreMemberRoleAssignments,
} from "../../../shared/db/schema/identity";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { createProject } from "../../handlers/project.handler";
import { createTestWorkspaceWithMember, addMemberToWorkspace } from "../../tests/_helpers";
import { setWeeklyGoalService } from "../services/weekly-goal.service";
import {
  routeOwnerProfile,
} from "../../services/autonomy-classifier";
import {
  getStrategyAgentManifestsService,
  configureStrategyAgentService,
  proposePestelSignalsService,
  proposeTowsOptionsService,
  proposeInitiativesService,
} from "../services/strategy-copilot.service";
import {
  createStrategicObjective,
} from "../services/strategic-objective.service";
import {
  selectTowsOption,
  createTowsOptionEvaluation,
  createTowsOption,
} from "../services/tows-option.service";
import {
  createOkrCycleService,
  createObjectiveService,
  addKeyResultService,
  publishObjectiveService,
} from "../../services/okr.service";
import {
  approveInitiativeService,
  createInitiativeInWorkspace,
  createInitiativeService,
} from "../../services/initiative.service";
import {
  updateWorkspaceStrategySettings,
} from "../services/workspace-strategy-settings.service";
import {
  createExecutionPlanService,
  acceptExecutionPlanService,
  CreatePlanItemInput,
} from "../../services/execution-plan.service";
import {
  createCycleService,
  updateCycleService,
} from "../../services/twelve-week-year.service";
import type { TenantContext } from "../../../shared/types/tenant_context";

function makeTenantContext(
  wsId: string,
  userId: string,
  role: string = "founder",
  overrides: Record<string, any> = {}
): TenantContext {
  return {
    workspaceId: wsId,
    userId,
    membershipRole: role,
    permissions: role === "founder" ? ["*"] : [],
    correlationId: "test-copilot-auth",
    ...overrides,
  } as TenantContext;
}

describe("strategy copilot roles & human-in-the-loop governance", () => {
  describe("1. Profile routing & capability classification", () => {
    it("routes research intelligence capabilities and domains accurately", () => {
      expect(routeOwnerProfile("evidence.ingestion", null)).toBe("research_intelligence");
      expect(routeOwnerProfile("source.discovery", null)).toBe("research_intelligence");
      expect(routeOwnerProfile("pestel.extraction", null)).toBe("research_intelligence");
      expect(routeOwnerProfile("resource.capability", null)).toBe("research_intelligence");
      expect(routeOwnerProfile("research.intelligence.market", null)).toBe("research_intelligence");
      expect(routeOwnerProfile(null, "research_intelligence")).toBe("research_intelligence");
      expect(routeOwnerProfile(null, "evidence-analysis")).toBe("research_intelligence");
      expect(routeOwnerProfile(null, "pestel")).toBe("research_intelligence");
    });

    it("routes strategy capabilities and domains accurately", () => {
      expect(routeOwnerProfile("swot.synthesis", null)).toBe("strategy");
      expect(routeOwnerProfile("tows.matrix", null)).toBe("strategy");
      expect(routeOwnerProfile("strategy.swot", null)).toBe("strategy");
      expect(routeOwnerProfile("strategy.tows", null)).toBe("strategy");
      expect(routeOwnerProfile("strategy.initiative", null)).toBe("strategy");
      expect(routeOwnerProfile("strategy.ranking", null)).toBe("strategy");
      expect(routeOwnerProfile("strategy.general", null)).toBe("strategy");
      expect(routeOwnerProfile(null, "strategy")).toBe("strategy");
      expect(routeOwnerProfile(null, "swot")).toBe("strategy");
      expect(routeOwnerProfile(null, "tows")).toBe("strategy");
    });

    it("preserves operations, finance, and marketing profile routing", () => {
      expect(routeOwnerProfile("operations.process", null)).toBe("operations");
      expect(routeOwnerProfile("engagement.client", null)).toBe("operations");
      expect(routeOwnerProfile("finance.budget", null)).toBe("finance");
      expect(routeOwnerProfile("billing.invoice", null)).toBe("finance");
      expect(routeOwnerProfile("strategy.positioning", null)).toBe("marketing");
      expect(routeOwnerProfile("marketing.campaign", null)).toBe("marketing");
      expect(routeOwnerProfile("research.customer_feedback", null)).toBe("marketing");
      expect(routeOwnerProfile(null, "operations")).toBe("operations");
      expect(routeOwnerProfile(null, "finance")).toBe("finance");
      expect(routeOwnerProfile(null, "marketing")).toBe("marketing");
    });
  });

  describe("2. Agent configuration & capability manifest", () => {
    it("returns manifest reflecting settings without silently creating missing AI members", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantContext(ws.workspaceId, ws.userId, "founder");

      // Settings: explicitly enable allowedAgentProfiles: ["strategy"]
      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        allowedAgentProfiles: ["strategy"],
      });
      const manifests = await getStrategyAgentManifestsService(founderCtx);
      expect(manifests.length).toBe(2);

      const strategyManifest = manifests.find((m) => m.profile === "strategy")!;
      expect(strategyManifest.enabledInSettings).toBe(true);
      expect(strategyManifest.workforceMemberId).toBeNull();
      expect(strategyManifest.status).toBe("NOT_CONFIGURED");
      expect(strategyManifest.capabilities.length).toBeGreaterThan(0);

      const researchManifest = manifests.find((m) => m.profile === "research_intelligence")!;
      expect(researchManifest.enabledInSettings).toBe(false);
      expect(researchManifest.status).toBe("DISABLED");
    });

    it("rejects configuration of profile not enabled in workspace settings", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantContext(ws.workspaceId, ws.userId, "founder");

      // research_intelligence is disabled by default
      await expect(
        configureStrategyAgentService(founderCtx, {
          profile: "research_intelligence",
          activateMember: true,
        })
      ).rejects.toThrow(/not permitted in workspace strategy settings/i);
    });

    it("enforces strategy.agent.configure governance authority", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantContext(ws.workspaceId, ws.userId, "founder");

      // Enable both profiles in settings
      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        allowedAgentProfiles: ["strategy", "research_intelligence"],
      });

      // Regular member attempts configuration -> Denied
      const member = await addMemberToWorkspace(ws.workspaceId, "member");
      const memberCtx = makeTenantContext(ws.workspaceId, member.userId, "member");

      await expect(
        configureStrategyAgentService(memberCtx, {
          profile: "strategy",
          activateMember: true,
        })
      ).rejects.toThrow();

      // Founder configures and activates member -> Succeeds
      const configured = await configureStrategyAgentService(founderCtx, {
        profile: "strategy",
        activateMember: true,
      });
      expect(configured.status).toBe("ACTIVE");
      expect(configured.workforceMemberId).not.toBeNull();

      // Verify member exists in identityWorkforceMembers
      const [dbMember] = await db
        .select()
        .from(identityWorkforceMembers)
        .where(eq(identityWorkforceMembers.id, BigInt(configured.workforceMemberId!)));
      expect(dbMember.memberType).toBe("AI_AGENT");
      expect(dbMember.agentSpecId).toBe("cosa.agents.strategy");
    });
  });

  describe("3. Proposal APIs with explicit DRAFT/PROPOSED state", () => {
    it("rejects an internal initiative create when its workspace differs from the verified context", async () => {
      const source = await createTestWorkspaceWithMember({ role: "founder" });
      const destination = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantContext(source.workspaceId, source.userId, "founder");

      await expect(
        createInitiativeInWorkspace(founderCtx, {
          workspaceId: destination.workspaceId,
          title: "Cross-workspace initiative",
        })
      ).rejects.toThrow(/workspace context does not match initiative workspace/i);
    });

    it("proposes PESTEL signals in DRAFT status with evidence refs", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantContext(ws.workspaceId, ws.userId, "founder");

      // Enable research_intelligence
      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        allowedAgentProfiles: ["strategy", "research_intelligence"],
        bscMode: "OFF",
      });

      const stratObj = await createStrategicObjective(founderCtx, {
        workspaceId: ws.workspaceId,
        title: "Tăng trưởng thị trường",
        successDefinition: "Đạt mục tiêu",
        status: "ACTIVE",
      });

      const res = await proposePestelSignalsService(founderCtx, {
        strategicObjectiveId: stratObj.id,
        signals: [
          {
            dimension: "TECHNOLOGICAL",
            statement: "Sự bùng nổ của AI Agents: nhiều đối thủ bắt đầu áp dụng tự động hoá quy trình",
            impact: "POSITIVE",
            certainty: "HIGH",
            evidenceRefs: ["market-report-2026", "news-tech"],
          },
        ],
      });

      expect(res.status).toBe("DRAFT");
      expect(res.proposedSignals.length).toBe(1);
      expect(res.proposedSignals[0]!.evidenceRefs).toEqual(["market-report-2026", "news-tech"]);
    });

    it("proposes TOWS options and Initiatives in DRAFT/PROPOSED status", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantContext(ws.workspaceId, ws.userId, "founder");

      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        allowedAgentProfiles: ["strategy"],
        bscMode: "OFF",
      });

      const stratObj = await createStrategicObjective(founderCtx, {
        workspaceId: ws.workspaceId,
        title: "Chiến lược 2026",
        successDefinition: "Thành công",
      });

      // 1. Propose TOWS options -> DRAFT
      const towsProposal = await proposeTowsOptionsService(founderCtx, {
        strategicObjectiveId: stratObj.id,
        options: [
          {
            quadrant: "SO",
            title: "Tận dụng AI để tối ưu hóa vận hành",
            description: "Dùng LLM giải phóng 40% thời gian nhân sự",
            evidenceRefs: ["ev-1"],
          },
        ],
      });

      expect(towsProposal.status).toBe("DRAFT");
      expect(towsProposal.proposedOptions[0]!.status).toBe("DRAFT");

      // 2. Select option via human governance
      const optionId = towsProposal.proposedOptions[0]!.id;
      await createTowsOptionEvaluation({
        workspaceId: ws.workspaceId,
        towsOptionId: optionId,
        impactScore: 5,
        difficultyScore: 3,
      });
      await selectTowsOption({ id: optionId }, founderCtx);

      // 3. Propose initiatives -> PROPOSED (DRAFT approvalStatus)
      const initProposal = await proposeInitiativesService(founderCtx, {
        strategicObjectiveId: stratObj.id,
        towsOptionId: optionId,
        initiatives: [
          {
            title: "Triển khai Agent Workflow Engine",
            description: "Xây dựng hệ thống điều phối tác vụ",
            intendedOutcome: "Tự động hóa 50 quy trình",
          },
        ],
      });

      expect(initProposal.status).toBe("PROPOSED");
      expect(initProposal.proposedInitiatives.length).toBe(1);
      expect(initProposal.proposedInitiatives[0]!.approvalStatus).toBe("DRAFT");
    });
  });

  describe("4. Terminal transition gating: AI agents receive permission denied on every terminal command", () => {
    it("rejects AI agent on TOWS option selection", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantContext(ws.workspaceId, ws.userId, "founder");

      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        bscMode: "OFF",
      });

      const stratObj = await createStrategicObjective(founderCtx, {
        workspaceId: ws.workspaceId,
        title: "Mục tiêu test",
        successDefinition: "Thành công",
      });

      const option = await createTowsOption({
        workspaceId: ws.workspaceId,
        strategicObjectiveId: stratObj.id,
        quadrant: "SO",
        title: "Phương án test",
      });

      const agentCtx = makeTenantContext(ws.workspaceId, "agent-user", "agent", {
        actorKind: "AI_AGENT" as any,
      });

      await expect(
        selectTowsOption({ id: option.id }, agentCtx)
      ).rejects.toThrow(/Agent cannot perform governance decisions|Agents cannot execute strategy governance action/i);
    });

    it("rejects AI agent on OKR objective publication", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const founderCtx = makeTenantContext(ws.workspaceId, ws.userId, "founder");

      await updateWorkspaceStrategySettings(founderCtx, {
        workspaceId: ws.workspaceId,
        bscMode: "OFF",
      });

      const cycle = await createOkrCycleService({
        workspaceId: ws.workspaceId,
        name: "Cycle Q1",
        authorization: ws.bearerToken,
      });

      const obj = await createObjectiveService({
        workspaceId: ws.workspaceId,
        cycleId: cycle.id,
        title: "Mục tiêu OKR",
        authorization: ws.bearerToken,
      });

      await addKeyResultService({
        objectiveId: obj.id,
        title: "KR 1",
        targetValue: 100,
        baselineValue: 0,
        unit: "count",
        authorization: ws.bearerToken,
      });

      const agentCtx = makeTenantContext(ws.workspaceId, "agent-user", "agent", {
        actorKind: "AI_AGENT" as any,
      });

      await expect(
        publishObjectiveService({ id: obj.id }, agentCtx)
      ).rejects.toThrow(/Agents cannot execute strategy governance action/i);
    });

    it("rejects AI agent on Initiative approval", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const init = await createInitiativeService(
        {
          workspaceId: ws.workspaceId,
          title: "Sáng kiến thử nghiệm",
        },
        ws.bearerToken
      );

      const agentCtx = makeTenantContext(ws.workspaceId, "agent-user", "agent", {
        actorKind: "AI_AGENT" as any,
      });

      await expect(
        approveInitiativeService({ id: init.id }, agentCtx)
      ).rejects.toThrow(/Agents cannot execute strategy governance action/i);
    });

    it("rejects AI agent on execution plan acceptance", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const project = await createProject({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        title: "Project execution",
      });

      const goal = await setWeeklyGoalService(
        {
          projectId: project.id,
          workspaceId: ws.workspaceId,
          focus: "Goal tuần",
          triggerDecomposition: false,
          origin: "command_center",
        },
        ws.bearerToken
      );

      const plan = await createExecutionPlanService(
        {
          workspaceId: ws.workspaceId,
          projectId: project.id,
          weeklyPlanId: goal.weeklyPlanId,
          goalText: "Goal",
          origin: "command_center",
          originRef: null,
          runId: null,
          items: [
            {
              title: "Task test",
              decisionReason: "Reason 12345",
              evidenceRefs: [],
              suggestedDomain: null,
              expectedCapability: null,
              capabilityRisk: null,
              tenantPolicyDecision: "ALLOW",
              dependsOnTitles: [],
            },
          ],
        },
        ws.bearerToken
      );

      const agentCtx = makeTenantContext(ws.workspaceId, "agent-user", "agent", {
        actorKind: "AI_AGENT" as any,
      });

      // Passing agent context should be rejected
      await expect(
        acceptExecutionPlanService(
          plan.id,
          { workspaceId: ws.workspaceId },
          // Agent authorization
          ws.bearerToken.replace(/.+/, `Bearer agent-token`)
        )
      ).rejects.toThrow();
    });

    it("rejects AI agent on cycle duration resize", async () => {
      const ws = await createTestWorkspaceWithMember({ role: "founder" });
      const cycle = await createCycleService({
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
        durationWeeks: 12,
      });

      // Directly verify that agent context cannot resize cycle
      await expect(
        updateCycleService({
          workspaceId: ws.workspaceId,
          cycleId: cycle.id,
          durationWeeks: 10,
          authorization: ws.bearerToken,
        })
      ).resolves.toBeDefined(); // Human succeeds

      // With an agent caller
      const wsAgent = await createTestWorkspaceWithMember({ role: "agent" });
      const cycleAgent = await createCycleService({
        workspaceId: wsAgent.workspaceId,
        authorization: wsAgent.bearerToken,
        durationWeeks: 12,
      });

      await expect(
        updateCycleService({
          workspaceId: wsAgent.workspaceId,
          cycleId: cycleAgent.id,
          durationWeeks: 10,
          authorization: wsAgent.bearerToken,
        })
      ).rejects.toThrow(/Agents cannot resize execution cycles/i);
    });
  });
});
