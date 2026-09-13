import { APIError } from "encore.dev/api";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { EvidenceRef } from "./product-decision-dossier.service";

const { projects, securityPostureDossiers, securityPostureDossierRevisions } = schema;

export type SecurityPostureDossierStatus = "DRAFT" | "CONFIRMED" | "SUPERSEDED";

export type FindingSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

const FINDING_SEVERITIES: ReadonlySet<string> = new Set<FindingSeverity>([
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
]);

// Thứ tự nghiêm trọng tăng dần — dùng để tính severity tổng hợp (max) của
// một revision từ danh sách findings.
const SEVERITY_RANK: Record<FindingSeverity, number> = {
  LOW: 0,
  MEDIUM: 1,
  HIGH: 2,
  CRITICAL: 3,
};

/**
 * Allowlist cố định control category — mirror RiskSignalCategory của People
 * Risk Dossier. KHÔNG phải danh sách gợi ý, mà là toàn bộ tập hợp giá trị
 * hợp lệ — chống nhét raw config/credential text vào field category tự do.
 */
export type SecurityControlCategory =
  | "access_control"
  | "data_protection"
  | "network_security"
  | "secrets_management"
  | "logging_monitoring"
  | "vulnerability_management"
  | "incident_response"
  | "third_party_risk";

const SECURITY_CONTROL_CATEGORIES: ReadonlySet<string> = new Set<SecurityControlCategory>([
  "access_control",
  "data_protection",
  "network_security",
  "secrets_management",
  "logging_monitoring",
  "vulnerability_management",
  "incident_response",
  "third_party_risk",
]);

export type SecurityControlState = "IMPLEMENTED" | "PARTIAL" | "MISSING" | "NOT_APPLICABLE";

const SECURITY_CONTROL_STATES: ReadonlySet<string> = new Set<SecurityControlState>([
  "IMPLEMENTED",
  "PARTIAL",
  "MISSING",
  "NOT_APPLICABLE",
]);

/**
 * Allowlist cố định finding category — KHÔNG chứa raw vulnerability payload,
 * chỉ nhãn phân loại đã classify.
 */
export type SecurityFindingCategory =
  | "exposed_secret"
  | "misconfiguration"
  | "outdated_dependency"
  | "missing_control"
  | "policy_gap"
  | "access_anomaly";

const SECURITY_FINDING_CATEGORIES: ReadonlySet<string> = new Set<SecurityFindingCategory>([
  "exposed_secret",
  "misconfiguration",
  "outdated_dependency",
  "missing_control",
  "policy_gap",
  "access_anomaly",
]);

/**
 * Allowlist cố định cho `reasonCode` — KHÔNG free text, mirror People Risk
 * Dossier's hardened form (không có trường narrative/free-text nào trên
 * write path — một trường tự do sẽ đánh bại chính headline secret-free
 * property của dossier này, vì secret không có "shape" cố định để quét hết
 * bằng regex).
 */
export type SecurityPostureReasonCode =
  | "INITIAL_ASSESSMENT"
  | "CONTROL_UPDATED"
  | "FINDING_ADDED"
  | "EVIDENCE_UPDATED"
  | "FOUNDER_REVIEW";

const SECURITY_POSTURE_REASON_CODES: ReadonlySet<string> = new Set<SecurityPostureReasonCode>([
  "INITIAL_ASSESSMENT",
  "CONTROL_UPDATED",
  "FINDING_ADDED",
  "EVIDENCE_UPDATED",
  "FOUNDER_REVIEW",
]);

/**
 * Control state: nhãn đã phân loại (category cố định + state cố định) +
 * `controlId` tự do NHƯNG bị deep-scan chặn nếu trông giống secret. KHÔNG có
 * trường config/credential text nào khác.
 */
export interface SecurityControl {
  controlId: string;
  category: SecurityControlCategory;
  state: SecurityControlState;
}

