import { createHash } from "node:crypto";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { getComplianceSnapshotInWorkspace } from "./ai-compliance-access.service";

const {
  aiComplianceSnapshots,
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceEvidence,
  aiProviderProfiles,
  aiDataProcessingProfiles,
  aiIncidents,
  aiSystemCatalog,
  aiSystemVersions,
} = schema;

export function canonicalJsonStringify(obj: any): string {
  if (obj === null || typeof obj !== "object") {
    if (typeof obj === "bigint") {
      return JSON.stringify(obj.toString());
    }
    return JSON.stringify(obj);
  }

  if (Array.isArray(obj)) {
    return "[" + obj.map((item) => canonicalJsonStringify(item)).join(",") + "]";
  }

  const keys = Object.keys(obj).sort();
  const pairs = keys.map(
    (k) => JSON.stringify(k) + ":" + canonicalJsonStringify(obj[k])
  );
  return "{" + pairs.join(",") + "}";
}

export function computeCanonicalSha256(content: any): string {
  const canonicalStr = canonicalJsonStringify(content);
  const hash = createHash("sha256").update(canonicalStr).digest("hex");
  return `sha256:${hash}`;
}

export async function captureComplianceSnapshot(
  workspaceId: string | bigint,
  deploymentIdInput?: string | bigint
): Promise<typeof aiComplianceSnapshots.$inferSelect> {
  const wsId = BigInt(workspaceId);

  // Find deployment or create active reference. Khi deploymentIdInput được
  // truyền từ caller, PHẢI xác nhận deployment đó thuộc đúng workspaceId
  // trước khi dùng — nếu không, một workspace khác có thể chụp snapshot
  // "gắn" vào deployment của workspace khác (cross-workspace IDOR).
  let deploymentRow = deploymentIdInput
    ? (await db
        .select()
        .from(workspaceAiDeployments)
        .where(
          and(
            eq(workspaceAiDeployments.id, BigInt(deploymentIdInput)),
            eq(workspaceAiDeployments.workspaceId, wsId)
          )
        ))[0]
    : (await db
        .select()
        .from(workspaceAiDeployments)
        .where(eq(workspaceAiDeployments.workspaceId, wsId))
        .orderBy(desc(workspaceAiDeployments.createdAt)))[0];

  let assessmentId: bigint;
  if (!deploymentRow) {
    // Generate minimal catalog/version/deployment/assessment for baseline snapshot
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();
    const depId = generateSnowflake();
    const assessId = generateSnowflake();

    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey: `default-system-${Date.now()}`,
      name: "Default System",
      allowedPurposes: ["advisory"],
      prohibitedPurposes: [],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: "sha256:default",
      status: "ACTIVE",
    });

    const [dep] = await db
      .insert(workspaceAiDeployments)
      .values({
        id: depId,
        workspaceId: wsId,
        systemVersionId: versionId,
        mode: "ADVISORY_ONLY",
        status: "ASSESSED",
        founderMemberId: generateSnowflake(),
      })
      .returning();

    const [ass] = await db
      .insert(aiRiskAssessments)
      .values({
        id: assessId,
        workspaceId: wsId,
        deploymentId: depId,
        classification: "OUT_OF_CATALOG",
        intendedPurpose: "advisory",
        controls: ["HUMAN_CONFIRMATION"],
        status: "APPROVED",
        expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
      })
      .returning();

    deploymentRow = dep;
    assessmentId = ass.id;
  } else {
    if (deploymentRow.currentAssessmentId) {
      assessmentId = deploymentRow.currentAssessmentId;
    } else {
      const assessments = await db
        .select()
        .from(aiRiskAssessments)
        .where(eq(aiRiskAssessments.deploymentId, deploymentRow.id))
        .orderBy(desc(aiRiskAssessments.createdAt));
      if (assessments.length > 0) {
        assessmentId = assessments[0].id;
      } else {
        const assessId = generateSnowflake();
        const [ass] = await db
          .insert(aiRiskAssessments)
          .values({
            id: assessId,
            workspaceId: wsId,
            deploymentId: deploymentRow.id,
            classification: "OUT_OF_CATALOG",
            intendedPurpose: "advisory",
            controls: ["HUMAN_CONFIRMATION"],
            status: "PENDING",
            expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
          })
          .returning();
        assessmentId = ass.id;
      }
    }
  }

  const providerRows = await db
    .select()
    .from(aiProviderProfiles)
    .where(eq(aiProviderProfiles.workspaceId, wsId))
    .orderBy(desc(aiProviderProfiles.createdAt));

  const dataProfileRows = await db
    .select()
    .from(aiDataProcessingProfiles)
    .where(eq(aiDataProcessingProfiles.deploymentId, deploymentRow.id))
    .orderBy(desc(aiDataProcessingProfiles.createdAt));

  const providerProfileVersion = providerRows[0]?.version || "1.0.0";
  const dataProfileVersion = dataProfileRows[0]?.version || "1.0.0";

  const policyContent = {
    workspaceId: wsId.toString(),
    deploymentId: deploymentRow.id.toString(),
    assessmentId: assessmentId.toString(),
    mode: deploymentRow.mode,
    status: deploymentRow.status,
    providerProfileVersion,
    dataProfileVersion,
    allowedCapabilities: [],
  };

  const policySnapshotHash = computeCanonicalSha256(policyContent);

  const snapshotPayload = {
    ...policyContent,
    policySnapshotHash,
    issuedAt: new Date().toISOString(),
  };

  const snapshotHash = computeCanonicalSha256(snapshotPayload);
  const snapshotId = generateSnowflake();
  const now = new Date();
  const expiresAt = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000);

  const [created] = await db
    .insert(aiComplianceSnapshots)
    .values({
      id: snapshotId,
      workspaceId: wsId,
      deploymentId: deploymentRow.id,
      assessmentId,
      mode: "ADVISORY_ONLY",
      status: deploymentRow.status,
      allowedCapabilities: [],
      providerProfileVersion,
      dataProfileVersion,
      legalVersionIds: [],
      policySnapshotHash,
      snapshotHash,
      issuedAt: now,
      expiresAt,
    })
    .returning();

  return created;
}

