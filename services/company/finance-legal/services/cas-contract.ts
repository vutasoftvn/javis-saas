/**
 * Cas.so Provider Contract (formerly BankHub)
 * 
 * Base URL Sandbox: https://sandbox.bankhub.dev
 * Base URL Production: https://production.bankhub.dev
 * Console: https://console.bankhub.dev
 * 
 * Auth model:
 * - Developer credentials: x-client-id + x-secret-key headers (get from console.bankhub.dev)
 * - Grant flow: POST /grant/token → open CasLink widget → user logs in bank (bankusrdemo1/soproud/otp:123456 for sandbox) → publicToken → POST /grant/exchange → accessToken
 * - Transaction query: GET /transactions with Authorization: Bearer <accessToken>
 * 
 * Status: SANDBOX_READY (pending production verification)
 */

export const CAS_CONTRACT = {
  providerName: "Cas.so (formerly BankHub)",
  contractVersion: "2023-01-01",
  status: "SANDBOX_READY" as const, // updated from NOT_READY when sandbox creds confirmed
  apiVersionHeader: "X-BankHub-Api-Version",
  baseUrls: {
    sandbox: "https://sandbox.bankhub.dev",
    production: "https://production.bankhub.dev",
  },
  auth: {
    developerHeaders: {
      clientId: "x-client-id",
      secretKey: "x-secret-key",
    },
    apiVersionHeader: "X-BankHub-Api-Version",
    apiVersion: "2023-01-01",
    note: "client_id + secret_key from console.bankhub.dev. NEVER in client-side code.",
  },
  grantFlow: {
    createGrantToken: { method: "POST", path: "/grant/token" },
    casLinkWidget: {
      sandboxBankUser: { username: "bankusrdemo1", password: "soproud", otp: "123456" },
      note: "Open CasLink with grantToken; user authenticates bank account. Receives publicToken callback.",
    },
    exchangePublicToken: { method: "POST", path: "/grant/exchange" },
    scopes: ["transaction", "balance", "qrpay", "va"],
    oneGrantMayHaveMultipleAccounts: true,
  },
  transactions: {
    method: "GET",
    path: "/transactions",
    authHeader: "Authorization: Bearer <accessToken>",
    pagination: { type: "page+limit", fields: ["page", "pageSize", "nextPage"] },
    responseRootKey: "records", // array of transactions
    timezone: "Asia/Ho_Chi_Minh",
    knownResponseFields: {
      id: "id",
      tid: "tid",
      description: "description",
      amount: "amount", // Số dương = in, âm = out (or use 'in'/'out' subfield)
      cusum_balance: "cusum_balance",
      bank_sub_acc_id: "bank_sub_acc_id",
      when: "when", // ISO-8601 or epoch ms
    },
    note: "Webhook supplement, not guaranteed for all banks. Always poll as fallback.",
  },
  webhook: {
    signatureHeader: "x-cas-webhook-secret-key",
    eventIdField: "id",
    retryBehavior: "Provider retries 5 times with backoff; idempotency via event id",
    eventTypes: ["transaction", "grant.revoked", "grant.expired"],
  },
  sampleSandboxEvidence: {
    dateCollected: null,
    note: "Fixtures stored in tests/fixtures/cas-so/ when collected",
  },
} as const;

export type CasGrantStatus = "PENDING" | "GRANTED" | "REVOKED" | "EXPIRED";
export type CasEnvironment = "sandbox" | "production";

// Raw transaction record from GET /transactions
export interface CasRawTransaction {
  id: number;
  tid: string;
  description: string;
  amount: number; // positive = credit, negative = debit (verify with real data)
  cusum_balance: number;
  bank_sub_acc_id: string; // linked account identifier
  sub_acc_id: string;
  when: string; // datetime string
  bank_name?: string;
  payment_channel?: string;
  virtual_account_id?: string;
}

export interface CasGrantToken {
  grantToken: string;
}

export interface CasExchangeResult {
  access_token: string; // accessToken for Bearer auth
  grant_id?: string;
  expires_at?: string;
  accounts?: CasAccountInfo[];
}

export interface CasAccountInfo {
  id: string;
  bank_sub_acc_id: string;
  bank_id: string;
  bank_account_name: string;
  bank_account_number: string;
}

export interface CasWebhookEnvelope {
  id: string;
  error: number; // 0 = success
  data: CasRawTransaction | null;
}