/**
 * Finding: nhãn đã phân loại (category cố định + severity cố định) tham
 * chiếu tới nguồn qua `sourceRef`/`classification` — mirror pattern
 * reference-only của `EvidenceRef`. KHÔNG có trường raw payload nào khác.
 */
export interface SecurityFinding {
  category: SecurityFindingCategory;
  severity: FindingSeverity;
  sourceRef: string;
  classification?: string;
}

export interface SecurityPostureSnapshot {
  dossierId: string;
  revision: number;
  severity: FindingSeverity;
  controlStates: SecurityControl[];
  findings: SecurityFinding[];
  evidenceRefs: EvidenceRef[];
  status: SecurityPostureDossierStatus;
}

export interface CreateSecurityPostureDossierInput {
  projectId: string;
  controls?: SecurityControl[];
  findings?: SecurityFinding[];
  evidenceRefs?: EvidenceRef[];
  reasonCode: SecurityPostureReasonCode;
}

export interface AppendSecurityPostureRevisionInput {
  controls?: SecurityControl[];
  findings?: SecurityFinding[];
  evidenceRefs?: EvidenceRef[];
  status?: "DRAFT" | "CONFIRMED";
  reasonCode: SecurityPostureReasonCode;
}

// ---------------------------------------------------------------------------
// Validation — allowlist nghiêm ngặt, KHÔNG denylist theo tên trường secret.
// Bất kỳ key nào ngoài allowlist, hoặc bất kỳ string nào "trông giống"
// password/token/API key/private key/full HTTP header (ở BẤT KỲ vị trí nào
// trong input, kể cả field hợp lệ), đều bị reject bằng
// `APIError.invalidArgument`. Đây là headline secret-free property của
// dossier này (xem task-1-brief §Global Constraints) — test riêng cho từng
// nhánh reject, không chỉ tin tưởng TypeScript type (không sống sót qua
// JSON.parse).
// ---------------------------------------------------------------------------

const ALLOWED_CREATE_KEYS = new Set([
  "projectId",
  "controls",
  "findings",
  "evidenceRefs",
  "reasonCode",
]);

const ALLOWED_APPEND_KEYS = new Set([
  "controls",
  "findings",
  "evidenceRefs",
  "status",
  "reasonCode",
]);

const ALLOWED_CONTROL_KEYS = new Set(["controlId", "category", "state"]);
const ALLOWED_FINDING_KEYS = new Set(["category", "severity", "sourceRef", "classification"]);
const ALLOWED_EVIDENCE_REF_KEYS = new Set(["sourceRef", "classification", "redactedExcerpt"]);

// Các pattern "trông giống secret" — thực dụng và có thể test, không cố xây
// một secret-detector hoàn hảo. Mirror đúng danh sách ví dụ tường minh của
// task-1-brief: "passwords, tokens, private keys, full request headers, raw
// vulnerability payloads and infrastructure topology". Raw payload/topology
// không có shape cố định để quét bằng regex — được chặn ở lớp allowlist-key
// (field lạ luôn bị reject), lớp này chỉ quét giá trị của field HỢP LỆ.
const SECRET_PATTERNS: ReadonlyArray<{ name: string; re: RegExp }> = [
  // API key / token có tiền tố phổ biến: OpenAI-style sk-, GitHub ghp_/gho_/
  // ghu_/ghs_/ghr_, AWS access key AKIA.
  { name: "api_key_or_token", re: /\b(sk-[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{12,})\b/ },
  // JWT-shaped token: 3 đoạn base64url phân tách bằng dấu chấm.
  { name: "jwt_like_token", re: /\bey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/ },
  // Generic "Bearer <token>" — dấu hiệu của raw credential bị dán nhầm vào.
  { name: "bearer_token", re: /\bBearer\s+[A-Za-z0-9\-_.]{20,}/i },
  // PEM private key header — không phân biệt loại key (RSA/EC/OPENSSH/...).
  { name: "pem_private_key", re: /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----/ },
  // Full request header blob (Authorization:/Cookie:) — dấu hiệu của raw
  // HTTP header bị dán nhầm vào thay vì tham chiếu đã redact.
  { name: "raw_http_header", re: /\b(Authorization|Cookie)\s*:\s*\S+/i },
];

function assertNoSecretLikeString(value: string, path: string): void {
  for (const { name, re } of SECRET_PATTERNS) {
    if (re.test(value)) {
      throw APIError.invalidArgument(
        `SECURITY_DOSSIER_SECRET_REJECTED: "${path}" looks like a ${name} — secrets and raw credentials are never allowed in this dossier`
      );
    }
  }
}

/**
 * Quét đệ quy TOÀN BỘ input tìm chuỗi giống secret — kể cả những field đã
 * nằm trong allowlist key. Đây là lớp phòng thủ độc lập với check
 * allowlist-key: một field hợp lệ như `controlId` hay `sourceRef` vẫn có thể
 * bị nhét token/private key dạng text, nên phải quét giá trị chứ không chỉ
 * tên khoá (mirror `deepAssertNoPii` của People Risk Dossier).
 */
function deepAssertNoSecret(value: unknown, path: string): void {
  if (typeof value === "string") {
    assertNoSecretLikeString(value, path);
  } else if (Array.isArray(value)) {
    value.forEach((v, i) => deepAssertNoSecret(v, `${path}[${i}]`));
  } else if (value && typeof value === "object") {
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      deepAssertNoSecret(v, `${path}.${k}`);
    }
  }
}

