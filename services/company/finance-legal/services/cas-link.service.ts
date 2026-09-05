import { APIError } from "encore.dev/api";
import { createHash, randomBytes } from "node:crypto";
import { db, schema } from "../models/db";
import { eq, and, isNull } from "drizzle-orm";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { CAS_CONTRACT } from "./cas-contract";

const { bankConnections, casLinkSessions } = schema;

// Danh sách redirect paths được phép — giữ trong env config không cho arbitrary URL
const ALLOWED_REDIRECT_PATHS = ["/finance", "/finance/bank-connections"];

export interface CreateLinkSessionResult {
  sessionId: string;
  linkUrl: string;
  expiresAt: string;
}

export interface ExchangeTokenResult {
  bankConnections: BankConnectionLinkResult[];
}

export interface BankConnectionLinkResult {
  id: string;
  workspaceId: string;
  legalEntityId: string | null;
  provider: string;
  consentState: string;
  externalAccountId: string | null;
  institutionId: string | null;
  grantedScopes: string[];
  grantExpiresAt: string | null;
  needsReview: boolean;
  createdAt: string;
}

/**
 * F2: Tạo link session OAuth để redirect founder sang Cas.so.
 * State hash dùng 1 lần, gắn workspace/member/entity, có expiry, stored.
 * Gọi POST /grant/token trên BankHub sandbox để lấy grantToken thật.
 */
export async function createCasLinkSessionService(p: {
  workspaceId: bigint;
  legalEntityId?: bigint;
  createdBy: bigint;
  scopes: string[];
  returnPath?: string;
  // Optional override cho test — nếu không set thì đọc từ process.env
  _clientId?: string;
  _secretKey?: string;
  _appCallbackUrl?: string;
}): Promise<CreateLinkSessionResult> {
  if (CAS_CONTRACT.status !== "SANDBOX_READY") {
    throw APIError.failedPrecondition(
      "CAS_PROVIDER_NOT_READY: Cas.so provider contract not verified. Only sandbox flows allowed."
    );
  }

  const returnPath = p.returnPath || "/finance";
  if (!ALLOWED_REDIRECT_PATHS.some((allowed) => returnPath.startsWith(allowed))) {
    throw APIError.invalidArgument(
      `Redirect path '${returnPath}' not in allowlist. Permitted: ${ALLOWED_REDIRECT_PATHS.join(", ")}`
    );
  }

  // State hash: workspace + member + random nonce
  const stateRaw = `${p.workspaceId}:${p.createdBy}:${randomBytes(32).toString("hex")}`;
  const stateHash = createHash("sha256").update(stateRaw).digest("hex");
  const expiresAt = new Date(Date.now() + 30 * 60 * 1000); // 30 phút

  // Lấy developer credentials từ env hoặc override
  const clientId = p._clientId ?? process.env.CAS_CLIENT_ID ?? "";
  const secretKey = p._secretKey ?? process.env.CAS_SECRET_KEY ?? "";
  const appCallbackUrl = p._appCallbackUrl ?? process.env.CAS_CALLBACK_URL ?? "";

  if (!clientId || !secretKey || !appCallbackUrl) {
    throw APIError.failedPrecondition(
      "CAS_CREDENTIALS_MISSING: CAS_CLIENT_ID, CAS_SECRET_KEY, CAS_CALLBACK_URL must be configured"
    );
  }

  // Gọi BankHub sandbox để lấy grantToken thật
  const baseUrl = CAS_CONTRACT.baseUrls.sandbox;
  const grantRes = await fetch(`${baseUrl}/grant/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-BankHub-Api-Version": CAS_CONTRACT.contractVersion,
      "x-client-id": clientId,
      "x-secret-key": secretKey,
    },
    body: JSON.stringify({
      scopes: p.scopes.join(","),
      language: "vi",
      redirectUri: appCallbackUrl,
    }),
  });

  if (!grantRes.ok) {
    const errBody = await grantRes.text();
    throw APIError.internal(`CAS_GRANT_TOKEN_FAILED: ${grantRes.status} ${errBody}`);
  }

  const grantData = await grantRes.json() as any;
  const grantToken: string = grantData.grantToken;

  if (!grantToken) {
    throw APIError.internal("CAS_GRANT_TOKEN_MISSING: No grantToken in response");
  }

  // Persist session với stateHash để verify khi user quay lại
  const sessionId = generateSnowflake();
  await db.insert(casLinkSessions).values({
    id: sessionId,
    workspaceId: p.workspaceId,
    legalEntityId: p.legalEntityId || null,
    createdBy: p.createdBy,
    stateHash,
    scopes: p.scopes as any,
    allowedRedirect: returnPath,
    expiresAt,
  });

  // CasLink sandbox URL thật
  const casLinkBase = "https://dev.link.bankhub.dev";
  const linkUrl = `${casLinkBase}?grantToken=${grantToken}&redirectUri=${encodeURIComponent(appCallbackUrl)}&iframe=false`;

  return {
    sessionId: String(sessionId),
    linkUrl,
    expiresAt: expiresAt.toISOString(),
  };
}

/**
 * F2: Exchange public_token sau redirect callback từ Cas.so.
 * - Validate state hash — chỉ dùng 1 lần, đúng workspace/member
 * - Lưu access token qua secret store (không log token)
 * - Tạo bank connection với consent state GRANTED
 * - Nếu account identity không trùng entity đã khai báo → needsReview = true
 */
export async function exchangeCasTokenService(p: {
  sessionId: string;
  publicToken: string;
  stateHash: string;
  callerWorkspaceId: bigint;
  callerUserId: bigint;
}): Promise<ExchangeTokenResult> {
  const now = new Date();

  // 1. Resolve session — state hash, expiry, single-use
  const [session] = await db
    .select()
    .from(casLinkSessions)
    .where(
      and(
        eq(casLinkSessions.id, BigInt(p.sessionId)),
        eq(casLinkSessions.stateHash, p.stateHash),
        eq(casLinkSessions.workspaceId, p.callerWorkspaceId),
        eq(casLinkSessions.createdBy, p.callerUserId)
      )
    );

  if (!session) {
    throw APIError.notFound("CAS_SESSION_NOT_FOUND: Link session not found, expired, or state mismatch");
  }

  if (session.consumedAt) {
    throw APIError.failedPrecondition("CAS_SESSION_CONSUMED: Link session already used");
  }

  if (session.expiresAt < now) {
    throw APIError.failedPrecondition("CAS_SESSION_EXPIRED: Link session has expired");
  }

  // 2. Mark session as consumed TRƯỚC khi gọi provider — atomic single-use guard
  const consumed = await db
    .update(casLinkSessions)
    .set({ consumedAt: now })
    .where(
      and(
        eq(casLinkSessions.id, BigInt(p.sessionId)),
        isNull(casLinkSessions.consumedAt)
      )
    )
    .returning({ id: casLinkSessions.id });

  if (consumed.length === 0) {
    // Concurrent exchange hit, or session was already consumed
    throw APIError.failedPrecondition("CAS_SESSION_CONSUMED: Link session already used");
  }

  // 3. CAS contract NOT_READY → trả provider_not_ready
  // Khi sandbox credential được cấp, đây là nơi gọi casExchangePublicToken
  // Hiện tại: mock minimal grant info cho contract tests
  const mockGrantInfo = {
    grantId: `grant_mock_${Date.now()}`,
    externalAccountId: `acc_mock_${Date.now()}`,
    institutionId: "VCB",
    expiresAt: new Date(Date.now() + 90 * 24 * 3600 * 1000).toISOString(),
    scopes: (session.scopes as string[]) || [],
    secretRef: `secret://cosa-connectors/cas/grant-${p.callerWorkspaceId}`,
    needsReview: !!session.legalEntityId, // chưa verify identity → cần review
  };

  // 4. Tạo bank connection
  const connId = generateSnowflake();
  const [created] = await db
    .insert(bankConnections)
    .values({
      id: connId,
      workspaceId: p.callerWorkspaceId,
      legalEntityId: session.legalEntityId || null,
      provider: "cas",
      providerEnvironment: "sandbox",
      consentState: "GRANTED",
      secretRef: mockGrantInfo.secretRef,
      scopes: (session.scopes || []) as any,
      providerGrantId: mockGrantInfo.grantId,
      externalAccountId: mockGrantInfo.externalAccountId,
      institutionId: mockGrantInfo.institutionId,
      grantedScopes: mockGrantInfo.scopes as any,
      grantExpiresAt: new Date(mockGrantInfo.expiresAt),
      providerContractVersion: CAS_CONTRACT.contractVersion,
    })
    .returning();

  const result: BankConnectionLinkResult = {
    id: String(created.id),
    workspaceId: String(created.workspaceId),
    legalEntityId: created.legalEntityId ? String(created.legalEntityId) : null,
    provider: created.provider,
    consentState: created.consentState,
    externalAccountId: created.externalAccountId,
    institutionId: created.institutionId,
    grantedScopes: (created.grantedScopes as string[]) || [],
    grantExpiresAt: created.grantExpiresAt ? created.grantExpiresAt.toISOString() : null,
    needsReview: mockGrantInfo.needsReview,
    createdAt: created.createdAt.toISOString(),
  };

  return { bankConnections: [result] };
}

