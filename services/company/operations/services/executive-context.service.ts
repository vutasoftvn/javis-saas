import { eq, and } from "drizzle-orm";
import { db, schema } from "../db";
import { TenantContext } from "../../shared/types/tenant_context";

const { tasks, okrObjectives, okrCycles, projects } = schema;

// Định nghĩa Evidence Reference — định danh deterministic cho từng entity
export interface ExecutiveEvidenceRef {
  readonly refId: string; // ví dụ "task:12345"
  readonly sourceKind: "task" | "objective" | "project";
  readonly sourceId: string;
  readonly workspaceId: string;
  readonly title: string;
  readonly observedAt: string; // ISO 8601 timestamp
  readonly authorityClass: "BUSINESS_SNAPSHOT";
  readonly redactedExcerpt?: string;
}

// Tổng số entity theo loại
export interface ExecutiveContextTotals {
  readonly tasks: number;
  readonly objectives: number;
  readonly projects: number;
}

// Schema snapshot trả về client
export interface ExecutiveContextSnapshot {
  readonly schemaVersion: "company.executive-context/v1";
  readonly workspaceId: string;
  readonly generatedAt: string; // ISO 8601
  readonly dataAsOf: string; // ISO 8601
  readonly focus?: "delivery_risk" | "objectives" | "general";
  readonly totals: ExecutiveContextTotals;
  readonly evidence: readonly ExecutiveEvidenceRef[];
}

/**
 * Query params cho executive context snapshot
 */
export interface GetExecutiveContextParams {
  readonly workspaceId: string;
  readonly focus?: "delivery_risk" | "objectives" | "general";
  readonly limit?: number;
}

/**
 * Redact sensitive patterns từ title/description
 * — loại bỏ API keys, tokens, credentials pattern
 */
function redactSensitiveContent(text: string): string {
  return text
    .replace(/sk_[a-z_]+[a-z0-9]+/gi, "[REDACTED_KEY]")
    .replace(/pk_[a-z_]+[a-z0-9]+/gi, "[REDACTED_KEY]")
    .replace(/Bearer\s+[a-zA-Z0-9_\-\.]+/g, "[REDACTED_TOKEN]")
    .replace(/token[_=:]\s*[a-zA-Z0-9_\-\.]+/gi, "[REDACTED_TOKEN]")
    .substring(0, 200); // Limit excerpt length
}

/**
 * Fetch và aggregate tasks, objectives, projects từ workspace scoped DB queries
 * Trả về ExecutiveContextSnapshot với evidence refs stable
 */
export async function getExecutiveContextService(
  context: TenantContext,
  params: GetExecutiveContextParams
): Promise<ExecutiveContextSnapshot> {
  const workspaceId = BigInt(context.workspaceId);
  const limit = Math.min(Math.max(params.limit || 50, 1), 50); // Clamp 1..50

  const now = new Date();
  const nowISO = now.toISOString();

  // Query tasks từ workspace này
  const taskRows = await db
    .select()
    .from(tasks)
    .where(
      and(eq(tasks.workspaceId, workspaceId), params.focus === "delivery_risk" ? eq(tasks.status, "blocked") : undefined)
    )
    .limit(limit);

  // Query objectives từ workspace này
  const objectiveRows = await db
    .select()
    .from(okrObjectives)
    .where(eq(okrObjectives.workspaceId, workspaceId))
    .limit(limit);

  // Query projects từ workspace này
  const projectRows = await db
    .select()
    .from(projects)
    .where(eq(projects.workspaceId, workspaceId))
    .limit(limit);

  // Build evidence refs từ entities
  const evidence: ExecutiveEvidenceRef[] = [];

  // Task evidence
  for (const task of taskRows) {
    evidence.push({
      refId: `task:${task.id}`,
      sourceKind: "task",
      sourceId: task.id.toString(),
      workspaceId: task.workspaceId.toString(),
      title: task.title,
      observedAt: (task.updatedAt || task.createdAt)?.toISOString() || nowISO,
      authorityClass: "BUSINESS_SNAPSHOT",
      redactedExcerpt: redactSensitiveContent(task.title),
    });
  }

  // Objective evidence
  for (const objective of objectiveRows) {
    evidence.push({
      refId: `objective:${objective.id}`,
      sourceKind: "objective",
      sourceId: objective.id.toString(),
      workspaceId: objective.workspaceId.toString(),
      title: objective.title,
      observedAt: (objective.updatedAt || objective.createdAt)?.toISOString() || nowISO,
      authorityClass: "BUSINESS_SNAPSHOT",
      redactedExcerpt: redactSensitiveContent(objective.title),
    });
  }

  // Project evidence
  for (const project of projectRows) {
    evidence.push({
      refId: `project:${project.id}`,
      sourceKind: "project",
      sourceId: project.id.toString(),
      workspaceId: project.workspaceId.toString(),
      title: project.title,
      observedAt: (project.updatedAt || project.createdAt)?.toISOString() || nowISO,
      authorityClass: "BUSINESS_SNAPSHOT",
      redactedExcerpt: redactSensitiveContent(project.title),
    });
  }

  // Totals — đếm tất cả entities không limit
  const allTasks = await db
    .select({ id: tasks.id })
    .from(tasks)
    .where(eq(tasks.workspaceId, workspaceId));

  const allObjectives = await db
    .select({ id: okrObjectives.id })
    .from(okrObjectives)
    .where(eq(okrObjectives.workspaceId, workspaceId));

  const allProjects = await db
    .select({ id: projects.id })
    .from(projects)
    .where(eq(projects.workspaceId, workspaceId));

  const snapshot: ExecutiveContextSnapshot = {
    schemaVersion: "company.executive-context/v1",
    workspaceId: context.workspaceId,
    generatedAt: nowISO,
    dataAsOf: nowISO,
    focus: params.focus,
    totals: {
      tasks: allTasks.length,
      objectives: allObjectives.length,
      projects: allProjects.length,
    },
    evidence: Object.freeze(evidence),
  };

  return snapshot;
}