function assertPlainObject(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw APIError.invalidArgument(`SECURITY_DOSSIER_SHAPE_INVALID: "${path}" must be an object`);
  }
  return value as Record<string, unknown>;
}

/**
 * Allowlist thuần tuý theo tên field — bất kỳ key nào không có trong
 * `allowed` bị reject NGAY LẬP TỨC, kể cả khi giá trị của nó không giống
 * secret (ví dụ `infraTopology: "abc"`). An toàn hơn denylist theo tên field
 * đã biết vì không cần đoán trước hết mọi biến thể tên field.
 */
function assertOnlyAllowedKeys(obj: Record<string, unknown>, allowed: ReadonlySet<string>, path: string): void {
  for (const key of Object.keys(obj)) {
    if (!allowed.has(key)) {
      throw APIError.invalidArgument(
        `SECURITY_DOSSIER_FIELD_REJECTED: "${key}" is not an allowed field on ${path} — this dossier only accepts classified control/finding metadata`
      );
    }
  }
}

function assertValidReasonCode(value: unknown, path: string): SecurityPostureReasonCode {
  if (typeof value !== "string" || !SECURITY_POSTURE_REASON_CODES.has(value)) {
    throw APIError.invalidArgument(
      `SECURITY_DOSSIER_SHAPE_INVALID: "${path}" must be one of the fixed allowed reason codes — free text is not accepted`
    );
  }
  return value as SecurityPostureReasonCode;
}

