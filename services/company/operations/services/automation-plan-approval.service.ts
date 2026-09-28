// Plan hub vận hành đợt 2 B5 (Task 6, phần 1) — founder duyệt MỘT LẦN thẻ kế hoạch tự động hoá
// (B4 tạo nháp) rồi services/cosa tạo lịch có snapshot uỷ quyền trước. File này CHỈ chuyển
// trạng thái nháp (`DRAFT -> APPROVED`) và ghi `approved_schedule_id` sau khi services/cosa tạo
// lịch xong — KHÔNG tạo lịch (đó là `createWorkspaceSchedule` bên services/cosa, xem
// services/cosa/services/automation-plan-approval.service.ts).
//
// Phát hiện từ review Task 5 (bắt buộc xử lý ở đây — xem task-6-brief.md):
//   1. KHÔNG tin `readiness`/`plan.connectors[].status` cũ trong nháp làm bằng chứng đã sẵn
//      sàng — nó do founder tự khai lúc đề xuất, chỉ phản ánh grant lúc đó (đã hết hạn khi
//      duyệt). Ở ĐÂY re-verify lại kênh founder (`resolveUsableChannelForFounder`, dùng danh
//      tính NGƯỜI BẤM DUYỆT — không phải người đề xuất, xem ADR mục 5) và agent deployment còn
//      ACTIVE. Việc re-verify connector (đọc `connectorAuthorizations`) thuộc về services/cosa vì
//      bảng đó sống ở đó — company không đọc được; services/cosa làm lại việc này ngay trước khi
//      tạo lịch (không tin `capabilityIds`/connector cũ nào company gửi xuống là "đã kết nối").
//   2. `plan.agentDeploymentId` trỏ tới `operations.project_agent_deployments` (V2). Nếu deployment
//      đó không còn tồn tại/không ACTIVE lúc duyệt (bị pause giữa lúc propose và approve) thì từ
//      chối rõ bằng `agent_deployment_unavailable` — KHÔNG tạo lịch với agent đã mất hiệu lực.
//      Không tự mở rộng sang `project_agent_assignments` (legacy) — đó là quyết định sản phẩm
//      riêng, ghi lại ở CONCERNS của report, không tự quyết mở rộng phạm vi (giống Task 5).
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import type { TenantContext } from "../../shared/types/tenant_context";
import { mvpItem, type MvpSuccess } from "../../shared/contracts/mvp-response";
import { resolveUsableChannelForFounder } from "../../identity/services/founder-notification-channel.service";
import { getProjectFounderDeployments } from "./founder-asset-query.service";
import {
  parseId,
  requireFounderOwner,
  type AutomationPlan,
} from "./automation-plan-proposal.service";

const { automationPlanProposals } = schema;

export interface AutomationPlanApprovalResult {
  proposalId: string;
  projectId: string;
  status: "APPROVED";
  plan: AutomationPlan;
  /** = plan.capabilityIds — lặp lại ở cấp ngoài để services/cosa không phải đọc sâu vào `plan`. */
  capabilityIds: string[];
  /** Founder SỞ HỮU LỊCH = người bấm duyệt (có thể khác người đề xuất nháp). */
  founderMemberId: string;
  founderUserId: string;
  decidedAt: string;
}

function invalidScheduleId(message: string): APIError {
  return APIError.invalidArgument(`automation_plan_link_invalid: ${message}`);
}

function toApprovalResult(
  row: typeof automationPlanProposals.$inferSelect,
  founderMemberId: string,
  founderUserId: string
): AutomationPlanApprovalResult {
  return {
    proposalId: row.id.toString(),
    projectId: row.projectId.toString(),
    status: "APPROVED",
    plan: row.plan as AutomationPlan,
    capabilityIds: [...(row.plan as AutomationPlan).capabilityIds],
    founderMemberId,
    founderUserId,
    decidedAt: row.decidedAt ? row.decidedAt.toISOString() : new Date().toISOString(),
  };
}

/**
 * Founder (hoặc co-founder) bấm Duyệt thẻ kế hoạch. Idempotent: gọi lại khi đã `APPROVED` mà
 * chưa có `approved_schedule_id` thì trả lại ĐÚNG dữ liệu đã quyết định lần trước (để services/cosa
 * retry an toàn sau khi tạo lịch thất bại giữa đường); đã có lịch rồi thì `alreadyExists`.
 */
