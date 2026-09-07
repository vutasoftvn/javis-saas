import { APIError } from "encore.dev/api";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { requireFounderCommand } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { computeCanonicalSha256 } from "./compliance/canonical-hasher";
import { listBookEntriesService } from "./accounting-books.service";
import { getAccountingPolicyService } from "./accounting-policy.service";
import {
  classifyBookEntry,
  computeMappingDefinitionHash,
  DerivedLineKind,
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
 *
 * Kiểm tra không chỉ definitionHash mà cả số dòng đã persist khớp
 * `derivedKind` mong đợi — hash tính từ `mapping.lines` trong code nên
 * không tự phát hiện được một bug insert cũ (thiếu ghi cột derived_kind)
 * từng làm dữ liệu persisted lệch khỏi mapping dù hash so khớp; chỉ so
 * hash sẽ khiến registry "trông như mới" trong khi rows cũ thực ra thiếu
 * cột, gây lỗi "missing ledger bucket" khi generateReportService đọc lại.
 */
export async function ensureMappingSeeded(mapping: RegimeMapping = TT58_2026_MAPPING): Promise<void> {
  const definitionHash = computeMappingDefinitionHash(mapping);

  const existing = await db
    .select({
      definitionHash: accountingReportMappings.definitionHash,
      derivedKind: accountingReportMappings.derivedKind,
    })
    .from(accountingReportMappings)
    .where(
      and(
        eq(accountingReportMappings.regimeCode, mapping.regimeCode),
        eq(accountingReportMappings.mappingVersion, mapping.mappingVersion)
      )
    );

  const expectedDerivedCount = mapping.lines.filter((line) => line.derivedKind).length;
  const actualDerivedCount = existing.filter((row) => row.derivedKind != null).length;
  const isFresh =
    existing.length === mapping.lines.length &&
    existing.every((row) => row.definitionHash === definitionHash) &&
    actualDerivedCount === expectedDerivedCount;

  if (isFresh) {
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

    // Upsert theo `uix_report_mapping_line` (migration 42) thay vì insert
    // trần: hai lời gọi đồng thời cùng thấy dữ liệu cũ đều chạy delete+insert,
    // và insert của lời gọi thứ hai đâm vào unique constraint -> 500. Không
    // sai dữ liệu (tự lành ở lần gọi sau) nhưng tránh được thì tránh.
    //
    // Vẫn GIỮ `tx.delete` phía trên: upsert một mình chỉ ghi đè đúng những
    // line_code có trong `mapping.lines`, nên nếu một version về sau bớt dòng
    // đi thì dòng cũ sẽ bị bỏ mồ côi — và `isFresh` (so khớp số dòng) sẽ
    // không bao giờ thỏa mãn nữa, khiến mọi lời gọi đều phải seed lại.
    for (const line of mapping.lines) {
      await tx
        .insert(accountingReportMappings)
        .values({
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
          derivedKind: line.derivedKind ?? null,
          sign: line.sign,
          rounding: line.rounding,
          definitionHash,
        })
        .onConflictDoUpdate({
          target: [
            accountingReportMappings.regimeCode,
            accountingReportMappings.mappingVersion,
            accountingReportMappings.reportCode,
            accountingReportMappings.lineCode,
          ],
          set: {
            officialCode: line.officialCode,
            name: line.name,
            sourceRef: line.sourceRef,
            ruleType: line.ruleType,
            bucket: line.bucket,
            derivedKind: line.derivedKind ?? null,
            sign: line.sign,
            rounding: line.rounding,
            definitionHash,
          },
        });
    }
  });
}

export interface ReportStatusInput {
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
    case "revenue":
    case "cogs":
    case "opex":
    case "inventory":
      return bucket;
    case null:
      throw APIError.failedPrecondition("report mapping line is missing ledger bucket");
    default:
      throw APIError.failedPrecondition(`report mapping line has invalid ledger bucket: ${bucket}`);
  }
}

/**
 * Guard runtime cho derivedKind đọc lại từ DB — cùng pattern với
 * `requireReportMappingBucket` ở trên: không tin thẳng giá trị `string |
 * null` bằng cast, vì giá trị lạ đọc từ DB sẽ lặng lẽ rơi vào nhánh
 * `net_profit_after_tax` trong `computeDerivedLine` và ra số sai không báo
 * lỗi — nghiêm trọng vì đây là report tài chính lõi.
 */
export function requireDerivedLineKind(value: string | null): DerivedLineKind {
  switch (value) {
    case "gross_profit":
    case "corporate_income_tax":
    case "net_profit_after_tax":
      return value;
    case null:
      throw APIError.failedPrecondition("report mapping line is missing derived kind");
    default:
      throw APIError.failedPrecondition(`report mapping line has invalid derived kind: ${value}`);
  }
}