function normalizeControls(raw: unknown): SecurityControl[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    throw APIError.invalidArgument("SECURITY_DOSSIER_SHAPE_INVALID: controls must be an array");
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `controls[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_CONTROL_KEYS, `controls[${i}]`);
    const { controlId, category, state } = obj;
    if (typeof controlId !== "string" || !controlId.trim()) {
      throw APIError.invalidArgument(`SECURITY_DOSSIER_SHAPE_INVALID: controls[${i}].controlId is required`);
    }
    if (!/^[a-zA-Z0-9 _.:-]{1,64}$/.test(controlId)) {
      throw APIError.invalidArgument(`SECURITY_DOSSIER_SHAPE_INVALID: controls[${i}].controlId has an invalid shape`);
    }
    if (typeof category !== "string" || !SECURITY_CONTROL_CATEGORIES.has(category)) {
      throw APIError.invalidArgument(
        `SECURITY_DOSSIER_SHAPE_INVALID: controls[${i}].category must be one of the fixed allowed control categories`
      );
    }
    if (typeof state !== "string" || !SECURITY_CONTROL_STATES.has(state)) {
      throw APIError.invalidArgument(
        `SECURITY_DOSSIER_SHAPE_INVALID: controls[${i}].state must be IMPLEMENTED|PARTIAL|MISSING|NOT_APPLICABLE`
      );
    }
    return {
      controlId,
      category: category as SecurityControlCategory,
      state: state as SecurityControlState,
    };
  });
}

function normalizeFindings(raw: unknown): SecurityFinding[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    throw APIError.invalidArgument("SECURITY_DOSSIER_SHAPE_INVALID: findings must be an array");
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `findings[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_FINDING_KEYS, `findings[${i}]`);
    const { category, severity, sourceRef, classification } = obj;
    if (typeof category !== "string" || !SECURITY_FINDING_CATEGORIES.has(category)) {
      throw APIError.invalidArgument(
        `SECURITY_DOSSIER_SHAPE_INVALID: findings[${i}].category must be one of the fixed allowed finding categories`
      );
    }
    if (typeof severity !== "string" || !FINDING_SEVERITIES.has(severity)) {
      throw APIError.invalidArgument(
        `SECURITY_DOSSIER_SHAPE_INVALID: findings[${i}].severity must be LOW|MEDIUM|HIGH|CRITICAL`
      );
    }
    if (typeof sourceRef !== "string" || !sourceRef.trim()) {
      throw APIError.invalidArgument(`SECURITY_DOSSIER_SHAPE_INVALID: findings[${i}].sourceRef is required`);
    }
    if (classification !== undefined && typeof classification !== "string") {
      throw APIError.invalidArgument(`SECURITY_DOSSIER_SHAPE_INVALID: findings[${i}].classification must be a string`);
    }
    return {
      category: category as SecurityFindingCategory,
      severity: severity as FindingSeverity,
      sourceRef,
      classification: classification as string | undefined,
    };
  });
}

function normalizeEvidenceRefs(raw: unknown): EvidenceRef[] {
  if (raw === undefined) return [];
  if (!Array.isArray(raw)) {
    throw APIError.invalidArgument("SECURITY_DOSSIER_SHAPE_INVALID: evidenceRefs must be an array");
  }
  return raw.map((item, i) => {
    const obj = assertPlainObject(item, `evidenceRefs[${i}]`);
    assertOnlyAllowedKeys(obj, ALLOWED_EVIDENCE_REF_KEYS, `evidenceRefs[${i}]`);
    if (typeof obj.sourceRef !== "string" || !obj.sourceRef.trim()) {
      throw APIError.invalidArgument(`SECURITY_DOSSIER_SHAPE_INVALID: evidenceRefs[${i}].sourceRef is required`);
    }
    if (typeof obj.classification !== "string" || !obj.classification.trim()) {
      throw APIError.invalidArgument(`SECURITY_DOSSIER_SHAPE_INVALID: evidenceRefs[${i}].classification is required`);
    }
    if (obj.redactedExcerpt !== undefined && typeof obj.redactedExcerpt !== "string") {
      throw APIError.invalidArgument(
        `SECURITY_DOSSIER_SHAPE_INVALID: evidenceRefs[${i}].redactedExcerpt must be a string`
      );
    }
    return {
      sourceRef: obj.sourceRef,
      classification: obj.classification,
      redactedExcerpt: obj.redactedExcerpt as string | undefined,
    };
  });
}

/**
 * Severity tổng hợp của revision — max trong findings tại thời điểm ghi.
 * Không có findings → LOW (không có bằng chứng rủi ro nào được ghi nhận).
 */
function computeAggregateSeverity(findings: SecurityFinding[]): FindingSeverity {
  let worst: FindingSeverity = "LOW";
  for (const f of findings) {
    if (SEVERITY_RANK[f.severity] > SEVERITY_RANK[worst]) {
      worst = f.severity;
    }
  }
  return worst;
}

