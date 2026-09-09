import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  AtomicQueueResult,
  Priority,
  WorkPackageView,
  confirmAiProposalAndQueue,
  createConfirmedTaskAndQueue,
  createWorkPackage,
  getWorkPackage,
  reassignWorkPackage,
} from "../services/work-package.service";
import type { CreateTaskOutcomeContractInput } from "../services/task-outcome-contract.service";

type ContractBody = Omit<CreateTaskOutcomeContractInput, "workspaceId" | "taskId">;
interface InitialPackageBody {
  assignedAgentInstanceId: string;
  objective: string;
  outputContract: Record<string, unknown>;
  acceptanceRubric: Record<string, number>;
  requestedPriority?: Priority;
}

export const createWorkPackageEndpoint = api(
  { method: "POST", path: "/operations/work-packages", expose: true },
  async (params: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    taskId: string;
    outcomeContractId: string;
    assignedAgentInstanceId: string;
    requestedPriority: Priority;
    objective: string;
    outputContract: Record<string, unknown>;
    acceptanceRubric: Record<string, number>;
    idempotencyKey: string;
  }): Promise<WorkPackageView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createWorkPackage(
      {
        taskId: params.taskId,
        outcomeContractId: params.outcomeContractId,
        assignedAgentInstanceId: params.assignedAgentInstanceId,
        requestedPriority: params.requestedPriority,
        objective: params.objective,
        outputContract: params.outputContract,
        acceptanceRubric: params.acceptanceRubric,
        idempotencyKey: params.idempotencyKey,
      },
      ctx
    );
  }
);

export const createConfirmedTaskAndQueueEndpoint = api(
  { method: "POST", path: "/operations/work-packages/confirmed-task", expose: true },
  async (params: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    task: { title: string; initiativeId?: string; priority: "low" | "medium" | "high" | "urgent" };
    contract: ContractBody;
    initialPackage: InitialPackageBody;
    idempotencyKey: string;
  }): Promise<AtomicQueueResult> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createConfirmedTaskAndQueue(
      {
        task: params.task,
        contract: params.contract,
        initialPackage: params.initialPackage,
        idempotencyKey: params.idempotencyKey,
      },
      ctx
    );
  }
);

export const confirmAiProposalAndQueueEndpoint = api(
  { method: "POST", path: "/operations/work-packages/confirm-proposal", expose: true },
  async (params: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    proposalTaskId: string;
    draftContractId: string;
    contractPatch: Partial<CreateTaskOutcomeContractInput>;
    initialPackage: InitialPackageBody;
    expectedVersion: number;
    idempotencyKey: string;
  }): Promise<AtomicQueueResult> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return confirmAiProposalAndQueue(
      {
        proposalTaskId: params.proposalTaskId,
        draftContractId: params.draftContractId,
        contractPatch: params.contractPatch,
        initialPackage: params.initialPackage,
        expectedVersion: params.expectedVersion,
        idempotencyKey: params.idempotencyKey,
      },
      ctx
    );
  }
);

export const reassignWorkPackageEndpoint = api(
  { method: "POST", path: "/operations/work-packages/:id/reassign", expose: true },
  async (params: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    targetAgentInstanceId: string;
    expectedVersion: number;
    reason?: string;
  }): Promise<WorkPackageView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return reassignWorkPackage(
      {
        workPackageId: params.id,
        targetAgentInstanceId: params.targetAgentInstanceId,
        expectedVersion: params.expectedVersion,
        reason: params.reason,
      },
      ctx
    );
  }
);

export const getWorkPackageEndpoint = api(
  { method: "GET", path: "/operations/work-packages/:id", expose: true },
  async (params: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<WorkPackageView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getWorkPackage(params.id, ctx);
  }
);
