import { APIError } from "encore.dev/api";
import { eq, and, desc, inArray } from "drizzle-orm";
import { db, schema } from "../../models/db";

const {
  aiComplianceSnapshots,
  workspaceAiDeployments,
  aiRiskAssessments,
  aiProviderProfiles,
  aiSystemCatalog,
  aiSystemVersions,
  aiSystemCapabilityBindings,
  regulationVersions,
} = schema;

export async function getSystemKeyForVersion(systemVersionId: bigint): Promise<string> {
  const [version] = await db
    .select()
    .from(aiSystemVersions)
    .where(eq(aiSystemVersions.id, systemVersionId));

  if (!version) {
    throw APIError.notFound("AI system version not found");
  }

  const [catalog] = await db
    .select()
    .from(aiSystemCatalog)
    .where(eq(aiSystemCatalog.id, version.systemCatalogId));

  if (!catalog) {
    throw APIError.notFound("AI system catalog not found");
  }

  return catalog.systemKey;
}

export async function findDeploymentForCapture(
  wsId: bigint,
  deploymentIdInput?: string | bigint
) {
  return deploymentIdInput
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
}

export async function getDeclaredCapabilityIds(systemVersionId: bigint): Promise<string[]> {
  const declaredBindings = await db
    .select()
    .from(aiSystemCapabilityBindings)
    .where(eq(aiSystemCapabilityBindings.systemVersionId, systemVersionId));

  return declaredBindings
    .filter((b) => !b.prohibitedPurpose)
    .map((b) => b.capabilityId);
}

export async function insertComplianceSnapshotRecord(values: typeof aiComplianceSnapshots.$inferInsert) {
  const [created] = await db
    .insert(aiComplianceSnapshots)
    .values(values)
    .returning();
  return created;
}

export async function listComplianceSnapshots(workspaceId: bigint) {
  return db
    .select()
    .from(aiComplianceSnapshots)
    .where(eq(aiComplianceSnapshots.workspaceId, workspaceId))
    .orderBy(desc(aiComplianceSnapshots.createdAt));
}

export async function findProviderProfileById(providerProfileId: bigint) {
  const [providerProfile] = await db
    .select()
    .from(aiProviderProfiles)
    .where(eq(aiProviderProfiles.id, providerProfileId));
  return providerProfile;
}

export async function findRegulationVersionsByIds(legalVersionIds: string[]) {
  if (legalVersionIds.length === 0) return [];
  return db
    .select()
    .from(regulationVersions)
    .where(inArray(regulationVersions.id, legalVersionIds.map(BigInt)));
}

export async function findRiskAssessmentById(assessmentId: bigint) {
  const [assessment] = await db
    .select()
    .from(aiRiskAssessments)
    .where(eq(aiRiskAssessments.id, assessmentId));
  return assessment;
}