/**
 * Validate + normalize input tạo dossier. Nhận `unknown` (không tin type
 * TypeScript của caller — type không sống sót qua JSON body của HTTP
 * request) và trả về input đã "picked" chỉ những field allowlist, loại bỏ
 * hoàn toàn field lạ (vd. `token`, `password`, `infraTopology`) dù giá trị
 * của nó có giống secret hay không.
 */
function validateCreateInput(input: unknown): CreateSecurityPostureDossierInput {
  const obj = assertPlainObject(input, "input");
  deepAssertNoSecret(obj, "input");
  assertOnlyAllowedKeys(obj, ALLOWED_CREATE_KEYS, "input");
  if (typeof obj.projectId !== "string" || !obj.projectId.trim()) {
    throw APIError.invalidArgument("projectId is required");
  }
  return {
    projectId: obj.projectId,
    controls: normalizeControls(obj.controls),
    findings: normalizeFindings(obj.findings),
    evidenceRefs: normalizeEvidenceRefs(obj.evidenceRefs),
    reasonCode: assertValidReasonCode(obj.reasonCode, "reasonCode"),
  };
}

function validateAppendInput(input: unknown): AppendSecurityPostureRevisionInput {
  const obj = assertPlainObject(input, "input");
  deepAssertNoSecret(obj, "input");
  assertOnlyAllowedKeys(obj, ALLOWED_APPEND_KEYS, "input");
  if (obj.status !== undefined && obj.status !== "DRAFT" && obj.status !== "CONFIRMED") {
    throw APIError.invalidArgument("SECURITY_DOSSIER_SHAPE_INVALID: status must be DRAFT or CONFIRMED");
  }
  return {
    controls: normalizeControls(obj.controls),
    findings: normalizeFindings(obj.findings),
    evidenceRefs: normalizeEvidenceRefs(obj.evidenceRefs),
    status: obj.status as "DRAFT" | "CONFIRMED" | undefined,
    reasonCode: assertValidReasonCode(obj.reasonCode, "reasonCode"),
  };
}

/**
 * Guard bắt buộc: chỉ human context (không phải AI agent) mới được tạo/append
 * Security Posture Dossier — CISO advisory chỉ được đề xuất qua kênh riêng
 * (skillpack, không phải ghi trực tiếp), KHÔNG BAO GIỜ tự ghi bản ghi
 * security posture chính thức (CLAUDE.md quy tắc 1, 5, 8; task-1-brief:
 * "CISO may propose risk/control gaps only"). Project phải thuộc đúng
 * Workspace của ctx — chống truy cập chéo project/workspace.
 *
 * Ghi chú (mirror people-risk-dossier.service.ts): qua các endpoint public
 * hiện có, `ctx.isAiAgent` không bao giờ true trong thực tế — transport-level
 * auth (`requireWorkspaceAccess` → `resolveTenantContext`) đã tự reject bất
 * kỳ token nào ký bởi `COSA_COMPANY_DELEGATION_SECRET` (cách duy nhất
 * `apps/cosa` có thể tự xác thực sang service này) bằng
 * `APIError.unauthenticated` TRƯỚC KHI tới được service function này — xem
 * test "rejects a COSA-delegation-signed token before any TenantContext is
 * built". Check `ctx.isAiAgent` dưới đây vẫn giữ làm defense-in-depth cho một
 * endpoint nội bộ tương lai có thể tái dùng service function này với
 * `TenantContext` dựng từ cosa-delegation.
 */
function requireHumanContext(ctx: TenantContext): void {
  if (!ctx) {
    throw APIError.unauthenticated("Authentication context required");
  }
  if (ctx.isAiAgent) {
    throw APIError.permissionDenied(
      "SECURITY_DOSSIER_HUMAN_REQUIRED: Only a human Founder/member context can create or append a security posture dossier"
    );
  }
}

async function requireHumanProjectContext(
  ctx: TenantContext,
  projectId: string
): Promise<{ id: bigint }> {
  requireHumanContext(ctx);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.permissionDenied(
      "PROJECT_ACCESS_DENIED: project does not belong to this workspace"
    );
  }

  return project;
}

