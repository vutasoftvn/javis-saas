import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { requireFounderCommand } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { computeCanonicalSha256 } from "./compliance/canonical-hasher";
import { listBookEntriesService } from "./accounting-books.service";
import {
  classifyBookEntry,
  computeMappingDefinitionHash,
  LedgerBucket,
  RegimeMapping,
  TT58_2026_MAPPING,
} from "./accounting-mapping";

const {
  accountingReportMappings,
  accountingMappingConfirmations,
  accountingReportSnapshots,
  accountingPeriods,
} = schema;

/**
 * Seed nội dung `accounting-mapping.ts` vào bảng registry theo exact-hash —
 * cùng pattern SpecResolver/skillpack registry đã dùng cho AgentSpec (không
 * tin trực tiếp object TS đang import). Idempotent: chỉ ghi lại khi hash
 * đổi (nội dung mapping trong code thay đổi).
 */
export async function ensureMappingSeeded(mapping: RegimeMapping = TT58_2026_MAPPING): Promise<void> {
  const definitionHash = computeMappingDefinitionHash(mapping);

  const existing = await db
    .select({ definitionHash: accountingReportMappings.definitionHash })
    .from(accountingReportMappings)
    .where(
      and(
        eq(accountingReportMappings.regimeCode, mapping.regimeCode),
        eq(accountingReportMappings.mappingVersion, mapping.mappingVersion)
      )
    )
    .limit(1);

  if (existing[0]?.definitionHash === definitionHash) {
    return;
  }

  await db.transaction(async (tx) => {
    await tx
      .delete(accountingReportMappings)
      .where(
        and(
          eq(accountingReportMappings.regimeCode, mapping.regimeCode),
          eq(accountingReportMappings.mappingVersion, mapping.mappingVersion)
        )
      );

    for (const line of mapping.lines) {
      await tx.insert(accountingReportMappings).values({
        id: generateSnowflake(),
        regimeCode: mapping.regimeCode,
        mappingVersion: mapping.mappingVersion,
        reportCode: line.reportCode,
        lineCode: line.lineCode,
        officialCode: line.officialCode,
        name: line.name,
        sourceRef: line.sourceRef,
        ruleType: line.ruleType,
        bucket: line.bucket,
        sign: line.sign,
        rounding: line.rounding,
        definitionHash,
      });
    }
  });
}

export interface ReportStatusInput {
  requiredBuckets: LedgerBucket[];
  coveredBuckets: LedgerBucket[];
  mappingConfirmed: boolean;
}

export interface ReportStatusResult {
  status: "INCOMPLETE" | "PROVIDER_NOT_READY" | "VERIFIED";
  issues: string[];
}

export function requireReportMappingBucket(bucket: string | null): LedgerBucket {
  switch (bucket) {
    case "cash":
    case "receivable":
    case "payable":
    case "loan":
    case "advance":
    case "capital":
    case "profit":
      return bucket;
    case null:
      throw APIError.failedPrecondition("report mapping line is missing ledger bucket");
    default:
      throw APIError.failedPrecondition(`report mapping line has invalid ledger bucket: ${bucket}`);
  }
}

export function computeReportStatus(input: ReportStatusInput): ReportStatusResult {
  const issues: string[] = [];
  const covered = new Set(input.coveredBuckets);

  for (const bucket of input.requiredBuckets) {
    if (!covered.has(bucket)) {
      issues.push(`missing_mapping_for_bucket:${bucket}`);
    }
  }

  if (!input.mappingConfirmed) {
    issues.push("mapping_not_confirmed_by_founder");
  }

  return {
    status: issues.length === 0 ? "VERIFIED" : "INCOMPLETE",
    issues,
  };
}

export interface ReportLineView {
  lineCode: string;
  officialCode: string;
  name: string;
  sourceRef: string;
  amountMinor: string;
}

export interface ReportSnapshotView {
  id: string;
  legalEntityId: string;
  periodId: string;
  reportCode: string;
  mappingVersion: string;
  inputWatermark: string;
  lines: ReportLineView[];
  status: "INCOMPLETE" | "PROVIDER_NOT_READY" | "VERIFIED";
  issues: string[];
  generatedAt: string;
}

