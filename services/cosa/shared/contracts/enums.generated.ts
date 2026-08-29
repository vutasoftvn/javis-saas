/**
 * GENERATED — KHÔNG SỬA TAY.
 * Nguồn: shared/contracts/enums.json · Sinh bởi: scripts/gen-contracts.mjs
 * Đổi enum ⇒ sửa JSON nguồn rồi chạy `node scripts/gen-contracts.mjs` và commit.
 */

/** Vòng đời trưởng thành của Workspace — độc lập với Project và Legal Entity. Cấm alias: company_stage, ventureStage, S0_GENESIS..S5_SCALE. */
export const WORKSPACE_LIFECYCLE_STAGE = ["W0_IDEA", "W1_PROBLEM_VALIDATION", "W2_SOLUTION_VALIDATION", "W3_MVP_BUILD", "W4_PRODUCT_MARKET_FIT", "W5_SCALE"] as const;
export type WorkspaceLifecycleStage = (typeof WORKSPACE_LIFECYCLE_STAGE)[number];
export function isWorkspaceLifecycleStage(v: unknown): v is WorkspaceLifecycleStage {
  return typeof v === "string" && (WORKSPACE_LIFECYCLE_STAGE as readonly string[]).includes(v);
}
export function parseWorkspaceLifecycleStage(v: string): WorkspaceLifecycleStage {
  if (!isWorkspaceLifecycleStage(v)) throw new Error(`Unknown WorkspaceLifecycleStage wire value: ${v}`);
  return v;
}

/** Vòng đời của một Project bên trong Workspace — độc lập với Workspace stage. Prefix P bắt buộc. */
export const PROJECT_LIFECYCLE_STAGE = ["P0_DISCOVERY", "P1_PROBLEM_VALIDATION", "P2_SOLUTION_VALIDATION", "P3_BUILD_VALIDATE", "P4_GO_TO_MARKET", "P5_OPERATE_GROWTH", "P6_SCALE_GOVERN"] as const;
export type ProjectLifecycleStage = (typeof PROJECT_LIFECYCLE_STAGE)[number];
export function isProjectLifecycleStage(v: unknown): v is ProjectLifecycleStage {
  return typeof v === "string" && (PROJECT_LIFECYCLE_STAGE as readonly string[]).includes(v);
}
export function parseProjectLifecycleStage(v: string): ProjectLifecycleStage {
  if (!isProjectLifecycleStage(v)) throw new Error(`Unknown ProjectLifecycleStage wire value: ${v}`);
  return v;
}

/** Trạng thái vận hành của Workspace. */
export const WORKSPACE_STATUS = ["ACTIVE", "ARCHIVED", "SUSPENDED"] as const;
export type WorkspaceStatus = (typeof WORKSPACE_STATUS)[number];
export function isWorkspaceStatus(v: unknown): v is WorkspaceStatus {
  return typeof v === "string" && (WORKSPACE_STATUS as readonly string[]).includes(v);
}
export function parseWorkspaceStatus(v: string): WorkspaceStatus {
  if (!isWorkspaceStatus(v)) throw new Error(`Unknown WorkspaceStatus wire value: ${v}`);
  return v;
}

/** Trạng thái vận hành của Project. */
export const PROJECT_STATUS = ["ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"] as const;
export type ProjectStatus = (typeof PROJECT_STATUS)[number];
export function isProjectStatus(v: unknown): v is ProjectStatus {
  return typeof v === "string" && (PROJECT_STATUS as readonly string[]).includes(v);
}
export function parseProjectStatus(v: string): ProjectStatus {
  if (!isProjectStatus(v)) throw new Error(`Unknown ProjectStatus wire value: ${v}`);
  return v;
}

