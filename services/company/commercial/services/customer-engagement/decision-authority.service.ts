import { APIError } from "encore.dev/api";
import { and, eq, gte, isNull, lt, or, sql } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

export interface ApprovalPolicy {
  required_capabilities: string[];
  distinct_approvers: number;
  requester_must_differ: boolean;
  requester_cannot_execute: boolean;
}

export interface AuthorityDTO {
  id: string;
  workspaceId: string;
  authorityKey: string;
  decisionKind: string;
  approvalPolicy: ApprovalPolicy;
  version: number;
  status: "pending_binding" | "enabled";
  effectiveFrom: string;
  effectiveUntil: string | null;
}

function assertContextWorkspace(workspaceId: string, ctx: TenantContext): void {
  if (String(workspaceId) !== String(ctx.workspaceId)) {
    throw APIError.permissionDenied("workspace mismatch");
  }
}

export async function seedDecisionAuthority(
  {
    workspaceId,
    authorityKey,
    decisionKind,
    matchCriteria = {},
    approvalPolicy,
  }: {
    workspaceId: string;
    authorityKey: string;
    decisionKind: string;
    matchCriteria?: Record<string, unknown>;
    approvalPolicy: ApprovalPolicy;
  },
  ctx: TenantContext,
): Promise<AuthorityDTO> {
  assertContextWorkspace(workspaceId, ctx);
  const id = BigInt(generateSnowflake());
  const [inserted] = await db
    .insert(schema.engagementDecisionAuthorities)
    .values({
      id,
      workspaceId: BigInt(workspaceId),
      authorityKey,
      decisionKind,
      matchCriteria,
      approvalPolicy,
      version: 1,
      status: "pending_binding",
    })
    .returning();

  return rowToAuthority(inserted);
}

export async function grantAuthorityCapability(
  {
    workspaceId,
    authorityKey,
    workforceMemberId,
    capability,
    activeUntil,
  }: {
    workspaceId: string;
    authorityKey: string;
    workforceMemberId: string | bigint;
    capability: string;
    activeUntil?: Date;
  },
  ctx: TenantContext,
): Promise<void> {
  assertContextWorkspace(workspaceId, ctx);
  const memberId = typeof workforceMemberId === "string" ? BigInt(workforceMemberId) : workforceMemberId;

  await db
    .insert(schema.engagementDecisionAuthorityGrants)
    .values({
      id: BigInt(generateSnowflake()),
      workspaceId: BigInt(workspaceId),
      authorityKey,
      workforceMemberId: memberId,
      capability,
      activeUntil: activeUntil || null,
    });

  await recomputeAuthorityStatus(authorityKey, ctx);
}

export async function recomputeAuthorityStatus(
  authorityKey: string,
  ctx: TenantContext,
): Promise<"pending_binding" | "enabled"> {
  const authority = await db.query.engagementDecisionAuthorities.findFirst({
    where: and(eq(schema.engagementDecisionAuthorities.workspaceId, BigInt(ctx.workspaceId)), eq(schema.engagementDecisionAuthorities.authorityKey, authorityKey)),
  });

  if (!authority) {
    throw APIError.notFound(`authority not found: ${authorityKey}`);
  }

  const requiredCapabilities = (authority.approvalPolicy as any).required_capabilities as string[];
  const now = new Date();

  // Check if every required capability has at least one active grant
  for (const cap of requiredCapabilities) {
    const grant = await db.query.engagementDecisionAuthorityGrants.findFirst({
      where: and(
        eq(schema.engagementDecisionAuthorityGrants.workspaceId, BigInt(ctx.workspaceId)),
        eq(schema.engagementDecisionAuthorityGrants.authorityKey, authorityKey),
        eq(schema.engagementDecisionAuthorityGrants.capability, cap),
        gte(schema.engagementDecisionAuthorityGrants.activeFrom, new Date(0)), // active_from <= now
        or(
          isNull(schema.engagementDecisionAuthorityGrants.activeUntil),
          gte(schema.engagementDecisionAuthorityGrants.activeUntil, now),
        ),
      ),
    });

    if (!grant) {
      // Capability missing: stay pending
      await db
        .update(schema.engagementDecisionAuthorities)
        .set({ status: "pending_binding" })
        .where(eq(schema.engagementDecisionAuthorities.id, authority.id));
      return "pending_binding";
    }
  }

  // All capabilities covered: enable
  await db
    .update(schema.engagementDecisionAuthorities)
    .set({ status: "enabled" })
    .where(eq(schema.engagementDecisionAuthorities.id, authority.id));
  return "enabled";
}

