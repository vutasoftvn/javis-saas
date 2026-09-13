import { APIError } from "encore.dev/api";
import { createHash } from "crypto";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  AiGovernanceRef,
  AiGovernanceSnapshot as SignedAiGovernanceSnapshot,
  verifyAiGovernanceSnapshotSignature,
} from "../../shared/auth/ai-governance-snapshot-verification";

const { projects, aiGovernanceDossiers, aiGovernanceDossierRevisions } = schema;

export type AiGovernanceDossierStatus = "DRAFT" | "CONFIRMED" | "SUPERSEDED";

/**
 * Task 2 (CAIO) — "AI Governance Dossier": bản ghi Project-scoped, append-
 * only, chỉ lưu THAM CHIẾU tới một snapshot đã ký (workspace/project/policy
 * ref/evaluator ref/id+version+hash/status/thời điểm quan sát) — KHÔNG BAO
 * GIỜ nội dung prompt/output/credential thật (task-2-brief §Global
 * Constraints: "No prompt transcript, API key, provider credential, raw user
 * message, model output or vulnerability payload enters Company dossier/
 * board frame"). Signature verify + workspace/project binding + staleness
 * check chạy TRƯỚC khi bất kỳ field nào của snapshot được ghi xuống DB —
 * fail closed (`failed_precondition`) nếu bất kỳ điều kiện nào không thoả.
 */

/**
 * Risk signal — chỉ phân loại (category/severity) cố định, KHÔNG có field tự
 * do nào có thể mang prompt/transcript/vulnerability payload thật.
 */
export type RiskSignalCategory =
  | "POLICY_DRIFT"
  | "EVALUATOR_FAILURE"
  | "MODEL_BEHAVIOR"
  | "COMPLIANCE_GAP"
  | "UNKNOWN";

const RISK_SIGNAL_CATEGORIES: ReadonlySet<string> = new Set<RiskSignalCategory>([
  "POLICY_DRIFT",
  "EVALUATOR_FAILURE",
  "MODEL_BEHAVIOR",
  "COMPLIANCE_GAP",
  "UNKNOWN",
]);

export type RiskSignalSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | "UNKNOWN";

const RISK_SIGNAL_SEVERITIES: ReadonlySet<string> = new Set<RiskSignalSeverity>([
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
  "UNKNOWN",
]);

export interface RiskSignal {
  category: RiskSignalCategory;
  severity: RiskSignalSeverity;
}

/**
 * Tham chiếu nguồn đã redact — reference-only shape, mirror `DataSourceRef`
 * (data-governance-dossier.service.ts) — KHÔNG BAO GIỜ raw file URI/path hay
 * credential, deep-scan chặn ở value level bên dưới.
 */
export interface AiGovernanceSourceRef {
  sourceRef: string;
  classification?: string;
  redactedExcerpt?: string;
}

export type AiGovernanceReasonCode =
  | "SNAPSHOT_INGESTED"
  | "RISK_SIGNAL_UPDATED"
  | "SOURCE_REF_UPDATED"
  | "FOUNDER_REVIEW";

const AI_GOVERNANCE_REASON_CODES: ReadonlySet<string> = new Set<AiGovernanceReasonCode>([
  "SNAPSHOT_INGESTED",
  "RISK_SIGNAL_UPDATED",
  "SOURCE_REF_UPDATED",
  "FOUNDER_REVIEW",
]);

/** Cửa sổ staleness cho `snapshot.observedAt` — quyết định cụ thể cho Task 2:
 * 24h. Lý do chọn 24h (không phải TTL ngắn kiểu delegation JWT <=600s):
 * snapshot này là 1 EVIDENCE ARTIFACT được founder xem xét/confirm theo nhịp
 * làm việc của con người (không phải 1 credential runtime), nhưng vẫn phải
 * có 1 trần cứng để "stale/foreign/unverifiable source fails closed" có ý
 * nghĩa — 24h đủ ngắn để loại snapshot cũ/hỏng, đủ dài để founder review
 * trong ngày làm việc mà không phải re-fetch liên tục. */
const SNAPSHOT_STALENESS_WINDOW_MS = 24 * 60 * 60 * 1000;
/** Cho phép skew đồng hồ nhỏ nếu observedAt hơi ở tương lai (clock drift giữa
 * 2 process/2 host) — không cho phép snapshot "từ tương lai" xa hơn mức này. */