/** Chế độ vận hành Runtime Fabric của Workspace. Không gộp thành một cờ online=true. */
export const RUNTIME_MODE = ["LOCAL_ONLY", "REMOTE_ACCESS", "CLOUD_CONTINUITY"] as const;
export type RuntimeMode = (typeof RUNTIME_MODE)[number];
export function isRuntimeMode(v: unknown): v is RuntimeMode {
  return typeof v === "string" && (RUNTIME_MODE as readonly string[]).includes(v);
}
export function parseRuntimeMode(v: string): RuntimeMode {
  if (!isRuntimeMode(v)) throw new Error(`Unknown RuntimeMode wire value: ${v}`);
  return v;
}

/** Phạm vi dữ liệu được sync ra ngoài host. Credentials không bao giờ sync raw. */
export const SYNC_POLICY = ["CONTROL_METADATA_ONLY", "SELECTIVE_ENCRYPTED", "FULL_ENCRYPTED"] as const;
export type SyncPolicy = (typeof SYNC_POLICY)[number];
export function isSyncPolicy(v: unknown): v is SyncPolicy {
  return typeof v === "string" && (SYNC_POLICY as readonly string[]).includes(v);
}
export function parseSyncPolicy(v: string): SyncPolicy {
  if (!isSyncPolicy(v)) throw new Error(`Unknown SyncPolicy wire value: ${v}`);
  return v;
}

/** Trạng thái đồng bộ hiện tại của Workspace. */
export const SYNC_STATUS = ["LOCAL_ONLY", "PENDING", "IN_SYNC", "CONFLICT", "ERROR"] as const;
export type SyncStatus = (typeof SYNC_STATUS)[number];
export function isSyncStatus(v: unknown): v is SyncStatus {
  return typeof v === "string" && (SYNC_STATUS as readonly string[]).includes(v);
}
export function parseSyncStatus(v: string): SyncStatus {
  if (!isSyncStatus(v)) throw new Error(`Unknown SyncStatus wire value: ${v}`);
  return v;
}

/** Vòng đời pháp nhân — KHÔNG map thành Workspace stage. Bỏ REGISTRATION_READINESS. */
export const LEGAL_ENTITY_STATUS = ["DRAFT", "REGISTRATION_PREPARATION", "REGISTERED_UNVERIFIED", "VERIFIED", "SUSPENDED", "DISSOLVED"] as const;
export type LegalEntityStatus = (typeof LEGAL_ENTITY_STATUS)[number];
export function isLegalEntityStatus(v: unknown): v is LegalEntityStatus {
  return typeof v === "string" && (LEGAL_ENTITY_STATUS as readonly string[]).includes(v);
}
export function parseLegalEntityStatus(v: string): LegalEntityStatus {
  if (!isLegalEntityStatus(v)) throw new Error(`Unknown LegalEntityStatus wire value: ${v}`);
  return v;
}

export const LEGACY_WORKSPACE_STAGE_TO_CANONICAL: Readonly<Record<string, string>> = Object.freeze({"S0_GENESIS":"W0_IDEA","S1_PROBLEM_VALIDATION":"W1_PROBLEM_VALIDATION","S2_SOLUTION_VALIDATION":"W2_SOLUTION_VALIDATION","S3_MVP_BUILD":"W3_MVP_BUILD","S4_PRODUCT_MARKET_FIT":"W4_PRODUCT_MARKET_FIT","S5_SCALE":"W5_SCALE"});
export const LEGACY_PROJECT_STAGE_TO_CANONICAL: Readonly<Record<string, string>> = Object.freeze({"S0_EXPLORE":"P0_DISCOVERY","S1_PROBLEM_VALIDATION":"P1_PROBLEM_VALIDATION","S2_SOLUTION_VALIDATION":"P2_SOLUTION_VALIDATION","S3_BUSINESS_VALIDATION":"P3_BUILD_VALIDATE","S4_GO_TO_MARKET":"P4_GO_TO_MARKET","S5_OPERATE_GROWTH":"P5_OPERATE_GROWTH","S6_SCALE_GOVERN":"P6_SCALE_GOVERN"});
