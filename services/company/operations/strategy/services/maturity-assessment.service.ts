import { APIError } from "encore.dev/api";
import { and, desc, eq, inArray, isNull } from "drizzle-orm";
import { db } from "../../models/db";
import { projects } from "../../../shared/db/schema/operations";
import {
  pmfScoreboardRuns,
  maturityAssessments,
  evidence,
  metricContracts,
} from "../../../shared/db/schema/strategy";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

export type MaturityLevel = "NOT_ASSESSED" | "EARLY" | "REPEATABLE" | "GOVERNED";

export interface MaturityDimension {
  level: MaturityLevel;
  rationale: string;
  missingEvidence: string[];
}

export interface MaturityDimensions {
  measurement: MaturityDimension;
  value: MaturityDimension;
  retention: MaturityDimension;
  commercial: MaturityDimension;
  operational: MaturityDimension;
}

export interface AssessMaturityParams {
  workspaceId: bigint;
  projectId: bigint;
  scoreboardRunId?: bigint;
  actorMemberId?: bigint;
  actorRole?: string;
}

export async function assessMaturity(p: AssessMaturityParams) {
  const [proj] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, p.projectId), eq(projects.workspaceId, p.workspaceId), isNull(projects.deletedAt)))
    .limit(1);

  if (!proj) {
    throw APIError.notFound("Project không tồn tại trong workspace này");
  }

  let scoreboardRun: typeof pmfScoreboardRuns.$inferSelect | undefined;

  if (p.scoreboardRunId) {
    const [run] = await db
      .select()
      .from(pmfScoreboardRuns)
      .where(
        and(
          eq(pmfScoreboardRuns.id, p.scoreboardRunId),
          eq(pmfScoreboardRuns.workspaceId, p.workspaceId),
          eq(pmfScoreboardRuns.projectId, p.projectId)
        )
      )
      .limit(1);

    if (!run) {
      throw APIError.notFound("PMF scoreboard run không tồn tại trong workspace này");
    }
    scoreboardRun = run;
  }

  // Fetch contracts for project
  const contracts = await db
    .select()
    .from(metricContracts)
    .where(
      and(
        eq(metricContracts.workspaceId, p.workspaceId),
        eq(metricContracts.projectId, p.projectId),
        isNull(metricContracts.deletedAt)
      )
    );

  // Fetch reviewed evidence for project
  const reviewedEvidences = await db
    .select()
    .from(evidence)
    .where(
      and(
        eq(evidence.workspaceId, p.workspaceId),
        eq(evidence.projectId, p.projectId),
        eq(evidence.status, "approved"),
        isNull(evidence.deletedAt)
      )
    );

  // Derive 5 dimensions
  const activeContracts = contracts.filter((c) => c.status === "ACTIVE");
  const hasPublishedMetrics = activeContracts.length > 0;

  // 1. Measurement Dimension
  let measurementLevel: MaturityLevel = "NOT_ASSESSED";
  const measurementMissing: string[] = [];
  if (!hasPublishedMetrics) {
    measurementMissing.push("Chưa có Metric Contract được phê duyệt (ACTIVE)");
  }
  if (!scoreboardRun) {
    measurementMissing.push("Chưa có kết quả tính toán PMF Scoreboard");
  }

  if (hasPublishedMetrics && scoreboardRun && scoreboardRun.result === "PROMISING") {
    measurementLevel = "GOVERNED";
  } else if (hasPublishedMetrics && scoreboardRun) {
    measurementLevel = "REPEATABLE";
  } else if (contracts.length > 0) {
    measurementLevel = "EARLY";
  }

  // 2. Value Dimension
  let valueLevel: MaturityLevel = "NOT_ASSESSED";
  const valueMissing: string[] = [];
  const valueEvidence = reviewedEvidences.filter(
    (e) => e.sourceType === "customer_interview" || e.sourceType === "feedback"
  );
  if (valueEvidence.length === 0) {
    valueMissing.push("Chưa có bằng chứng phỏng vấn khách hàng hoặc phản hồi giá trị đã duyệt");
  } else if (valueEvidence.length >= 3) {
    valueLevel = "REPEATABLE";
  } else {
    valueLevel = "EARLY";
  }

  // 3. Retention Dimension
  let retentionLevel: MaturityLevel = "NOT_ASSESSED";
  const retentionMissing: string[] = [];
  const retentionSnapshots = scoreboardRun
    ? (scoreboardRun.scoreComponents as any[]).filter((c) => c.qualityStatus === "VALID")
    : [];
  if (retentionSnapshots.length === 0) {
    retentionMissing.push("Chưa có snapshot telemetry hợp lệ về tỷ lệ retention/hoạt động định kỳ");
  } else if (scoreboardRun?.result === "PROMISING") {
    retentionLevel = "REPEATABLE";
  } else {
    retentionLevel = "EARLY";
  }

  // 4. Commercial Dimension
  let commercialLevel: MaturityLevel = "NOT_ASSESSED";
  const commercialMissing: string[] = [];
  const commercialEvidence = reviewedEvidences.filter((e) => e.sourceType === "pilot_outcome" || e.sourceType === "commercial");
  if (commercialEvidence.length === 0) {
    commercialMissing.push("Chưa có bằng chứng kết quả pilot thương mại hoặc cam kết thanh toán");
  } else {
    commercialLevel = "EARLY";
  }

  // 5. Operational Dimension
  let operationalLevel: MaturityLevel = "NOT_ASSESSED";
  const operationalMissing: string[] = [];
  if (reviewedEvidences.length >= 5 && activeContracts.length >= 2) {
    operationalLevel = "REPEATABLE";
  } else if (reviewedEvidences.length > 0) {
    operationalLevel = "EARLY";
  } else {
    operationalMissing.push("Chưa thiết lập quy trình vận hành thu thập bằng chứng liên tục");
  }

  const dimensions: MaturityDimensions = {
    measurement: {
      level: measurementLevel,
      rationale: `Đánh giá dựa trên ${activeContracts.length} metric contracts và ${scoreboardRun ? "1" : "0"} scoreboard run.`,
      missingEvidence: measurementMissing,
    },
    value: {
      level: valueLevel,
      rationale: `Đánh giá dựa trên ${valueEvidence.length} bằng chứng giá trị khách hàng đã duyệt.`,
      missingEvidence: valueMissing,
    },
    retention: {
      level: retentionLevel,
      rationale: `Đánh giá dựa trên dữ liệu telemetry và snapshot hoạt động.`,
      missingEvidence: retentionMissing,
    },
    commercial: {
      level: commercialLevel,
      rationale: `Đánh giá dựa trên kết quả pilot và sự sẵn sàng thanh toán.`,
      missingEvidence: commercialMissing,
    },
    operational: {
      level: operationalLevel,
      rationale: `Đánh giá dựa trên năng lực thu thập và review bằng chứng định kỳ.`,
      missingEvidence: operationalMissing,
    },
  };

  const now = new Date();
  const id = generateSnowflake();

  const [assessment] = await db
    .insert(maturityAssessments)
    .values({
      id,
      workspaceId: p.workspaceId,
      projectId: p.projectId,
      scoreboardRunId: scoreboardRun?.id ?? null,
      dimensions,
      assessedAt: now,
      createdAt: now,
    })
    .returning();

  if (!assessment) {
    throw APIError.internal("Failed to save maturity assessment");
  }

  return assessment;
}

