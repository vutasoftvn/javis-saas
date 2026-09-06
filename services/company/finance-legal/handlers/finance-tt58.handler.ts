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
import {
  createBookEntryService,
  listBookEntriesService,
  BookEntryView,
} from "../services/accounting-books.service";
import {
  generateReportService,
  listReportSnapshotsService,
  confirmMappingService,
  ReportSnapshotView,
} from "../services/accounting-reports.service";

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
  openingBalance?: string;
  burnWindowMonths?: number;
}

export const postCalculateSnapshot = api(
  { method: "POST", path: "/finance/snapshots/calculate", expose: true },
  async (params: CalculateSnapshotParams): Promise<FinancialSnapshotView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return calculateAndSaveSnapshotService({
      workspaceId: BigInt(ctx.workspaceId),
      snapshotDate: params.snapshotDate,
      openingBalance: params.openingBalance,
      burnWindowMonths: params.burnWindowMonths,
    });
  }
);

// 7. TT58 Books & Reports (F5)
export interface CreateBookEntryParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: string;
  periodId: string;
  documentId?: string;
  item: string;
  category: "capital" | "loan" | "internal_transfer" | "revenue" | "cost" | "advance" | "payable" | "receivable";
  amountMinor: string;
  currency?: string;
  effectiveDate: string;
  source: string;
}

export const postBookEntry = api(
  { method: "POST", path: "/finance/books", expose: true },
  async (params: CreateBookEntryParams): Promise<BookEntryView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createBookEntryService(ctx, {
      legalEntityId: params.legalEntityId,
      periodId: params.periodId,
      documentId: params.documentId,
      item: params.item,
      category: params.category,
      amountMinor: params.amountMinor,
      currency: params.currency,
      effectiveDate: params.effectiveDate,
      source: params.source,
    });
  }
);

export interface ListBookEntriesParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: Query<string>;
  periodId: Query<string>;
}

export const getBookEntries = api(
  { method: "GET", path: "/finance/books", expose: true },
  async (params: ListBookEntriesParams): Promise<{ entries: BookEntryView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const entries = await listBookEntriesService(ctx, {
      legalEntityId: params.legalEntityId,
      periodId: params.periodId,
    });
    return { entries };
  }
);

export interface GenerateReportParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: string;
  periodId: string;
  reportCode: string;
  mappingVersion?: string;
  expectedPeriodVersion?: number;
}

export const postGenerateReport = api(
  { method: "POST", path: "/finance/reports/generate", expose: true },
  async (params: GenerateReportParams): Promise<ReportSnapshotView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return generateReportService(ctx, {
      legalEntityId: params.legalEntityId,
      periodId: params.periodId,
      reportCode: params.reportCode,
      mappingVersion: params.mappingVersion,
      expectedPeriodVersion: params.expectedPeriodVersion,
    });
  }
);

export interface ListReportsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: Query<string>;
  periodId: Query<string>;
  reportCode?: Query<string>;
}

export const getReports = api(
  { method: "GET", path: "/finance/reports", expose: true },
  async (params: ListReportsParams): Promise<{ reports: ReportSnapshotView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const reports = await listReportSnapshotsService(ctx, {
      legalEntityId: params.legalEntityId,
      periodId: params.periodId,
      reportCode: params.reportCode,
    });
    return { reports };
  }
);

export interface ConfirmMappingParams {
  regimeCode: string;
  mappingVersion: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postConfirmAccountingMapping = api(
  { method: "POST", path: "/finance/accounting-mapping/:regimeCode/:mappingVersion/confirm", expose: true },
  async (params: ConfirmMappingParams): Promise<{ confirmedAt: string }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return confirmMappingService(ctx, params.regimeCode, params.mappingVersion);
  }
);