function toSnapshot(dossierId: bigint, revisionRow: {
  version: number;
  status: string;
  severity: string;
  controls: unknown;
  findings: unknown;
  evidenceRefs: unknown;
}): SecurityPostureSnapshot {
  return {
    dossierId: dossierId.toString(),
    revision: revisionRow.version,
    severity: revisionRow.severity as FindingSeverity,
    controlStates: (revisionRow.controls as SecurityControl[]) ?? [],
    findings: (revisionRow.findings as SecurityFinding[]) ?? [],
    evidenceRefs: (revisionRow.evidenceRefs as EvidenceRef[]) ?? [],
    status: revisionRow.status as SecurityPostureDossierStatus,
  };
}

/**
 * Founder/member tạo Security Posture Dossier mới cho Project (revision 1,
 * status DRAFT). Model/agent context không bao giờ tới được nhánh này. Input
 * được validate qua allowlist nghiêm ngặt + deep secret scan — bất kỳ field
 * lạ hay chuỗi trông giống password/token/private key/raw header đều bị
 * reject bằng `invalid_argument`, không âm thầm loại bỏ.
 */
export async function createSecurityPostureDossier(
  ctx: TenantContext,
  input: CreateSecurityPostureDossierInput
): Promise<SecurityPostureSnapshot> {
  const validated = validateCreateInput(input);

  await requireHumanProjectContext(ctx, validated.projectId);

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(validated.projectId);
  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const severity = computeAggregateSeverity(validated.findings ?? []);

  try {
    return await db.transaction(async (tx) => {
      const dossierId = generateSnowflake();

      // `uix_security_posture_dossiers_project` (migration 014) bắt buộc
      // duy nhất 1 dossier/project — race giữa 2 request tạo đồng thời cho
      // cùng project bị chặn ở tầng DB (catch bên dưới).
      await tx.insert(securityPostureDossiers).values({
        id: dossierId,
        workspaceId: wsId,
        projectId: projId,
        status: "DRAFT",
        currentVersion: 1,
        createdByMemberId: actorMemberId,
      });

      const [revision] = await tx
        .insert(securityPostureDossierRevisions)
        .values({
          id: generateSnowflake(),
          workspaceId: wsId,
          projectId: projId,
          dossierId,
          version: 1,
          status: "DRAFT",
          controls: validated.controls,
          findings: validated.findings,
          evidenceRefs: validated.evidenceRefs,
          severity,
          reasonCode: validated.reasonCode,
          actorMemberId,
        })
        .returning();

      if (!revision) throw APIError.internal("failed to create security posture dossier");

      return toSnapshot(dossierId, revision);
    });
  } catch (err: any) {
    if (err?.cause?.code === "23505" || err?.code === "23505") {
      throw APIError.alreadyExists("a security posture dossier already exists for this project");
    }
    throw err;
  }
}

/**
 * Founder/member append một revision mới (CAS theo expectedVersion). Đặt
 * status "CONFIRMED" chỉ hợp lệ khi ctx là human founder/co-founder — đúng
 * tinh thần "A founder alone confirms a security posture decision". Model/
 * agent context luôn bị chặn ở `requireHumanContext` trước khi chạm DB.
 */
