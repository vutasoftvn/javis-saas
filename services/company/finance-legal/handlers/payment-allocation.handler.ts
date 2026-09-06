import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  createPaymentAllocationService,
  reversePaymentAllocationService,
  listPaymentAllocationsService,
  PaymentAllocationView,
  CreatePaymentAllocationInput,
} from "../services/payment-allocation.service";

export interface CreatePaymentAllocationApiRequest extends CreatePaymentAllocationInput {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const createPaymentAllocation = api(
  { method: "POST", path: "/finance-legal/payment-allocations", expose: true },
  async (req: CreatePaymentAllocationApiRequest): Promise<PaymentAllocationView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return createPaymentAllocationService(ctx, req);
  }
);

export interface ReversePaymentAllocationApiRequest {
  id: string;
  reason: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const reversePaymentAllocation = api(
  { method: "POST", path: "/finance-legal/payment-allocations/:id/reverse", expose: true },
  async (req: ReversePaymentAllocationApiRequest): Promise<PaymentAllocationView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return reversePaymentAllocationService(ctx, { allocationId: req.id, reason: req.reason });
  }
);

export interface ListPaymentAllocationsApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  requestId?: string;
  bankTransactionId?: string;
}

export const listPaymentAllocations = api(
  { method: "GET", path: "/finance-legal/payment-allocations", expose: true },
  async (req: ListPaymentAllocationsApiRequest): Promise<{ data: PaymentAllocationView[] }> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const data = await listPaymentAllocationsService(ctx, {
      requestId: req.requestId,
      bankTransactionId: req.bankTransactionId,
    });
    return { data };
  }
);