export async function verifySnapshotIntegrity(
  workspaceId: string | bigint,
  snapshotId: string | bigint
): Promise<boolean> {
  const snapshot = await getComplianceSnapshotInWorkspace(workspaceId, snapshotId);

  const payloadToVerify = {
    workspaceId: snapshot.workspaceId.toString(),
    deploymentId: snapshot.deploymentId.toString(),
    assessmentId: snapshot.assessmentId.toString(),
    mode: snapshot.mode,
    status: snapshot.status,
    providerProfileVersion: snapshot.providerProfileVersion,
    dataProfileVersion: snapshot.dataProfileVersion,
    allowedCapabilities: snapshot.allowedCapabilities,
    policySnapshotHash: snapshot.policySnapshotHash,
    issuedAt: snapshot.issuedAt.toISOString(),
  };

  const calculatedHash = computeCanonicalSha256(payloadToVerify);
  return calculatedHash === snapshot.snapshotHash;
}

export async function listSnapshots(
  workspaceId: string | bigint
): Promise<Array<typeof aiComplianceSnapshots.$inferSelect>> {
  return db
    .select()
    .from(aiComplianceSnapshots)
    .where(eq(aiComplianceSnapshots.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(aiComplianceSnapshots.createdAt));
}

export interface ResolveComplianceSnapshotInput {
  workspaceId: string | bigint;
  deploymentId?: string | bigint;
  policySnapshotHash?: string;
}

export async function resolveComplianceSnapshot(
  input: ResolveComplianceSnapshotInput
): Promise<typeof aiComplianceSnapshots.$inferSelect> {
  return captureComplianceSnapshot(input.workspaceId, input.deploymentId);
}