export interface GenerateReportInput {
  legalEntityId: string;
  periodId: string;
  reportCode: string;
  mappingVersion?: string;
  expectedPeriodVersion?: number;
}

export async function generateReportService(
  ctx: TenantContext,
  input: GenerateReportInput
): Promise<ReportSnapshotView> {
  const mapping = TT58_2026_MAPPING;
  if (input.mappingVersion && input.mappingVersion !== mapping.mappingVersion) {
    throw APIError.invalidArgument(
      `Unknown mappingVersion ${input.mappingVersion}; available: ${mapping.mappingVersion}`
    );
  }

  const knownReportCodes = new Set(mapping.lines.map((line) => line.reportCode));
  if (!knownReportCodes.has(input.reportCode)) {
    throw APIError.invalidArgument(
      `Unknown reportCode ${input.reportCode}; available: ${[...knownReportCodes].join(", ")}`
    );
  }

  if (input.expectedPeriodVersion !== undefined) {
    const [period] = await db
      .select({ id: accountingPeriods.id, version: accountingPeriods.version })
      .from(accountingPeriods)
      .where(
        and(
          eq(accountingPeriods.id, BigInt(input.periodId)),
          eq(accountingPeriods.workspaceId, BigInt(ctx.workspaceId))
        )
      )
      .limit(1);
    if (!period) throw APIError.notFound(`accounting period ${input.periodId} not found`);
    if (period.version !== input.expectedPeriodVersion) {
      throw APIError.aborted(
        `VERSION_CONFLICT: expected period version ${input.expectedPeriodVersion} but current is ${period.version}`
      );
    }
  }

  await ensureMappingSeeded(mapping);

  const mappingLines = await db
    .select()
    .from(accountingReportMappings)
    .where(
      and(
        eq(accountingReportMappings.regimeCode, mapping.regimeCode),
        eq(accountingReportMappings.mappingVersion, mapping.mappingVersion),
        eq(accountingReportMappings.reportCode, input.reportCode)
      )
    );

  const [confirmation] = await db
    .select()
    .from(accountingMappingConfirmations)
    .where(
      and(
        // Chỉ đọc xác nhận CỦA CHÍNH workspace này — xác nhận của workspace
        // khác không được phép nâng report của tenant này lên VERIFIED.
        eq(accountingMappingConfirmations.workspaceId, BigInt(ctx.workspaceId)),
        eq(accountingMappingConfirmations.regimeCode, mapping.regimeCode),
        eq(accountingMappingConfirmations.mappingVersion, mapping.mappingVersion)
      )
    )
    .limit(1);

  const entries = await listBookEntriesService(ctx, {
    legalEntityId: input.legalEntityId,
    periodId: input.periodId,
  });

  const bucketTotals = new Map<LedgerBucket, bigint>();
  for (const entry of entries) {
    const effects = classifyBookEntry(entry.category, BigInt(entry.amountMinor));
    for (const effect of effects) {
      bucketTotals.set(effect.bucket, (bucketTotals.get(effect.bucket) ?? 0n) + effect.amountMinor);
    }
  }

  const reportMappingLines = mappingLines.map((row) => ({
    ...row,
    bucket: requireReportMappingBucket(row.bucket),
  }));

  const lines: ReportLineView[] = reportMappingLines.map((row) => ({
    lineCode: row.lineCode,
    officialCode: row.officialCode,
    name: row.name,
    sourceRef: row.sourceRef,
    amountMinor: String((bucketTotals.get(row.bucket) ?? 0n) * BigInt(row.sign)),
  }));

  const requiredBuckets = reportMappingLines.map((row) => row.bucket);
  const coveredBuckets = requiredBuckets.filter((bucket) => bucketTotals.has(bucket));

  const { status, issues } = computeReportStatus({
    requiredBuckets,
    coveredBuckets,
    mappingConfirmed: Boolean(confirmation),
  });

  const inputWatermark = computeCanonicalSha256({
    mappingVersion: mapping.mappingVersion,
    entries: entries
      .map((e) => ({ id: e.id, category: e.category, amountMinor: e.amountMinor, version: e.version }))
      .sort((a, b) => a.id.localeCompare(b.id)),
  });

  const [row] = await db
    .insert(accountingReportSnapshots)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(ctx.workspaceId),
      legalEntityId: BigInt(input.legalEntityId),
      periodId: BigInt(input.periodId),
      reportCode: input.reportCode,
      mappingVersion: mapping.mappingVersion,
      inputWatermark,
      lines,
      status,
      issues,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to generate report snapshot");

  return {
    id: String(row.id),
    legalEntityId: String(row.legalEntityId),
    periodId: String(row.periodId),
    reportCode: row.reportCode,
    mappingVersion: row.mappingVersion,
    inputWatermark: row.inputWatermark,
    lines: row.lines,
    status: row.status,
    issues: row.issues,
    generatedAt: row.generatedAt.toISOString(),
  };
}