export async function getMaturityAssessmentInWorkspace(workspaceId: bigint, assessmentId: bigint) {
  const [assessment] = await db
    .select()
    .from(maturityAssessments)
    .where(and(eq(maturityAssessments.id, assessmentId), eq(maturityAssessments.workspaceId, workspaceId)))
    .limit(1);

  if (!assessment) {
    throw APIError.notFound("Maturity assessment không tồn tại trong workspace này");
  }

  return assessment;
}

export async function listMaturityAssessmentsInWorkspace(workspaceId: bigint, projectId?: bigint) {
  if (projectId) {
    return db
      .select()
      .from(maturityAssessments)
      .where(
        and(
          eq(maturityAssessments.workspaceId, workspaceId),
          eq(maturityAssessments.projectId, projectId)
        )
      )
      .orderBy(desc(maturityAssessments.assessedAt));
  }

  return db
    .select()
    .from(maturityAssessments)
    .where(eq(maturityAssessments.workspaceId, workspaceId))
    .orderBy(desc(maturityAssessments.assessedAt));
}

export interface MaturityAssessmentDto {
  id: string;
  workspaceId: string;
  projectId: string;
  scoreboardRunId: string | null;
  dimensions: MaturityDimensions;
  assessedAt: string;
  createdAt: string;
}

export function toMaturityAssessmentDto(row: typeof maturityAssessments.$inferSelect): MaturityAssessmentDto {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    scoreboardRunId: row.scoreboardRunId ? row.scoreboardRunId.toString() : null,
    dimensions: row.dimensions as MaturityDimensions,
    assessedAt: row.assessedAt.toISOString(),
    createdAt: row.createdAt.toISOString(),
  };
}
