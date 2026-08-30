import { createHash } from "node:crypto";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { getProcessingAuthorizationInWorkspace } from "./ai-compliance-access.service";

const {
  aiProviderProfiles,
  aiDataProcessingProfiles,
  dataProcessingAuthorizations,
  dataSubjectRequests,
  workspaceAiDeployments,
} = schema;

export function hashSubjectReference(subjectRef: string): string {
  return createHash("sha256").update(subjectRef.trim()).digest("hex");
}

export function hashProof(proof: string): string {
  return createHash("sha256").update(proof.trim()).digest("hex");
}

export interface UpsertProviderProfileInput {
  workspaceId: string | bigint;
  providerKey: string;
  modelKey: string;
  version: string;
  status: "DRAFT" | "APPROVED" | "SUSPENDED" | "REVOKED";
  declaredProcessingRegion: string;
  dpaReference?: string;
  allowedDataCategories: string[];
  reviewedByMemberId?: string | bigint;
}

export interface UpsertDataProcessingProfileInput {
  workspaceId: string | bigint;
  deploymentId: string | bigint;
  bindingId?: string | bigint;
  purposeId: string;
  dataCategories: string[];
  recipientProviderProfileId: string | bigint;
  retentionPolicyId: string;
  transferConditions?: string[];
  minimizationRequired?: boolean;
  version: string;
  status: "DRAFT" | "ACTIVE" | "SUSPENDED" | "RETIRED";
}

export interface GrantProcessingAuthorizationInput {
  workspaceId: string | bigint;
  subjectReference: string;
  purposeId: string;
  purposeVersion: string;
  authorityType: "CONSENT" | "CONTRACTUAL_NECESSITY" | "LEGAL_OBLIGATION" | "VITAL_INTERESTS" | "LEGITIMATE_INTERESTS";
  proofReference: string;
}

export interface CreateDataSubjectRequestInput {
  workspaceId: string | bigint;
  subjectReference: string;
  requestType: "ACCESS" | "CORRECTION" | "DELETION" | "RESTRICTION";
  deadline: string;
  legalHold?: boolean;
  legalHoldReason?: string;
  handledByMemberId?: string | bigint;
}

export interface ResolveDataUseInput {
  workspaceId: string | bigint;
  deploymentId: string | bigint;
  capabilityId?: string;
  purposeId: string;
  dataCategories: string[];
  providerKey: string;
  subjectReference?: string;
}

export interface DataUseDecision {
  allowed: boolean;
  denialCode: string | null;
  providerProfileVersion: string | null;
  dataProfileVersion: string | null;
  retentionPolicyId: string | null;
  minimizationRequired: boolean;
}

export async function upsertProviderProfile(
  input: UpsertProviderProfileInput
): Promise<typeof aiProviderProfiles.$inferSelect> {
  const wsId = BigInt(input.workspaceId);
  const existing = await db
    .select()
    .from(aiProviderProfiles)
    .where(
      and(
        eq(aiProviderProfiles.workspaceId, wsId),
        eq(aiProviderProfiles.providerKey, input.providerKey),
        eq(aiProviderProfiles.modelKey, input.modelKey),
        eq(aiProviderProfiles.version, input.version)
      )
    );

  const now = new Date();
  if (existing.length > 0) {
    const [updated] = await db
      .update(aiProviderProfiles)
      .set({
        status: input.status,
        declaredProcessingRegion: input.declaredProcessingRegion,
        dpaReference: input.dpaReference,
        allowedDataCategories: input.allowedDataCategories,
        reviewedAt: input.reviewedByMemberId ? now : undefined,
        reviewedByMemberId: input.reviewedByMemberId ? BigInt(input.reviewedByMemberId) : null,
        updatedAt: now,
      })
      .where(eq(aiProviderProfiles.id, existing[0].id))
      .returning();
    return updated;
  }

  const id = generateSnowflake();
  const [created] = await db
    .insert(aiProviderProfiles)
    .values({
      id,
      workspaceId: wsId,
      providerKey: input.providerKey,
      modelKey: input.modelKey,
      version: input.version,
      status: input.status,
      declaredProcessingRegion: input.declaredProcessingRegion,
      dpaReference: input.dpaReference,
      allowedDataCategories: input.allowedDataCategories,
      reviewedAt: input.reviewedByMemberId ? now : null,
      reviewedByMemberId: input.reviewedByMemberId ? BigInt(input.reviewedByMemberId) : null,
    })
    .returning();
  return created;
}

