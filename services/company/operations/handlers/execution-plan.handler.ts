import { api, APIError, Header, Query } from "encore.dev/api";
import {
  createExecutionPlanService,
  listExecutionPlansService,
  getExecutionPlanService,
  patchExecutionPlanItemService,
  acceptExecutionPlanService,
  rejectExecutionPlanService,
  listCapabilityPolicyService,
  setCapabilityPolicyService,
  CreatePlanItemInput,
  ExecutionPlanView,
  ExecutionPlanItemView,
  AcceptExecutionPlanResult,
  CapabilityPolicyEntry,
} from "../services/execution-plan.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { TenantPolicyDecision } from "../services/autonomy-classifier";
import { AutonomyClass } from "../services/autonomy-classifier";
import {
  resolveCosaTaskContext,
  WGA_CAP_EXECUTION_PLAN_CREATE,
} from "../../shared/auth/cosa-task-delegation";

interface ListParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: Query<string>;
  status?: Query<string>;
}

export const listExecutionPlans = api(
  { method: "GET", path: "/operations/execution-plans", expose: true },
  async (p: ListParams): Promise<{ plans: ExecutionPlanView[] }> => {
    if (!p.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    if (!p.projectId) throw APIError.invalidArgument("projectId query required");
    const plans = await listExecutionPlansService(
      { workspaceId: p.workspaceId, projectId: p.projectId, status: p.status },
      p.authorization
    );
    return { plans };
  }
);

interface GetParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const getExecutionPlan = api(
  { method: "GET", path: "/operations/execution-plans/:id", expose: true },
  async (p: GetParams): Promise<ExecutionPlanView> => {
    if (!p.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    return getExecutionPlanService(p.id, p.workspaceId, p.authorization);
  }
);

interface CreateParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  weeklyPlanId?: string | null;
  goalText: string;
  origin?: "command_center" | "chat";
  originRef?: string | null;
  runId?: string | null;
  items: CreatePlanItemInput[];
}

export const createExecutionPlan = api(
  { method: "POST", path: "/operations/execution-plans", expose: true },
  async (p: CreateParams): Promise<ExecutionPlanView> => {
    if (!p.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    if (!p.projectId) throw APIError.invalidArgument("projectId required");
    if (!p.goalText || !p.goalText.trim()) throw APIError.invalidArgument("goalText required");
    if (!Array.isArray(p.items) || p.items.length === 0) {
      throw APIError.invalidArgument("items required (at least 1)");
    }
    // runId present -> gọi bởi background task goal_decomposition của apps/cosa:
    // xác thực bằng cosa company-delegation token, không phải user session.
    const ctxOverride = p.runId
      ? resolveCosaTaskContext(p.authorization, {
          workspaceId: p.workspaceId,
          capabilityId: WGA_CAP_EXECUTION_PLAN_CREATE,
          runId: p.runId,
        })
      : undefined;
    return createExecutionPlanService(
      {
        workspaceId: p.workspaceId,
        projectId: p.projectId,
        weeklyPlanId: p.weeklyPlanId ?? null,
        goalText: p.goalText,
        origin: p.origin ?? "command_center",
        originRef: p.originRef ?? null,
        runId: p.runId ?? null,
        items: p.items,
      },
      p.authorization,
      ctxOverride
    );
  }
);

interface PatchItemParams {
  id: string;
  itemId: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  title?: string;
  evidenceRefs?: string[];
  priority?: "low" | "medium" | "high" | "urgent";
  autonomyClass?: AutonomyClass;
  ownerAgentProfile?: string | null;
  drop?: boolean;
}

export const patchExecutionPlanItem = api(
  { method: "PATCH", path: "/operations/execution-plans/:id/items/:itemId", expose: true },
  async (p: PatchItemParams): Promise<ExecutionPlanItemView> => {
    if (!p.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    return patchExecutionPlanItemService(
      p.id,
      p.itemId,
      {
        title: p.title,
        evidenceRefs: p.evidenceRefs,
        priority: p.priority,
        autonomyClass: p.autonomyClass,
        ownerAgentProfile: p.ownerAgentProfile,
        drop: p.drop,
      },
      p.workspaceId,
      p.authorization
    );
  }
);

interface AcceptParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  acceptedByMemberId?: string | null;
}

export const acceptExecutionPlan = api(
  { method: "POST", path: "/operations/execution-plans/:id/accept", expose: true },
  async (p: AcceptParams): Promise<AcceptExecutionPlanResult> => {
    if (!p.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    return acceptExecutionPlanService(
      p.id,
      { workspaceId: p.workspaceId, acceptedByMemberId: p.acceptedByMemberId ?? null },
      p.authorization
    );
  }
);

interface RejectParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const rejectExecutionPlan = api(
  { method: "POST", path: "/operations/execution-plans/:id/reject", expose: true },
  async (p: RejectParams): Promise<{ ok: true }> => {
    if (!p.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    await rejectExecutionPlanService(p.id, p.workspaceId, p.authorization);
    return { ok: true };
  }
);

// WGA #3 — override lớp quyền hạn per-capability (founder).
export const listCapabilityPolicy = api(
  { method: "GET", path: "/operations/capability-policy", expose: true },
  async ({
    workspaceId,
    authorization,
  }: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<{ entries: CapabilityPolicyEntry[] }> => {
    const entries = await listCapabilityPolicyService(workspaceId, authorization);
    return { entries };
  }
);

export const setCapabilityPolicy = api(
  { method: "POST", path: "/operations/capability-policy", expose: true },
  async ({
    capabilityId,
    decision,
    workspaceId,
    authorization,
  }: {
    capabilityId: string;
    decision: TenantPolicyDecision | null;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<{ entries: CapabilityPolicyEntry[] }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const entries = await setCapabilityPolicyService(
      { workspaceId, capabilityId, decision: decision ?? null },
      ctx
    );
    return { entries };
  }
);