export async function resolveEnabledAuthority(
  authorityKey: string,
  ctx: TenantContext,
): Promise<{ authority: AuthorityDTO; approvalPolicy: ApprovalPolicy }> {
  const now = new Date();
  const authority = await db.query.engagementDecisionAuthorities.findFirst({
    where: and(
      eq(schema.engagementDecisionAuthorities.workspaceId, BigInt(ctx.workspaceId)),
      eq(schema.engagementDecisionAuthorities.authorityKey, authorityKey),
      eq(schema.engagementDecisionAuthorities.status, "enabled"),
      gte(schema.engagementDecisionAuthorities.effectiveFrom, new Date(0)),
      or(
        isNull(schema.engagementDecisionAuthorities.effectiveUntil),
        gte(schema.engagementDecisionAuthorities.effectiveUntil, now),
      ),
    ),
  });

  if (!authority) {
    throw APIError.failedPrecondition(`authority not enabled: ${authorityKey}`);
  }

  return {
    authority: rowToAuthority(authority),
    approvalPolicy: authority.approvalPolicy as ApprovalPolicy,
  };
}

export async function memberCoversCapability(
  workforceMemberId: string | bigint,
  authorityKey: string,
  ctx: TenantContext,
): Promise<string | null> {
  const memberId = typeof workforceMemberId === "string" ? BigInt(workforceMemberId) : workforceMemberId;
  const now = new Date();

  const grant = await db.query.engagementDecisionAuthorityGrants.findFirst({
    where: and(
      eq(schema.engagementDecisionAuthorityGrants.workspaceId, BigInt(ctx.workspaceId)),
      eq(schema.engagementDecisionAuthorityGrants.authorityKey, authorityKey),
      eq(schema.engagementDecisionAuthorityGrants.workforceMemberId, memberId),
      gte(schema.engagementDecisionAuthorityGrants.activeFrom, new Date(0)),
      or(
        isNull(schema.engagementDecisionAuthorityGrants.activeUntil),
        gte(schema.engagementDecisionAuthorityGrants.activeUntil, now),
      ),
    ),
  });

  return grant?.capability ?? null;
}

export function assertApprovalPolicySatisfied(
  approvalPolicy: ApprovalPolicy,
  approvalRows: Array<{ workforceMemberId: bigint | string; capability: string; decision: string }>,
): void {
  // Filter for approve decisions only
  const approvalDecisions = approvalRows.filter((r) => r.decision === "approve");

  // Count distinct members
  const distinctMembers = new Set(approvalDecisions.map((r) => (typeof r.workforceMemberId === "string" ? r.workforceMemberId : String(r.workforceMemberId))));

  if (distinctMembers.size < approvalPolicy.distinct_approvers) {
    throw APIError.failedPrecondition(
      `insufficient distinct approvers: ${distinctMembers.size} < ${approvalPolicy.distinct_approvers}`,
    );
  }

  // Check capability coverage
  const coveredCapabilities = new Set(approvalDecisions.map((r) => r.capability));
  for (const reqCap of approvalPolicy.required_capabilities) {
    if (!coveredCapabilities.has(reqCap)) {
      throw APIError.failedPrecondition(`missing required capability: ${reqCap}`);
    }
  }
}

function rowToAuthority(row: any): AuthorityDTO {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    authorityKey: row.authorityKey,
    decisionKind: row.decisionKind,
    approvalPolicy: row.approvalPolicy as ApprovalPolicy,
    version: row.version,
    status: row.status as "pending_binding" | "enabled",
    effectiveFrom: row.effectiveFrom instanceof Date ? row.effectiveFrom.toISOString() : row.effectiveFrom,
    effectiveUntil: row.effectiveUntil ? (row.effectiveUntil instanceof Date ? row.effectiveUntil.toISOString() : row.effectiveUntil) : null,
  };
}
