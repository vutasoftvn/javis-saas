import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess, requireFounderCommand } from "../../shared/auth/workspace-access";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";
import type { MvpSuccess } from "../../shared/contracts/mvp-response";
import {
  proposeAutomationPlan,
  getAutomationPlanProposal,
  type AutomationPlanProposalResult,
  type AutomationPlanScheduleInput,
} from "../services/automation-plan-proposal.service";

// Plan hub vận hành đợt 2 B4 — `automation.plan.propose` (T1). Agent chat gọi bằng delegation
// mang capability này; founder = danh tính trong delegation. Chỉ lưu NHÁP, không tạo lịch.

export interface ProposeAutomationPlanParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  runId?: Header<"X-COSA-Run-Id">;
  projectId: string;
  agentDeploymentId?: string;
  proposeNewAgent?: boolean;
  skillId: string;
  connectorKeys: string[];
  connectorStatus?: Record<string, string>;
  channelKind?: string;
  schedule: AutomationPlanScheduleInput;
  tokenBudgetPerRun: number;
}

export const proposeAutomationPlanApi = api(
  { expose: true, method: "POST", path: "/operations/projects/:projectId/automation-plans/proposals" },
  async (params: ProposeAutomationPlanParams): Promise<MvpSuccess<AutomationPlanProposalResult>> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId, {
      agentCapabilities: [AGENT_CAP.AUTOMATION_PLAN_PROPOSE],
    });
    return proposeAutomationPlan(
      tenantCtx,
      params.projectId,
      {
        agentDeploymentId: params.agentDeploymentId,
        proposeNewAgent: params.proposeNewAgent,
        skillId: params.skillId,
        connectorKeys: params.connectorKeys,
        connectorStatus: params.connectorStatus,
        channelKind: params.channelKind,
        schedule: params.schedule,
        tokenBudgetPerRun: params.tokenBudgetPerRun,
      },
      { runId: params.runId ?? null }
    );
  }
);

export interface GetAutomationPlanProposalParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  proposalId: string;
}

// Founder session nạp lại thẻ kế hoạch (B6) — không mở cho delegation agent.
export const getAutomationPlanProposalApi = api(
  {
    expose: true,
    method: "GET",
    path: "/operations/projects/:projectId/automation-plans/proposals/:proposalId",
  },
  async (params: GetAutomationPlanProposalParams): Promise<MvpSuccess<AutomationPlanProposalResult>> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireFounderCommand(tenantCtx, "get_automation_plan_proposal");
    return getAutomationPlanProposal(tenantCtx, params.projectId, params.proposalId);
  }
);
