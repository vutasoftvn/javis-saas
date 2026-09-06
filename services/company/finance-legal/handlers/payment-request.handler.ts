import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  createPaymentRequestService,
  updatePaymentRequestService,
  submitPaymentRequestService,
  approvePaymentRequestService,
  rejectPaymentRequestService,
  cancelPaymentRequestService,
  reportPaymentTransferService,
  getPaymentRequestService,
  listPaymentRequestsService,
  PaymentRequestView,
  CreatePaymentRequestInput,
  UpdatePaymentRequestInput,
} from "../services/payment-request.service";

export interface CreatePaymentRequestApiRequest extends CreatePaymentRequestInput {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const createPaymentRequest = api(
  { method: "POST", path: "/finance-legal/payment-requests", expose: true },
  async (req: CreatePaymentRequestApiRequest): Promise<PaymentRequestView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return createPaymentRequestService(ctx, req);
  }
);

export interface ListPaymentRequestsApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId?: string;
  approvalState?: string;
}

export const listPaymentRequests = api(
  { method: "GET", path: "/finance-legal/payment-requests", expose: true },
  async (req: ListPaymentRequestsApiRequest): Promise<{ data: PaymentRequestView[] }> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const data = await listPaymentRequestsService(ctx, {
      legalEntityId: req.legalEntityId,
      approvalState: req.approvalState,
    });
    return { data };
  }
);

export interface GetPaymentRequestApiRequest {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const getPaymentRequest = api(
  { method: "GET", path: "/finance-legal/payment-requests/:id", expose: true },
  async (req: GetPaymentRequestApiRequest): Promise<PaymentRequestView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return getPaymentRequestService(ctx, req.id);
  }
);

export interface UpdatePaymentRequestApiRequest extends Omit<UpdatePaymentRequestInput, "id"> {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const updatePaymentRequest = api(
  { method: "PATCH", path: "/finance-legal/payment-requests/:id", expose: true },
  async (req: UpdatePaymentRequestApiRequest): Promise<PaymentRequestView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return updatePaymentRequestService(ctx, req);
  }
);

export interface PaymentRequestActionApiRequest {
  id: string;
  expectedVersion: number;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const submitPaymentRequest = api(
  { method: "POST", path: "/finance-legal/payment-requests/:id/submit", expose: true },
  async (req: PaymentRequestActionApiRequest): Promise<PaymentRequestView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return submitPaymentRequestService(ctx, req);
  }
);

export const approvePaymentRequest = api(
  { method: "POST", path: "/finance-legal/payment-requests/:id/approve", expose: true },
  async (req: PaymentRequestActionApiRequest): Promise<PaymentRequestView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return approvePaymentRequestService(ctx, req);
  }
);

export interface RejectPaymentRequestApiRequest extends PaymentRequestActionApiRequest {
  reason: string;
}

export const rejectPaymentRequest = api(
  { method: "POST", path: "/finance-legal/payment-requests/:id/reject", expose: true },
  async (req: RejectPaymentRequestApiRequest): Promise<PaymentRequestView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return rejectPaymentRequestService(ctx, req);
  }
);

export const cancelPaymentRequest = api(
  { method: "POST", path: "/finance-legal/payment-requests/:id/cancel", expose: true },
  async (req: PaymentRequestActionApiRequest): Promise<PaymentRequestView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return cancelPaymentRequestService(ctx, req);
  }
);

export const reportPaymentTransfer = api(
  { method: "POST", path: "/finance-legal/payment-requests/:id/report-transfer", expose: true },
  async (req: PaymentRequestActionApiRequest): Promise<PaymentRequestView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return reportPaymentTransferService(ctx, req);
  }
);