export async function upsertDataProcessingProfile(
  input: UpsertDataProcessingProfileInput
): Promise<typeof aiDataProcessingProfiles.$inferSelect> {
  const wsId = BigInt(input.workspaceId);
  const depId = BigInt(input.deploymentId);

  const existing = await db
    .select()
    .from(aiDataProcessingProfiles)
    .where(
      and(
        eq(aiDataProcessingProfiles.workspaceId, wsId),
        eq(aiDataProcessingProfiles.deploymentId, depId),
        eq(aiDataProcessingProfiles.purposeId, input.purposeId),
        eq(aiDataProcessingProfiles.version, input.version)
      )
    );

  const now = new Date();
  if (existing.length > 0) {
    const [updated] = await db
      .update(aiDataProcessingProfiles)
      .set({
        dataCategories: input.dataCategories,
        recipientProviderProfileId: BigInt(input.recipientProviderProfileId),
        retentionPolicyId: input.retentionPolicyId,
        transferConditions: input.transferConditions || [],
        minimizationRequired: input.minimizationRequired ?? true,
        status: input.status,
        updatedAt: now,
      })
      .where(eq(aiDataProcessingProfiles.id, existing[0].id))
      .returning();
    return updated;
  }

  const id = generateSnowflake();
  const [created] = await db
    .insert(aiDataProcessingProfiles)
    .values({
      id,
      workspaceId: wsId,
      deploymentId: depId,
      bindingId: input.bindingId ? BigInt(input.bindingId) : null,
      purposeId: input.purposeId,
      dataCategories: input.dataCategories,
      recipientProviderProfileId: BigInt(input.recipientProviderProfileId),
      retentionPolicyId: input.retentionPolicyId,
      transferConditions: input.transferConditions || [],
      minimizationRequired: input.minimizationRequired ?? true,
      version: input.version,
      status: input.status,
    })
    .returning();
  return created;
}

export async function grantProcessingAuthorization(
  input: GrantProcessingAuthorizationInput
): Promise<typeof dataProcessingAuthorizations.$inferSelect> {
  const id = generateSnowflake();
  const subjectHash = hashSubjectReference(input.subjectReference);
  const proofHash = hashProof(input.proofReference);

  const [created] = await db
    .insert(dataProcessingAuthorizations)
    .values({
      id,
      workspaceId: BigInt(input.workspaceId),
      subjectReferenceHash: subjectHash,
      purposeId: input.purposeId,
      purposeVersion: input.purposeVersion,
      authorityType: input.authorityType,
      proofReference: input.proofReference,
      proofHash,
      status: "GRANTED",
    })
    .returning();

  return created;
}

export async function withdrawProcessingAuthorization(
  workspaceId: string | bigint,
  authorizationId: string | bigint,
  memberId?: string | bigint
): Promise<typeof dataProcessingAuthorizations.$inferSelect> {
  const authorization = await getProcessingAuthorizationInWorkspace(workspaceId, authorizationId);

  const [updated] = await db
    .update(dataProcessingAuthorizations)
    .set({
      status: "WITHDRAWN",
      withdrawnAt: new Date(),
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(dataProcessingAuthorizations.id, authorization.id),
        eq(dataProcessingAuthorizations.workspaceId, BigInt(workspaceId))
      )
    )
    .returning();

  return updated;
}

export async function createDataSubjectRequest(
  input: CreateDataSubjectRequestInput
): Promise<typeof dataSubjectRequests.$inferSelect> {
  const id = generateSnowflake();
  const subjectHash = hashSubjectReference(input.subjectReference);

  const status = input.legalHold ? "LEGAL_HOLD" : "RECEIVED";

  const [created] = await db
    .insert(dataSubjectRequests)
    .values({
      id,
      workspaceId: BigInt(input.workspaceId),
      subjectReferenceHash: subjectHash,
      requestType: input.requestType,
      deadline: new Date(input.deadline),
      status,
      legalHold: input.legalHold ?? false,
      legalHoldReason: input.legalHoldReason,
      handledByMemberId: input.handledByMemberId ? BigInt(input.handledByMemberId) : null,
    })
    .returning();

  return created;
}

