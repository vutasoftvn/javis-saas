import { api, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getAccountingRegimePolicyService,
  setAccountingRegimePolicyService,
  AccountingRegimePolicyView,
} from "../services/accounting-regime-policy.service";
import {
  listBankConnectionsService,
  createBankConnectionService,
  BankConnectionView,
} from "../services/bank-connection.service";
import {
  listBankTransactionsService,
  ingestBankTransactionService,
  BankTransactionView,
} from "../services/bank-transaction.service";
import {
  listAccountingDocumentsService,
  createDraftDocumentService,
  confirmAccountingDocumentService,
  voidAccountingDocumentService,
  AccountingDocumentView,
} from "../services/accounting-document.service";
import {
  listReconciliationProposalsService,
  proposeReconciliationService,
  acceptReconciliationProposalService,
  ReconciliationProposalView,
} from "../services/reconciliation-proposal.service";
import {
  getFinancialSnapshotsService,
  calculateAndSaveSnapshotService,
  FinancialSnapshotView,
} from "../services/financial-snapshot.service";

// 1. Accounting Regime Policy
export interface GetRegimePolicyParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  date?: Query<string>;
}

export const getRegimePolicy = api(
  { method: "GET", path: "/finance/regime-policy", expose: true },
  async (params: GetRegimePolicyParams): Promise<{ policy: AccountingRegimePolicyView | null }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const policy = await getAccountingRegimePolicyService(BigInt(ctx.workspaceId), params.date);
    return { policy };
  }
);

// 2. Bank Connections
export interface ListBankConnectionsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const getBankConnections = api(
  { method: "GET", path: "/finance/bank-connections", expose: true },
  async (params: ListBankConnectionsParams): Promise<{ connections: BankConnectionView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const connections = await listBankConnectionsService(BigInt(ctx.workspaceId));
    return { connections };
  }
);

export interface CreateBankConnectionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  provider: "cas" | "manual";
  secretRef?: string;
  scopes?: string[];
}

export const postBankConnection = api(
  { method: "POST", path: "/finance/bank-connections", expose: true },
  async (params: CreateBankConnectionParams): Promise<BankConnectionView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createBankConnectionService({
      workspaceId: BigInt(ctx.workspaceId),
      provider: params.provider,
      secretRef: params.secretRef,
      scopes: params.scopes,
    });
  }
);

// 3. Bank Transactions
export interface ListBankTransactionsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  status?: Query<string>;
}

export const getBankTransactions = api(
  { method: "GET", path: "/finance/bank-transactions", expose: true },
  async (params: ListBankTransactionsParams): Promise<{ transactions: BankTransactionView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const transactions = await listBankTransactionsService(BigInt(ctx.workspaceId), params.status);
    return { transactions };
  }
);

// 4. Accounting Documents
export interface ListAccountingDocumentsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  status?: Query<string>;
}

export const getAccountingDocuments = api(
  { method: "GET", path: "/finance/accounting-documents", expose: true },
  async (params: ListAccountingDocumentsParams): Promise<{ documents: AccountingDocumentView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const documents = await listAccountingDocumentsService(BigInt(ctx.workspaceId), params.status);
    return { documents };
  }
);

export interface CreateAccountingDocumentParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  documentType: "RECEIPT" | "PAYMENT" | "INVOICE" | "JOURNAL";
  number: string;
  documentDate: string;
  amount: string | number;
  currency?: string;
  description: string;
  lineItems?: any[];
}

export const postAccountingDocument = api(
  { method: "POST", path: "/finance/accounting-documents", expose: true },
  async (params: CreateAccountingDocumentParams): Promise<AccountingDocumentView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createDraftDocumentService({
      workspaceId: BigInt(ctx.workspaceId),
      documentType: params.documentType,
      number: params.number,
      documentDate: params.documentDate,
      amount: params.amount,
      currency: params.currency,
      description: params.description,
      lineItems: params.lineItems,
    });
  }
);

export interface ConfirmDocumentParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postConfirmAccountingDocument = api(
  { method: "POST", path: "/finance/accounting-documents/:id/confirm", expose: true },
  async (params: ConfirmDocumentParams): Promise<AccountingDocumentView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return confirmAccountingDocumentService({
      documentId: BigInt(params.id),
      workspaceId: BigInt(ctx.workspaceId),
      confirmedBy: BigInt(ctx.userId || "1"),
    });
  }
);

// 5. Reconciliation Proposals
export interface ListReconciliationParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  status?: Query<string>;
}

export const getReconciliationProposals = api(
  { method: "GET", path: "/finance/reconciliation-proposals", expose: true },
  async (params: ListReconciliationParams): Promise<{ proposals: ReconciliationProposalView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const proposals = await listReconciliationProposalsService(BigInt(ctx.workspaceId), params.status);
    return { proposals };
  }
);

export interface AcceptReconciliationParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postAcceptReconciliationProposal = api(
  { method: "POST", path: "/finance/reconciliation-proposals/:id/accept", expose: true },
  async (params: AcceptReconciliationParams): Promise<ReconciliationProposalView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return acceptReconciliationProposalService({
      proposalId: BigInt(params.id),
      workspaceId: BigInt(ctx.workspaceId),
      acceptedBy: BigInt(ctx.userId || "1"),
    });
  }
);

// 6. Financial Snapshots
export interface GetSnapshotsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const getFinancialSnapshots = api(
  { method: "GET", path: "/finance/snapshots", expose: true },
  async (params: GetSnapshotsParams): Promise<{ snapshots: FinancialSnapshotView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const snapshots = await getFinancialSnapshotsService(BigInt(ctx.workspaceId));
    return { snapshots };
  }
);

export interface CalculateSnapshotParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  snapshotDate: string;
}

export const postCalculateSnapshot = api(
  { method: "POST", path: "/finance/snapshots/calculate", expose: true },
  async (params: CalculateSnapshotParams): Promise<FinancialSnapshotView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return calculateAndSaveSnapshotService({
      workspaceId: BigInt(ctx.workspaceId),
      snapshotDate: params.snapshotDate,
    });
  }
);
