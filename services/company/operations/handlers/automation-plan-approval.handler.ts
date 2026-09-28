import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess, requireFounderCommand } from "../../shared/auth/workspace-access";
import type { MvpSuccess } from "../../shared/contracts/mvp-response";
import {
  approveAutomationPlanProposal,
  linkAutomationPlanSchedule,
  type AutomationPlanApprovalResult,
} from "../services/automation-plan-approval.service";

// Plan hub vận hành đợt 2 B5 (Task 6) — founder session bấm Duyệt (KHÔNG nhận delegation agent;
// founder tự bấm). Cả 2 endpoint chỉ mở cho phiên đăng nhập người dùng (`requireFounderCommand`),
// giống `getAutomationPlanProposalApi` (B4).

export interface ApproveAutomationPlanParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  proposalId: string;
}

export const approveAutomationPlanApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/automation-plans/proposals/:proposalId/approve",
  },
  async (params: ApproveAutomationPlanParams): Promise<MvpSuccess<AutomationPlanApprovalResult>> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireFounderCommand(tenantCtx, "approve_automation_plan_proposal");
    return approveAutomationPlanProposal(tenantCtx, params.projectId, params.proposalId);
  }
);

export interface LinkAutomationPlanScheduleParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  proposalId: string;
  scheduleId: string;
}

// services/cosa gọi ngay sau khi tạo lịch thật xong (forward Authorization của founder — chưa có
// cơ chế service-to-service riêng cho đường ghi hẹp này, xem task-6-brief.md mục thiết kế 1).
export const linkAutomationPlanScheduleApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/automation-plans/proposals/:proposalId/link-schedule",
  },
  async (
    params: LinkAutomationPlanScheduleParams
  ): Promise<MvpSuccess<{ proposalId: string; approvedScheduleId: string }>> => {
    const tenantCtx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    requireFounderCommand(tenantCtx, "link_automation_plan_schedule");
    return linkAutomationPlanSchedule(tenantCtx, params.projectId, params.proposalId, params.scheduleId);
  }
);