export async function approveAutomationPlanProposal(
  ctx: TenantContext,
  projectId: string,
  proposalId: string,
  now: Date = new Date()
): Promise<MvpSuccess<AutomationPlanApprovalResult>> {
  const approverMemberId = requireFounderOwner(ctx);
  const projId = parseId(projectId, "projectId");
  const id = parseId(proposalId, "proposalId");

  return db.transaction(async (tx) => {
    // Khoá đúng dòng nháp — hai lần bấm Duyệt song song (hoặc worker retry chồng lấp request
    // người dùng) không được cùng đi qua nhánh DRAFT và tạo 2 quyết định khác nhau.
    const [row] = await tx
      .select()
      .from(automationPlanProposals)
      .where(
        and(
          eq(automationPlanProposals.id, id),
          eq(automationPlanProposals.workspaceId, BigInt(ctx.workspaceId)),
          eq(automationPlanProposals.projectId, projId)
        )
      )
      .limit(1)
      .for("update");

    if (!row) {
      throw APIError.notFound("automation_plan_not_found: không tìm thấy nháp kế hoạch");
    }

    if (row.status === "DISCARDED") {
      throw APIError.failedPrecondition("automation_plan_discarded: nháp kế hoạch đã bị huỷ");
    }

    if (row.status === "APPROVED") {
      if (row.approvedScheduleId) {
        throw APIError.alreadyExists(
          `automation_plan_already_linked: nháp đã có lịch (scheduleId=${row.approvedScheduleId})`
        );
      }
      if (!row.decidedByMemberId || !row.decidedByUserId) {
        // Không nên xảy ra với dòng được tạo bởi flow này — coi như hỏng dữ liệu.
        throw APIError.internal("automation_plan_decision_incomplete: thiếu founder đã duyệt");
      }
      return mvpItem(
        toApprovalResult(row, row.decidedByMemberId.toString(), row.decidedByUserId),
        [{ kind: "company_db", ref: `operating.automation_plan_proposals:${row.id.toString()}` }]
      );
    }

    // status === "DRAFT" — re-verify readiness BÂY GIỜ, không tin `row.readiness` cũ.
    const plan = row.plan as AutomationPlan;
    const blockers: string[] = [];

    try {
      // Founder sở hữu lịch = người bấm duyệt (ADR mục 5) — không phải proposedByMemberId.
      await resolveUsableChannelForFounder(ctx.workspaceId, approverMemberId, plan.channel.kind);
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      if (
        message.startsWith("founder_channel_unavailable:") ||
        message.startsWith("founder_channel_ambiguous:")
      ) {
        blockers.push("founder_channel_unverified");
      } else {
        throw err;
      }
    }

    if (plan.agentDeploymentId) {
      const deployments = await getProjectFounderDeployments(ctx, projId.toString());
      const deployment = deployments.data.agents.find((a) => a.id === plan.agentDeploymentId);
      if (!deployment || deployment.state !== "ACTIVE") {
        throw APIError.failedPrecondition(
          `agent_deployment_unavailable: agent đã chọn không còn hoạt động trong Project (deploymentId=${plan.agentDeploymentId})`
        );
      }
    } else {
      // proposeNewAgent=true và chưa có deployment thật để tái dùng.
      blockers.push("requires_new_agent");
    }

    if (blockers.length > 0) {
      throw APIError.failedPrecondition(`automation_plan_not_ready: ${blockers.join(",")}`);
    }

    const decidedAt = now;
    const [updated] = await tx
      .update(automationPlanProposals)
      .set({
        status: "APPROVED",
        decidedAt,
        decidedByMemberId: BigInt(approverMemberId),
        decidedByUserId: ctx.userId,
      })
      .where(eq(automationPlanProposals.id, row.id))
      .returning();

    if (!updated) {
      throw APIError.internal("automation_plan_approve_failed: không ghi được quyết định duyệt");
    }

    return mvpItem(toApprovalResult(updated, approverMemberId, ctx.userId), [
      { kind: "company_db", ref: `operating.automation_plan_proposals:${updated.id.toString()}` },
    ]);
  });
}

/**
 * services/cosa gọi sau khi `createWorkspaceSchedule` thành công, để ghi `approved_schedule_id`.
 * Idempotent theo đúng `scheduleId` (worker/handler retry an toàn); gán lịch KHÁC vào nháp đã có
 * lịch là lỗi (không được âm thầm ghi đè).
 */
export async function linkAutomationPlanSchedule(
  ctx: TenantContext,
  projectId: string,
  proposalId: string,
  scheduleId: string
): Promise<MvpSuccess<{ proposalId: string; approvedScheduleId: string }>> {
  const projId = parseId(projectId, "projectId");
  const id = parseId(proposalId, "proposalId");
  if (typeof scheduleId !== "string" || !scheduleId.trim() || scheduleId.length > 128) {
    throw invalidScheduleId("scheduleId phải là chuỗi không rỗng, tối đa 128 ký tự");
  }
  const cleanScheduleId = scheduleId.trim();

  return db.transaction(async (tx) => {
    const [row] = await tx
      .select()
      .from(automationPlanProposals)
      .where(
        and(
          eq(automationPlanProposals.id, id),
          eq(automationPlanProposals.workspaceId, BigInt(ctx.workspaceId)),
          eq(automationPlanProposals.projectId, projId)
        )
      )
      .limit(1)
      .for("update");

    if (!row) {
      throw APIError.notFound("automation_plan_not_found: không tìm thấy nháp kế hoạch");
    }
    if (row.status !== "APPROVED") {
      throw APIError.failedPrecondition(
        "automation_plan_not_approved: chỉ nháp đã duyệt mới gán được lịch"
      );
    }
    if (row.approvedScheduleId) {
      if (row.approvedScheduleId === cleanScheduleId) {
        return mvpItem(
          { proposalId: row.id.toString(), approvedScheduleId: row.approvedScheduleId },
          [{ kind: "company_db", ref: `operating.automation_plan_proposals:${row.id.toString()}` }]
        );
      }
      throw APIError.alreadyExists(
        `automation_plan_already_linked: nháp đã gán lịch khác (scheduleId=${row.approvedScheduleId})`
      );
    }

    const [updated] = await tx
      .update(automationPlanProposals)
      .set({ approvedScheduleId: cleanScheduleId })
      .where(eq(automationPlanProposals.id, row.id))
      .returning();

    if (!updated) {
      throw APIError.internal("automation_plan_link_failed: không ghi được approved_schedule_id");
    }

    return mvpItem(
      { proposalId: updated.id.toString(), approvedScheduleId: cleanScheduleId },
      [{ kind: "company_db", ref: `operating.automation_plan_proposals:${updated.id.toString()}` }]
    );
  });
}