const SNAPSHOT_FUTURE_SKEW_MS = 5 * 60 * 1000;

export interface AiGovernanceSnapshotDraft {
  workspaceId: string;
  projectId: string;
  policy: AiGovernanceRef[];
  evaluators: AiGovernanceRef[];
  status: "VERIFIED";
  observedAt: string;
  signature: string;
}

export interface AiGovernanceDossierSnapshot {
  dossierId: string;
  revision: number;
  status: AiGovernanceDossierStatus;
  snapshotRef: string;
  policy: AiGovernanceRef[];
  evaluators: AiGovernanceRef[];
  observedAt: string;
  riskSignals: RiskSignal[];
  sourceRefs: AiGovernanceSourceRef[];
}

export interface CreateAiGovernanceDossierInput {
  projectId: string;
  snapshot: AiGovernanceSnapshotDraft;
  riskSignals?: RiskSignal[];
  sourceRefs?: AiGovernanceSourceRef[];
  reasonCode: AiGovernanceReasonCode;
}

/**
 * Append LUÔN yêu cầu lại toàn bộ `riskSignals`/`sourceRefs` (full-replace,
 * KHÔNG merge) — mirror pattern đã thiết lập ở mọi dossier khác trong
 * portfolio này (progress.md lesson #9).
 */
export interface AppendAiGovernanceRevisionInput {
  snapshot: AiGovernanceSnapshotDraft;
  riskSignals?: RiskSignal[];
  sourceRefs?: AiGovernanceSourceRef[];
  status?: "DRAFT" | "CONFIRMED";
  reasonCode: AiGovernanceReasonCode;
}

// ---------------------------------------------------------------------------
// Validation — allowlist nghiêm ngặt + deep-scan chặn field-sample/raw-value,
// embedding-vector-shaped array, raw file URI, và credential-shaped string ở
// BẤT KỲ field nào (mirror data-governance-dossier.service.ts's
// deepAssertSafeShape — cùng bộ pattern để nhất quán trên toàn portfolio).
// ---------------------------------------------------------------------------

const ALLOWED_CREATE_KEYS = new Set(["projectId", "snapshot", "riskSignals", "sourceRefs", "reasonCode"]);
const ALLOWED_APPEND_KEYS = new Set(["snapshot", "riskSignals", "sourceRefs", "status", "reasonCode"]);
const ALLOWED_SNAPSHOT_KEYS = new Set([
  "workspaceId",
  "projectId",
  "policy",
  "evaluators",
  "status",
  "observedAt",
  "signature",
]);
const ALLOWED_REF_KEYS = new Set(["id", "version", "definitionHash"]);
const ALLOWED_RISK_SIGNAL_KEYS = new Set(["category", "severity"]);
const ALLOWED_SOURCE_REF_KEYS = new Set(["sourceRef", "classification", "redactedExcerpt"]);

