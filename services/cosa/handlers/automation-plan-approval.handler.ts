import { api, Header } from "encore.dev/api";
import { approveAutomationPlan } from "../services/automation-plan-approval.service";
import type { ScheduleDefinitionResponse } from "./workspace-schedule.handler";

// Plan hub vận hành đợt 2 B5 (Task 6) — Flutter (Task 7) gọi endpoint này khi founder bấm Duyệt
// thẻ kế hoạch. `Authorization` là phiên đăng nhập của chính founder (KHÔNG phải delegation
// agent) — được forward nguyên vẹn sang services/company (approve + link-schedule) vì chưa có
// cơ chế service-to-service riêng cho đường ghi hẹp này (xem task-6-brief.md).
//
// `projectId` không nằm trong path (brief chỉ định `/cosa/workspaces/:workspaceId/automation-
// plans/:proposalId/approve`, không có projectId) nhưng company's route theo đúng B4 lại cần
// project scope — quyết định controller: nhận `projectId` như body field bắt buộc (Flutter đã có
// sẵn projectId trong context khi hiển thị thẻ kế hoạch của Project).
export interface ApproveAutomationPlanParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  proposalId: string;
  projectId: string;
}

export const approveAutomationPlanEndpoint = api(
  { method: "POST", path: "/cosa/workspaces/:workspaceId/automation-plans/:proposalId/approve", expose: true },
  async (params: ApproveAutomationPlanParams): Promise<ScheduleDefinitionResponse> => {
    const schedule = await approveAutomationPlan({
      organizationId: params.workspaceId,
      projectId: params.projectId,
      proposalId: params.proposalId,
      authorization: params.authorization,
    });
    return schedule;
  }
);