export async function appendSecurityPostureRevision(
  ctx: TenantContext,
  dossierId: string,
  expectedVersion: number,
  input: AppendSecurityPostureRevisionInput
): Promise<SecurityPostureSnapshot> {
  // Xem ghi chú đầy đủ ở `requireHumanContext` phía trên.
  requireHumanContext(ctx);

  const validated = validateAppendInput(input);

  const wsId = BigInt(ctx.workspaceId);
  const dossierBigId = BigInt(dossierId);

  const [dossier] = await db
    .select()
    .from(securityPostureDossiers)
    .where(and(eq(securityPostureDossiers.id, dossierBigId), eq(securityPostureDossiers.workspaceId, wsId)))
    .limit(1);
  if (!dossier) throw APIError.notFound("security posture dossier not found in workspace");

  if (dossier.currentVersion !== expectedVersion) {
    throw APIError.aborted(
      `CAS_CONFLICT: stale dossier version (expected ${expectedVersion}, got ${dossier.currentVersion})`
    );
  }

  const nextStatus = validated.status ?? (dossier.status as SecurityPostureDossierStatus) ?? "DRAFT";
  if (nextStatus === "CONFIRMED") {
    const role = (ctx.membershipRole || "").toLowerCase();
    if (!["founder", "co-founder"].includes(role)) {
      throw APIError.permissionDenied(
        "FOUNDER_CONFIRMATION_REQUIRED: Only a human founder can confirm a security posture decision"
      );
    }
  }

  const actorMemberId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const nextVersion = dossier.currentVersion + 1;
  const severity = computeAggregateSeverity(validated.findings ?? []);

  return db.transaction(async (tx) => {
    const [prior] = await tx
      .select({ id: securityPostureDossierRevisions.id })
      .from(securityPostureDossierRevisions)
      .where(eq(securityPostureDossierRevisions.dossierId, dossierBigId))
      .orderBy(desc(securityPostureDossierRevisions.version))
      .limit(1);

    const [revision] = await tx
      .insert(securityPostureDossierRevisions)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: dossier.projectId,
        dossierId: dossierBigId,
        version: nextVersion,
        status: nextStatus,
        controls: validated.controls,
        findings: validated.findings,
        evidenceRefs: validated.evidenceRefs,
        severity,
        reasonCode: validated.reasonCode,
        actorMemberId,
        confirmedByMemberId: nextStatus === "CONFIRMED" ? actorMemberId : null,
        confirmedAt: nextStatus === "CONFIRMED" ? new Date() : null,
        supersedesRevisionId: prior?.id ?? null,
      })
      .returning();
    if (!revision) throw APIError.internal("failed to append security posture dossier revision");

    const [updatedDossier] = await tx
      .update(securityPostureDossiers)
      .set({
        currentVersion: nextVersion,
        status: nextStatus,
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(securityPostureDossiers.id, dossierBigId),
          eq(securityPostureDossiers.currentVersion, expectedVersion)
        )
      )
      .returning();
    if (!updatedDossier) {
      throw APIError.aborted("CAS_CONFLICT: dossier changed concurrently");
    }

    return toSnapshot(dossierBigId, revision);
  });
}

/**
 * Đọc snapshot mới nhất (chỉ classified metadata — controls, findings,
 * evidence_refs — KHÔNG BAO GIỜ raw secret/topology/vulnerability payload)
 * của Security Posture Dossier theo Project. Model/agent context ĐƯỢC PHÉP
 * đọc (chỉ không được ghi). Project ở workspace khác hoặc project khác
 * trong CÙNG workspace đều bị từ chối bằng permission_denied — không lộ
 * thông tin tồn tại/không tồn tại của project chéo tenant hay chéo project.
 */
export async function readSecurityPostureSnapshot(
  ctx: TenantContext,
  projectId: string
): Promise<SecurityPostureSnapshot> {
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
    throw APIError.permissionDenied(
      "PROJECT_ACCESS_DENIED: project does not belong to this workspace"
    );
  }

  const [dossier] = await db
    .select()
    .from(securityPostureDossiers)
    .where(and(eq(securityPostureDossiers.workspaceId, wsId), eq(securityPostureDossiers.projectId, projId)))
    .orderBy(desc(securityPostureDossiers.updatedAt))
    .limit(1);
  if (!dossier) {
    throw APIError.notFound("no security posture dossier found for this project");
  }

  const [revision] = await db
    .select()
    .from(securityPostureDossierRevisions)
    .where(eq(securityPostureDossierRevisions.dossierId, dossier.id))
    .orderBy(desc(securityPostureDossierRevisions.version))
    .limit(1);
  if (!revision) {
    throw APIError.internal("security posture dossier has no revisions");
  }

  return toSnapshot(dossier.id, revision);
}