const CREDENTIAL_PATTERNS: ReadonlyArray<{ name: string; re: RegExp }> = [
  { name: "api_key_or_token", re: /\b(sk-[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{12,})\b/ },
  { name: "jwt_like_token", re: /\bey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/ },
  { name: "bearer_token", re: /\bBearer\s+[A-Za-z0-9\-_.]{20,}/i },
  { name: "pem_private_key", re: /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----/ },
];

const RAW_FILE_URI_PATTERNS: ReadonlyArray<{ name: string; re: RegExp }> = [
  { name: "file_uri", re: /\bfile:\/\//i },
  { name: "s3_uri", re: /\bs3:\/\//i },
  { name: "gcs_uri", re: /\bgs:\/\//i },
  { name: "unix_absolute_path", re: /(^|\s)\/(Users|home)\//i },
  { name: "windows_absolute_path", re: /\b[A-Za-z]:\\/ },
  { name: "generic_url", re: /\bhttps?:\/\/\S+/i },
];

const DELIMITED_ROW_PATTERN = /([^,\n]+,){2,}[^,\n]+/;
const TAB_DELIMITED_PATTERN = /\S+\t+\S+/;
const MAX_FREE_TEXT_LENGTH = 300;

function assertNoDataValueShape(value: string, path: string): void {
  for (const { name, re } of RAW_FILE_URI_PATTERNS) {
    if (re.test(value)) {
      throw APIError.invalidArgument(
        `AI_GOVERNANCE_DOSSIER_RAW_URI_REJECTED: "${path}" looks like a ${name} — raw file URIs/paths are never allowed in this dossier`
      );
    }
  }
  for (const { name, re } of CREDENTIAL_PATTERNS) {
    if (re.test(value)) {
      throw APIError.invalidArgument(
        `AI_GOVERNANCE_DOSSIER_CREDENTIAL_REJECTED: "${path}" looks like a ${name} — API credentials/provider secrets are never allowed in this dossier`
      );
    }
  }
  if (DELIMITED_ROW_PATTERN.test(value) || TAB_DELIMITED_PATTERN.test(value)) {
    throw APIError.invalidArgument(
      `AI_GOVERNANCE_DOSSIER_FIELD_SAMPLE_REJECTED: "${path}" looks like a delimited data row rather than a reference label — raw prompt/output text is never allowed in this dossier`
    );
  }
  if (value.length > MAX_FREE_TEXT_LENGTH) {
    throw APIError.invalidArgument(
      `AI_GOVERNANCE_DOSSIER_FIELD_SAMPLE_REJECTED: "${path}" exceeds ${MAX_FREE_TEXT_LENGTH} characters — this looks like a pasted prompt/output transcript, not a reference label`
    );
  }
}

function isEmbeddingVectorShaped(arr: unknown[]): boolean {
  return arr.length > 0 && arr.every((v) => typeof v === "number");
}

function deepAssertSafeShape(value: unknown, path: string): void {
  if (typeof value === "string") {
    assertNoDataValueShape(value, path);
  } else if (Array.isArray(value)) {
    if (isEmbeddingVectorShaped(value)) {
      throw APIError.invalidArgument(
        `AI_GOVERNANCE_DOSSIER_EMBEDDING_REJECTED: "${path}" looks like an embedding vector (an array of numbers) — embeddings are never allowed in this dossier`
      );
    }
    value.forEach((v, i) => deepAssertSafeShape(v, `${path}[${i}]`));
  } else if (value && typeof value === "object") {
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      deepAssertSafeShape(v, `${path}.${k}`);
    }
  }
}

function assertPlainObject(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw APIError.invalidArgument(`AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: "${path}" must be an object`);
  }
  return value as Record<string, unknown>;
}

function assertOnlyAllowedKeys(obj: Record<string, unknown>, allowed: ReadonlySet<string>, path: string): void {
  for (const key of Object.keys(obj)) {
    if (!allowed.has(key)) {
      throw APIError.invalidArgument(
        `AI_GOVERNANCE_DOSSIER_FIELD_REJECTED: "${key}" is not an allowed field on ${path} — this dossier only accepts a signed snapshot reference, risk signal classifications and redacted source references`
      );
    }
  }
}

function assertValidReasonCode(value: unknown, path: string): AiGovernanceReasonCode {
  if (typeof value !== "string" || !AI_GOVERNANCE_REASON_CODES.has(value)) {
    throw APIError.invalidArgument(
      `AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: "${path}" must be one of the fixed allowed reason codes — free text is not accepted`
    );
  }
  return value as AiGovernanceReasonCode;
}

function normalizeRefList(raw: unknown, path: string): AiGovernanceRef[] {
  if (!Array.isArray(raw) || raw.length === 0) {
    throw APIError.invalidArgument(`AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: "${path}" must be a non-empty array`);
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `${path}[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_REF_KEYS, `${path}[${i}]`);
    const { id, version, definitionHash } = obj;
    if (typeof id !== "string" || !id.trim() || typeof version !== "string" || !version.trim() || typeof definitionHash !== "string" || !definitionHash.trim()) {
      throw APIError.invalidArgument(
        `AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: "${path}[${i}]" requires non-empty id/version/definitionHash`
      );
    }
    return { id, version, definitionHash };
  });
}

function validateSnapshotShape(raw: unknown): AiGovernanceSnapshotDraft {
  const obj = assertPlainObject(raw, "snapshot");
  assertOnlyAllowedKeys(obj, ALLOWED_SNAPSHOT_KEYS, "snapshot");
  deepAssertSafeShape(obj, "snapshot");

  if (typeof obj.workspaceId !== "string" || !obj.workspaceId.trim()) {
    throw APIError.invalidArgument("AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: snapshot.workspaceId is required");
  }
  if (typeof obj.projectId !== "string" || !obj.projectId.trim()) {
    throw APIError.invalidArgument("AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: snapshot.projectId is required");
  }
  if (obj.status !== "VERIFIED") {
    throw APIError.invalidArgument("AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: snapshot.status must be VERIFIED");
  }
  if (typeof obj.observedAt !== "string" || Number.isNaN(Date.parse(obj.observedAt))) {
    throw APIError.invalidArgument("AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: snapshot.observedAt must be an ISO timestamp");
  }
  if (typeof obj.signature !== "string" || !obj.signature.trim()) {
    throw APIError.invalidArgument("AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: snapshot.signature is required");
  }

  return {
    workspaceId: obj.workspaceId,
    projectId: obj.projectId,
    policy: normalizeRefList(obj.policy, "snapshot.policy"),
    evaluators: normalizeRefList(obj.evaluators, "snapshot.evaluators"),
    status: "VERIFIED",
    observedAt: obj.observedAt,
    signature: obj.signature,
  };
}

function normalizeRiskSignals(raw: unknown): RiskSignal[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    throw APIError.invalidArgument("AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: riskSignals must be an array");
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `riskSignals[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_RISK_SIGNAL_KEYS, `riskSignals[${i}]`);
    if (typeof obj.category !== "string" || !RISK_SIGNAL_CATEGORIES.has(obj.category)) {
      throw APIError.invalidArgument(
        `AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: riskSignals[${i}].category must be one of the fixed allowed categories`
      );
    }
    if (typeof obj.severity !== "string" || !RISK_SIGNAL_SEVERITIES.has(obj.severity)) {
      throw APIError.invalidArgument(
        `AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: riskSignals[${i}].severity must be one of the fixed allowed severities`
      );
    }
    return { category: obj.category as RiskSignalCategory, severity: obj.severity as RiskSignalSeverity };
  });
}

function normalizeSourceRefs(raw: unknown): AiGovernanceSourceRef[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    throw APIError.invalidArgument("AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: sourceRefs must be an array");
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `sourceRefs[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_SOURCE_REF_KEYS, `sourceRefs[${i}]`);
    if (typeof obj.sourceRef !== "string" || !obj.sourceRef.trim()) {
      throw APIError.invalidArgument(`AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: sourceRefs[${i}].sourceRef is required`);
    }
    if (obj.classification !== undefined && typeof obj.classification !== "string") {
      throw APIError.invalidArgument(`AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: sourceRefs[${i}].classification must be a string`);
    }
    if (obj.redactedExcerpt !== undefined && typeof obj.redactedExcerpt !== "string") {
      throw APIError.invalidArgument(`AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: sourceRefs[${i}].redactedExcerpt must be a string`);
    }
    return {
      sourceRef: obj.sourceRef,
      classification: obj.classification as string | undefined,
      redactedExcerpt: obj.redactedExcerpt as string | undefined,
    };
  });
}

function validateCreateInput(input: unknown): CreateAiGovernanceDossierInput {
  const obj = assertPlainObject(input, "input");
  assertOnlyAllowedKeys(obj, ALLOWED_CREATE_KEYS, "input");
  deepAssertSafeShape(obj, "input");
  if (typeof obj.projectId !== "string" || !obj.projectId.trim()) {
    throw APIError.invalidArgument("projectId is required");
  }
  return {
    projectId: obj.projectId,
    snapshot: validateSnapshotShape(obj.snapshot),
    riskSignals: normalizeRiskSignals(obj.riskSignals),
    sourceRefs: normalizeSourceRefs(obj.sourceRefs),
    reasonCode: assertValidReasonCode(obj.reasonCode, "reasonCode"),
  };
}

function validateAppendInput(input: unknown): AppendAiGovernanceRevisionInput {
  const obj = assertPlainObject(input, "input");
  assertOnlyAllowedKeys(obj, ALLOWED_APPEND_KEYS, "input");
  deepAssertSafeShape(obj, "input");
  if (obj.status !== undefined && obj.status !== "DRAFT" && obj.status !== "CONFIRMED") {
    throw APIError.invalidArgument("AI_GOVERNANCE_DOSSIER_SHAPE_INVALID: status must be DRAFT or CONFIRMED");
  }
  return {
    snapshot: validateSnapshotShape(obj.snapshot),
    riskSignals: normalizeRiskSignals(obj.riskSignals),
    sourceRefs: normalizeSourceRefs(obj.sourceRefs),
    status: obj.status as "DRAFT" | "CONFIRMED" | undefined,
    reasonCode: assertValidReasonCode(obj.reasonCode, "reasonCode"),
  };
}

/**
 * Verify signature + binding (workspace/project) + staleness — "stale/
 * foreign/unverifiable source fails closed" (task-2-brief §Global
 * Constraints). Chạy TRƯỚC khi bất kỳ field snapshot nào chạm DB. Throw
 * `failed_precondition` cho MỌI lý do fail (không phân biệt lý do cụ thể
 * trong error CODE — chỉ trong message — để không lộ oracle giúp caller dò
 * ra secret/binding qua side channel).
 */
function assertVerifiedSnapshotBinding(
  ctx: TenantContext,
  targetProjectId: string,
  snapshot: AiGovernanceSnapshotDraft
): void {
  const signed: SignedAiGovernanceSnapshot = {
    workspaceId: snapshot.workspaceId,
    projectId: snapshot.projectId,
    policy: snapshot.policy,
    evaluators: snapshot.evaluators,
    status: snapshot.status,
    observedAt: snapshot.observedAt,
    signature: snapshot.signature,
  };

  if (!verifyAiGovernanceSnapshotSignature(signed)) {
    throw APIError.failedPrecondition(
      "AI_GOVERNANCE_SNAPSHOT_UNVERIFIABLE: snapshot signature is missing, malformed or does not match its content — unsigned/tampered sources fail closed"
    );
  }

  if (snapshot.workspaceId !== ctx.workspaceId) {
    throw APIError.failedPrecondition(
      "AI_GOVERNANCE_SNAPSHOT_FOREIGN_WORKSPACE: snapshot is bound to a different workspace than this dossier"
    );
  }
  if (snapshot.projectId !== targetProjectId) {
    throw APIError.failedPrecondition(
      "AI_GOVERNANCE_SNAPSHOT_FOREIGN_PROJECT: snapshot is bound to a different project than this dossier"
    );
  }

  const observedAtMs = Date.parse(snapshot.observedAt);
  const now = Date.now();
  if (now - observedAtMs > SNAPSHOT_STALENESS_WINDOW_MS) {
    throw APIError.failedPrecondition(
      `AI_GOVERNANCE_SNAPSHOT_STALE: snapshot.observedAt is older than the ${SNAPSHOT_STALENESS_WINDOW_MS / 3_600_000}h staleness window`
    );
  }
  if (observedAtMs - now > SNAPSHOT_FUTURE_SKEW_MS) {
    throw APIError.failedPrecondition(
      "AI_GOVERNANCE_SNAPSHOT_STALE: snapshot.observedAt is implausibly far in the future"
    );
  }
}

/**
 * Opaque reference hash cho 1 snapshot đã verify — KHÔNG lưu raw `signature`
 * (vật liệu mật mã học của chữ ký, dù không "nhạy cảm" theo nghĩa business
 * content, không có lý do gì phải tồn tại vĩnh viễn trong 1 bảng business
 * evidence) — thay vào đó lưu 1 hash tham chiếu độc lập của toàn bộ envelope
 * đã verify, đủ để chứng minh "đây đúng là snapshot nào" khi audit mà không
 * mang theo giá trị chữ ký gốc.
 */
function computeSnapshotRef(snapshot: AiGovernanceSnapshotDraft): string {
  return createHash("sha256")
    .update(
      JSON.stringify({
        workspaceId: snapshot.workspaceId,
        projectId: snapshot.projectId,
        policy: snapshot.policy,
        evaluators: snapshot.evaluators,
        status: snapshot.status,
        observedAt: snapshot.observedAt,
      })
    )
    .digest("hex");
}

/**
 * Guard bắt buộc: chỉ human context (không phải AI agent) mới được tạo/append
 * AI Governance Dossier — "Founder confirms a governance decision; no agent
 * can write the dossier as a confirmation" (task-2-brief §Global
 * Constraints; CLAUDE.md quy tắc 5, 8). Mirror
 * data-governance-dossier.service.ts::requireHumanContext.
 */
function requireHumanContext(ctx: TenantContext): void {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }
  if (ctx.isAiAgent) {
    throw APIError.permissionDenied(
      "AI_GOVERNANCE_DOSSIER_HUMAN_REQUIRED: Only a human Founder/member context can create or append an AI governance dossier"
    );
  }
}

async function requireHumanProjectContext(ctx: TenantContext, projectId: string): Promise<{ id: bigint }> {
  requireHumanContext(ctx);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.permissionDenied("PROJECT_ACCESS_DENIED: project does not belong to this workspace");
  }

  return project;
}

function toSnapshot(
  dossierId: bigint,
  revisionRow: {
    version: number;
    status: string;
    snapshotRef: string;
    policy: unknown;
    evaluators: unknown;
    observedAt: Date | string;
    riskSignals: unknown;
    sourceRefs: unknown;
  }
): AiGovernanceDossierSnapshot {
  const observedAt = revisionRow.observedAt instanceof Date ? revisionRow.observedAt.toISOString() : String(revisionRow.observedAt);
  return {
    dossierId: dossierId.toString(),
    revision: revisionRow.version,
    status: revisionRow.status as AiGovernanceDossierStatus,
    snapshotRef: revisionRow.snapshotRef,
    policy: (revisionRow.policy as AiGovernanceRef[]) ?? [],
    evaluators: (revisionRow.evaluators as AiGovernanceRef[]) ?? [],
    observedAt,
    riskSignals: (revisionRow.riskSignals as RiskSignal[]) ?? [],
    sourceRefs: (revisionRow.sourceRefs as AiGovernanceSourceRef[]) ?? [],
  };
}

/**
 * Founder/member tạo AI Governance Dossier mới cho Project (revision 1,
 * status DRAFT). Model/agent context không bao giờ tới được nhánh này.
 * Snapshot phải verify được signature + binding + staleness TRƯỚC khi bất kỳ
 * field nào được ghi.
 */
export async function createAiGovernanceDossier(
  ctx: TenantContext,
  input: CreateAiGovernanceDossierInput
): Promise<AiGovernanceDossierSnapshot> {
  const validated = validateCreateInput(input);

  await requireHumanProjectContext(ctx, validated.projectId);
  assertVerifiedSnapshotBinding(ctx, validated.projectId, validated.snapshot);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(validated.projectId);
  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const snapshotRef = computeSnapshotRef(validated.snapshot);

  try {
    return await db.transaction(async (tx) => {
      const dossierId = generateSnowflake();

      // `uix_ai_governance_dossiers_project` (migration 022) bắt buộc duy
      // nhất 1 dossier/project.
      await tx.insert(aiGovernanceDossiers).values({
        id: dossierId,
        workspaceId: wsId,
        projectId: projId,
        status: "DRAFT",
        currentVersion: 1,
        createdByMemberId: actorMemberId,
      });

      const [revision] = await tx
        .insert(aiGovernanceDossierRevisions)
        .values({
          id: generateSnowflake(),
          workspaceId: wsId,
          projectId: projId,
          dossierId,
          version: 1,
          status: "DRAFT",
          snapshotRef,
          policy: validated.snapshot.policy,
          evaluators: validated.snapshot.evaluators,
          observedAt: new Date(validated.snapshot.observedAt),
          riskSignals: validated.riskSignals,
          sourceRefs: validated.sourceRefs,
          reasonCode: validated.reasonCode,
          actorMemberId,
        })
        .returning();

      if (!revision) throw APIError.internal("failed to create ai governance dossier");

      return toSnapshot(dossierId, revision);
    });
  } catch (err: any) {
    if (err?.cause?.code === "23505" || err?.code === "23505") {
      throw APIError.alreadyExists("an ai governance dossier already exists for this project");
    }
    throw err;
  }
}

/**
 * Founder/member append một revision mới (CAS theo expectedVersion). Đặt
 * status "CONFIRMED" chỉ hợp lệ khi ctx là human founder/co-founder. Model/
 * agent context luôn bị chặn ở `requireHumanContext` trước khi chạm DB.
 */
export async function appendAiGovernanceRevision(
  ctx: TenantContext,
  dossierId: string,
  expectedVersion: number,
  input: AppendAiGovernanceRevisionInput
): Promise<AiGovernanceDossierSnapshot> {
  requireHumanContext(ctx);

  const validated = validateAppendInput(input);

  const wsId = BigInt(ctx.workspaceId);
  const dossierBigId = BigInt(dossierId);

  const [dossier] = await db
    .select()
    .from(aiGovernanceDossiers)
    .where(and(eq(aiGovernanceDossiers.id, dossierBigId), eq(aiGovernanceDossiers.workspaceId, wsId)))
    .limit(1);
  if (!dossier) throw APIError.notFound("ai governance dossier not found in workspace");

  assertVerifiedSnapshotBinding(ctx, dossier.projectId.toString(), validated.snapshot);

  if (dossier.currentVersion !== expectedVersion) {
    throw APIError.aborted(
      `CAS_CONFLICT: stale dossier version (expected ${expectedVersion}, got ${dossier.currentVersion})`
    );
  }

  const nextStatus = validated.status ?? (dossier.status as AiGovernanceDossierStatus) ?? "DRAFT";
  if (nextStatus === "CONFIRMED") {
    const role = (ctx.membershipRole || "").toLowerCase();
    if (!["founder", "co-founder"].includes(role)) {
      throw APIError.permissionDenied(
        "FOUNDER_CONFIRMATION_REQUIRED: Only a human founder can confirm an ai governance dossier revision"
      );
    }
  }

  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const nextVersion = dossier.currentVersion + 1;
  const snapshotRef = computeSnapshotRef(validated.snapshot);

  return db.transaction(async (tx) => {
    const [prior] = await tx
      .select({ id: aiGovernanceDossierRevisions.id })
      .from(aiGovernanceDossierRevisions)
      .where(eq(aiGovernanceDossierRevisions.dossierId, dossierBigId))
      .orderBy(desc(aiGovernanceDossierRevisions.version))
      .limit(1);

    const [revision] = await tx
      .insert(aiGovernanceDossierRevisions)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: dossier.projectId,
        dossierId: dossierBigId,
        version: nextVersion,
        status: nextStatus,
        snapshotRef,
        policy: validated.snapshot.policy,
        evaluators: validated.snapshot.evaluators,
        observedAt: new Date(validated.snapshot.observedAt),
        riskSignals: validated.riskSignals,
        sourceRefs: validated.sourceRefs,
        reasonCode: validated.reasonCode,
        actorMemberId,
        confirmedByMemberId: nextStatus === "CONFIRMED" ? actorMemberId : null,
        confirmedAt: nextStatus === "CONFIRMED" ? new Date() : null,
        supersedesRevisionId: prior?.id ?? null,
      })
      .returning();
    if (!revision) throw APIError.internal("failed to append ai governance dossier revision");

    const [updatedDossier] = await tx
      .update(aiGovernanceDossiers)
      .set({
        currentVersion: nextVersion,
        status: nextStatus,
        updatedAt: new Date(),
      })
      .where(and(eq(aiGovernanceDossiers.id, dossierBigId), eq(aiGovernanceDossiers.currentVersion, expectedVersion)))
      .returning();
    if (!updatedDossier) {
      throw APIError.aborted("CAS_CONFLICT: dossier changed concurrently");
    }

    return toSnapshot(dossierBigId, revision);
  });
}

/**
 * Đọc snapshot mới nhất (chỉ reference/hash/status/thời điểm — KHÔNG BAO GIỜ
 * raw signature/prompt/output/credential) của AI Governance Dossier theo
 * Project. Model/agent context ĐƯỢC PHÉP đọc (chỉ không được ghi). Project ở
 * workspace khác hoặc project khác trong CÙNG workspace đều bị từ chối.
 */
export async function readAiGovernanceSnapshot(
  ctx: TenantContext,
  projectId: string
): Promise<AiGovernanceDossierSnapshot> {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);
  if (!project) {
    throw APIError.permissionDenied("PROJECT_ACCESS_DENIED: project does not belong to this workspace");
  }

  const [dossier] = await db
    .select()
    .from(aiGovernanceDossiers)
    .where(and(eq(aiGovernanceDossiers.workspaceId, wsId), eq(aiGovernanceDossiers.projectId, projId)))
    .orderBy(desc(aiGovernanceDossiers.updatedAt))
    .limit(1);
  if (!dossier) {
    throw APIError.notFound("no ai governance dossier found for this project");
  }

  const [revision] = await db
    .select()
    .from(aiGovernanceDossierRevisions)
    .where(eq(aiGovernanceDossierRevisions.dossierId, dossier.id))
    .orderBy(desc(aiGovernanceDossierRevisions.version))
    .limit(1);
  if (!revision) {
    throw APIError.internal("ai governance dossier has no revisions");
  }

  return toSnapshot(dossier.id, revision);
}