export async function resolveDataUse(
  input: ResolveDataUseInput
): Promise<DataUseDecision> {
  const wsId = BigInt(input.workspaceId);
  const depId = BigInt(input.deploymentId);

  // 1. Check provider profile
  const providerRows = await db
    .select()
    .from(aiProviderProfiles)
    .where(
      and(
        eq(aiProviderProfiles.workspaceId, wsId),
        eq(aiProviderProfiles.providerKey, input.providerKey),
        eq(aiProviderProfiles.status, "APPROVED")
      )
    )
    .orderBy(desc(aiProviderProfiles.createdAt));

  if (providerRows.length === 0) {
    return {
      allowed: false,
      denialCode: "PROVIDER_NOT_APPROVED",
      providerProfileVersion: null,
      dataProfileVersion: null,
      retentionPolicyId: null,
      minimizationRequired: true,
    };
  }

  const provider = providerRows[0];
  const providerAllowedCats = new Set(
    Array.isArray(provider.allowedDataCategories)
      ? (provider.allowedDataCategories as string[])
      : []
  );

  const hasUnpermittedCat = input.dataCategories.some(
    (cat) => !providerAllowedCats.has(cat)
  );
  if (hasUnpermittedCat) {
    return {
      allowed: false,
      denialCode: "PROVIDER_CATEGORY_NOT_PERMITTED",
      providerProfileVersion: provider.version,
      dataProfileVersion: null,
      retentionPolicyId: null,
      minimizationRequired: true,
    };
  }

  // 2. Check data processing profile
  const profileRows = await db
    .select()
    .from(aiDataProcessingProfiles)
    .where(
      and(
        eq(aiDataProcessingProfiles.workspaceId, wsId),
        eq(aiDataProcessingProfiles.deploymentId, depId),
        eq(aiDataProcessingProfiles.purposeId, input.purposeId),
        eq(aiDataProcessingProfiles.status, "ACTIVE")
      )
    )
    .orderBy(desc(aiDataProcessingProfiles.createdAt));

  if (profileRows.length === 0) {
    return {
      allowed: false,
      denialCode: "PROCESSING_PROFILE_NOT_ACTIVE",
      providerProfileVersion: provider.version,
      dataProfileVersion: null,
      retentionPolicyId: null,
      minimizationRequired: true,
    };
  }

  const profile = profileRows[0];

  // 3. Check personal data authorization if subjectReference is supplied or personal categories requested
  const isPersonal = input.dataCategories.some(
    (c) => c === "PERSONAL" || c === "SENSITIVE_PERSONAL"
  );

  if (isPersonal && input.subjectReference) {
    const subjectHash = hashSubjectReference(input.subjectReference);
    const authRows = await db
      .select()
      .from(dataProcessingAuthorizations)
      .where(
        and(
          eq(dataProcessingAuthorizations.workspaceId, wsId),
          eq(dataProcessingAuthorizations.subjectReferenceHash, subjectHash),
          eq(dataProcessingAuthorizations.purposeId, input.purposeId)
        )
      )
      .orderBy(desc(dataProcessingAuthorizations.createdAt));

    if (authRows.length === 0) {
      return {
        allowed: false,
        denialCode: "PROCESSING_AUTHORIZATION_MISSING",
        providerProfileVersion: provider.version,
        dataProfileVersion: profile.version,
        retentionPolicyId: profile.retentionPolicyId,
        minimizationRequired: profile.minimizationRequired,
      };
    }

    const latestAuth = authRows[0];
    if (latestAuth.status === "WITHDRAWN") {
      return {
        allowed: false,
        denialCode: "PROCESSING_AUTHORIZATION_WITHDRAWN",
        providerProfileVersion: provider.version,
        dataProfileVersion: profile.version,
        retentionPolicyId: profile.retentionPolicyId,
        minimizationRequired: profile.minimizationRequired,
      };
    }
    if (latestAuth.status === "RESTRICTED") {
      return {
        allowed: false,
        denialCode: "PROCESSING_AUTHORIZATION_RESTRICTED",
        providerProfileVersion: provider.version,
        dataProfileVersion: profile.version,
        retentionPolicyId: profile.retentionPolicyId,
        minimizationRequired: profile.minimizationRequired,
      };
    }
    if (latestAuth.status !== "GRANTED") {
      return {
        allowed: false,
        denialCode: "PROCESSING_AUTHORIZATION_INVALID",
        providerProfileVersion: provider.version,
        dataProfileVersion: profile.version,
        retentionPolicyId: profile.retentionPolicyId,
        minimizationRequired: profile.minimizationRequired,
      };
    }
  }

  return {
    allowed: true,
    denialCode: null,
    providerProfileVersion: provider.version,
    dataProfileVersion: profile.version,
    retentionPolicyId: profile.retentionPolicyId,
    minimizationRequired: profile.minimizationRequired,
  };
}