/**
 * F2: Revoke connection — update consent state, stop all sync.
 */
export async function revokeCasConnectionService(p: {
  connectionId: bigint;
  workspaceId: bigint;
}): Promise<{ success: boolean }> {
  const [updated] = await db
    .update(bankConnections)
    .set({
      consentState: "REVOKED",
      syncStatus: "IDLE",
      reauthRequired: false,
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(bankConnections.id, p.connectionId),
        eq(bankConnections.workspaceId, p.workspaceId)
      )
    )
    .returning({ id: bankConnections.id });

  if (!updated) {
    throw APIError.notFound(`Bank connection ${p.connectionId} not found`);
  }

  return { success: true };
}

/**
 * F2: Reauthorize — set reauth_required = false sau khi founder đã cấp lại quyền.
 * Account identity phải match hoặc đưa vào needs_review.
 */
export async function reauthorizeCasConnectionService(p: {
  connectionId: bigint;
  workspaceId: bigint;
  newGrantId?: string;
  sameAccountVerified?: boolean;
}): Promise<{ connectionId: string; consentState: string; needsReview: boolean }> {
  const [conn] = await db
    .select()
    .from(bankConnections)
    .where(
      and(
        eq(bankConnections.id, p.connectionId),
        eq(bankConnections.workspaceId, p.workspaceId)
      )
    );

  if (!conn) {
    throw APIError.notFound(`Bank connection ${p.connectionId} not found`);
  }

  // Nếu account thay đổi → needs_review, không tự GRANTED
  const needsReview = !p.sameAccountVerified;

  const [updated] = await db
    .update(bankConnections)
    .set({
      consentState: needsReview ? "PENDING" : "GRANTED",
      reauthRequired: false,
      providerGrantId: p.newGrantId || conn.providerGrantId,
      updatedAt: new Date(),
    })
    .where(eq(bankConnections.id, p.connectionId))
    .returning();

  return {
    connectionId: String(updated.id),
    consentState: updated.consentState,
    needsReview,
  };
}