export interface ListReportSnapshotsParams {
  legalEntityId: string;
  periodId: string;
  reportCode?: string;
}

export async function listReportSnapshotsService(
  ctx: TenantContext,
  params: ListReportSnapshotsParams
): Promise<ReportSnapshotView[]> {
  const conditions = [
    eq(accountingReportSnapshots.workspaceId, BigInt(ctx.workspaceId)),
    eq(accountingReportSnapshots.legalEntityId, BigInt(params.legalEntityId)),
    eq(accountingReportSnapshots.periodId, BigInt(params.periodId)),
  ];
  if (params.reportCode) {
    conditions.push(eq(accountingReportSnapshots.reportCode, params.reportCode));
  }

  const rows = await db
    .select()
    .from(accountingReportSnapshots)
    .where(and(...conditions));

  return rows.map((row) => ({
    id: String(row.id),
    legalEntityId: String(row.legalEntityId),
    periodId: String(row.periodId),
    reportCode: row.reportCode,
    mappingVersion: row.mappingVersion,
    inputWatermark: row.inputWatermark,
    lines: row.lines,
    status: row.status,
    issues: row.issues,
    generatedAt: row.generatedAt.toISOString(),
  }));
}

/**
 * Xác nhận nội dung mapping TT58 — chỉ founder được phép, vì mapping quyết
 * định report có thể lên `status=VERIFIED` hay không (business truth, không
 * để LLM/agent tự quyết). Xác nhận có phạm vi THEO WORKSPACE: idempotent theo
 * (workspaceId, regimeCode, mappingVersion) qua unique constraint
 * `uix_mapping_confirmation` (migration 43). Founder chỉ xác nhận cho tenant
 * của mình, không thay mặt tenant khác.
 */
export async function confirmMappingService(
  ctx: TenantContext,
  regimeCode: string,
  mappingVersion: string
): Promise<{ confirmedAt: string }> {
  requireFounderCommand(ctx, "finance.accounting_mapping.confirm");

  if (regimeCode !== TT58_2026_MAPPING.regimeCode || mappingVersion !== TT58_2026_MAPPING.mappingVersion) {
    throw APIError.invalidArgument(`Unknown mapping ${regimeCode}/${mappingVersion}`);
  }
  await ensureMappingSeeded(TT58_2026_MAPPING);

  const [row] = await db
    .insert(accountingMappingConfirmations)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(ctx.workspaceId),
      regimeCode,
      mappingVersion,
      confirmedByMemberId: BigInt(ctx.workforceMemberId ?? ctx.userId),
    })
    .onConflictDoUpdate({
      target: [
        accountingMappingConfirmations.workspaceId,
        accountingMappingConfirmations.regimeCode,
        accountingMappingConfirmations.mappingVersion,
      ],
      set: {
        confirmedByMemberId: BigInt(ctx.workforceMemberId ?? ctx.userId),
        confirmedAt: new Date(),
      },
    })
    .returning();

  if (!row) throw APIError.internal("Failed to record mapping confirmation");
  return { confirmedAt: row.confirmedAt.toISOString() };
}