/**
 * VERIFIED chỉ phụ thuộc việc founder đã xác nhận mapping hay chưa.
 *
 * Trước đây hàm này còn đối chiếu "bucket bắt buộc" (suy ra từ chính các dòng
 * mapping do code seed) với "bucket đã có giao dịch", rồi bắn
 * `missing_mapping_for_bucket:*`. Cách đó đánh đồng hai chuyện khác hẳn nhau:
 * "cấu hình mapping còn thiếu" (vấn đề thật) và "doanh nghiệp này hợp lệ khi
 * không có giao dịch nào ở bucket đó" (trạng thái bình thường). Hệ quả: mọi
 * doanh nghiệp thuần dịch vụ — phần lớn doanh nghiệp siêu nhỏ VN — không bao
 * giờ có giao dịch `inventory`/`cogs`, nên B01/B02 vĩnh viễn INCOMPLETE dù dữ
 * liệu hoàn toàn đầy đủ và chính xác. Issue của dòng derived (ví dụ
 * `corporate_income_tax_rate_not_configured`) là chuyện riêng, vẫn được
 * `generateReportService` gộp vào sau khi gọi hàm này.
 */
export function computeReportStatus(input: ReportStatusInput): ReportStatusResult {
  const issues: string[] = [];

  if (!input.mappingConfirmed) {
    issues.push("mapping_not_confirmed_by_founder");
  }

  return {
    status: issues.length === 0 ? "VERIFIED" : "INCOMPLETE",
    issues,
  };
}

export interface DerivedLineResult {
  amountMinor: bigint;
  issue?: string;
}

/**
 * 3 công thức derived cố định cho B01/B02 — không xây formula-engine tổng
 * quát (YAGNI). Thuế TNDN không bao giờ âm (lỗ -> thuế = 0). Khi tax rate
 * chưa cấu hình, trả issue rõ ràng thay vì giả định thuế suất bất kỳ.
 */
export function computeDerivedLine(
  kind: DerivedLineKind,
  bucketTotals: Map<LedgerBucket, bigint>,
  taxRateBps: number | null
): DerivedLineResult {
  const revenue = bucketTotals.get("revenue") ?? 0n;
  const cogs = bucketTotals.get("cogs") ?? 0n;
  const opex = bucketTotals.get("opex") ?? 0n;
  const grossProfit = revenue - cogs;

  if (kind === "gross_profit") {
    return { amountMinor: grossProfit };
  }

  const preTax = grossProfit - opex;
  const base = preTax > 0n ? preTax : 0n;

  if (kind === "corporate_income_tax") {
    if (taxRateBps == null) {
      return { amountMinor: 0n, issue: "corporate_income_tax_rate_not_configured" };
    }
    return { amountMinor: (base * BigInt(taxRateBps)) / 10000n };
  }

  // net_profit_after_tax
  if (taxRateBps == null) {
    return { amountMinor: preTax, issue: "corporate_income_tax_rate_not_configured" };
  }
  const tax = (base * BigInt(taxRateBps)) / 10000n;
  return { amountMinor: preTax - tax };
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

  // Kiểm tra kỳ LUÔN chạy, không chỉ khi caller gửi expectedPeriodVersion.
  // Trước đây một cặp (periodId, legalEntityId) lệch nhau lặng lẽ trả về 0
  // book entry -> báo cáo toàn số 0 trông y hệt báo cáo thật. Không phải rò
  // rỉ cross-tenant (workspaceId vẫn được lọc đúng ở downstream) nhưng là dữ
  // liệu vô nghĩa gây hiểu nhầm — chặn thẳng ở đây.
  const [period] = await db
    .select({
      id: accountingPeriods.id,
      legalEntityId: accountingPeriods.legalEntityId,
      version: accountingPeriods.version,
    })
    .from(accountingPeriods)
    .where(
      and(
        eq(accountingPeriods.id, BigInt(input.periodId)),
        eq(accountingPeriods.workspaceId, BigInt(ctx.workspaceId))
      )
    )
    .limit(1);
  if (!period) throw APIError.notFound(`accounting period ${input.periodId} not found`);
  if (period.legalEntityId !== null && String(period.legalEntityId) !== input.legalEntityId) {
    throw APIError.invalidArgument(
      `period ${input.periodId} belongs to a different legal entity than ${input.legalEntityId}`
    );
  }

  if (input.expectedPeriodVersion !== undefined && period.version !== input.expectedPeriodVersion) {
    throw APIError.aborted(
      `VERSION_CONFLICT: expected period version ${input.expectedPeriodVersion} but current is ${period.version}`
    );
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

  const policy = await getAccountingPolicyService(ctx, input.legalEntityId);
  const taxRateBps = policy?.corporateIncomeTaxRateBps ?? null;

  const derivedIssues = new Set<string>();
  const lines: ReportLineView[] = mappingLines.map((row) => {
    if (row.derivedKind) {
      const result = computeDerivedLine(requireDerivedLineKind(row.derivedKind), bucketTotals, taxRateBps);
      if (result.issue) derivedIssues.add(result.issue);
      return {
        lineCode: row.lineCode,
        officialCode: row.officialCode,
        name: row.name,
        sourceRef: row.sourceRef,
        amountMinor: String(result.amountMinor * BigInt(row.sign)),
      };
    }
    const bucket = requireReportMappingBucket(row.bucket);
    return {
      lineCode: row.lineCode,
      officialCode: row.officialCode,
      name: row.name,
      sourceRef: row.sourceRef,
      amountMinor: String((bucketTotals.get(bucket) ?? 0n) * BigInt(row.sign)),
    };
  });

  const { status, issues } = computeReportStatus({ mappingConfirmed: Boolean(confirmation) });
  for (const issue of derivedIssues) issues.push(issue);
  const finalStatus = issues.length === 0 ? status : "INCOMPLETE";

  // `taxRateBps` PHẢI nằm trong watermark: các dòng derived (THUE_TNDN,
  // LOI_NHUAN_GOP, LOI_NHUAN_SAU_THUE, LOI_NHUAN_GIU_LAI) phụ thuộc thuế
  // suất, mà thuế suất đọc từ bảng `accounting_policies` — hoàn toàn khác
  // nguồn với book entries. Thiếu nó, founder sửa thuế suất (không đụng book
  // entry nào) sẽ cho ra watermark + status + issues y hệt, nên dedup trả về
  // snapshot CŨ với số thuế cũ. Không chỉ sai hiển thị:
  // `syncComputedCorporateIncomeTaxService` đọc dòng THUE_TNDN từ chính kết
  // quả này rồi ghi vào `tax_obligation_instances`.
  const inputWatermark = computeCanonicalSha256({
    mappingVersion: mapping.mappingVersion,
    taxRateBps,
    entries: entries
      .map((e) => ({ id: e.id, category: e.category, amountMinor: e.amountMinor, version: e.version }))
      .sort((a, b) => a.id.localeCompare(b.id)),
  });

  // Không ghi snapshot mới khi không có gì thay đổi. Tab TT58 ở Flutter gọi
  // endpoint này mỗi lần mở màn hình (nhiều lần cho cùng một reportCode), nên
  // insert vô điều kiện làm bảng audit phình ra chỉ vì người dùng xem báo cáo.
  //
  // `inputWatermark` KHÔNG bao gồm trạng thái xác nhận mapping, nên chỉ khớp
  // watermark là chưa đủ: nếu founder xác nhận mapping SAU khi đã có snapshot
  // INCOMPLETE cùng watermark, trả lại dòng cũ sẽ che mất việc report đã lên
  // VERIFIED. Vì vậy chỉ bỏ qua insert khi cả status và issues của dòng cũ
  // cũng khớp đúng những gì vừa tính ở đây.
  const [existing] = await db
    .select()
    .from(accountingReportSnapshots)
    .where(
      and(
        eq(accountingReportSnapshots.workspaceId, BigInt(ctx.workspaceId)),
        eq(accountingReportSnapshots.legalEntityId, BigInt(input.legalEntityId)),
        eq(accountingReportSnapshots.periodId, BigInt(input.periodId)),
        eq(accountingReportSnapshots.reportCode, input.reportCode),
        eq(accountingReportSnapshots.mappingVersion, mapping.mappingVersion)
      )
    )
    .orderBy(desc(accountingReportSnapshots.generatedAt), desc(accountingReportSnapshots.id))
    .limit(1);

  if (
    existing &&
    existing.inputWatermark === inputWatermark &&
    existing.status === finalStatus &&
    JSON.stringify(existing.issues) === JSON.stringify(issues)
  ) {
    return {
      id: String(existing.id),
      legalEntityId: String(existing.legalEntityId),
      periodId: String(existing.periodId),
      reportCode: existing.reportCode,
      mappingVersion: existing.mappingVersion,
      inputWatermark: existing.inputWatermark,
      lines: existing.lines,
      status: existing.status,
      issues: existing.issues,
      generatedAt: existing.generatedAt.toISOString(),
    };
  }

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
      status: finalStatus,
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
