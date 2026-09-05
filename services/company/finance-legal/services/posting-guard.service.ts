import { APIError } from "encore.dev/api";
import { and, eq, gte, lte } from "drizzle-orm";
import { schema } from "../models/db";

const { accountingPeriods } = schema;

export interface AssertOpenPostingPeriodParams {
  workspaceId: bigint | string;
  legalEntityId?: bigint | string | null;
  postingDate: string | Date;
}

/**
 * Chuẩn hóa ngày thành định dạng YYYY-MM-DD
 */
export function normalizeDate(date: string | Date): string {
  if (typeof date === "string") {
    if (date.includes("T")) {
      return date.split("T")[0];
    }
    return date;
  }
  return date.toISOString().split("T")[0];
}

/**
 * Kiểm tra và serialize khóa kỳ ghi sổ cho giao dịch hoặc chứng từ kế toán.
 * 
 * - Ngăn chặn posting vào kỳ đã đóng (PERIOD_CLOSED).
 * - Serialize tranh chấp giữa posting và close kỳ bằng row lock 'FOR SHARE'.
 *   Khi close kỳ lock 'FOR UPDATE', posting sẽ phải chờ. Khi lock nhả, posting
 *   phát hiện kỳ đã đóng và rollback, không để chứng từ lọt sau khi đóng kỳ.
 */
export async function assertOpenPostingPeriod(
  tx: any,
  params: AssertOpenPostingPeriodParams
): Promise<void> {
  const wsId = BigInt(params.workspaceId);
  const dateStr = normalizeDate(params.postingDate);
  const legalEntityId = params.legalEntityId ? BigInt(params.legalEntityId) : null;

  // 1. Kiểm tra xem có kỳ CLOSED nào bao phủ ngày này không
  const closedConditions = [
    eq(accountingPeriods.workspaceId, wsId),
    eq(accountingPeriods.status, "CLOSED"),
    lte(accountingPeriods.startDate, dateStr),
    gte(accountingPeriods.endDate, dateStr),
  ];
  if (legalEntityId) {
    closedConditions.push(eq(accountingPeriods.legalEntityId, legalEntityId));
  }

  const [closedPeriod] = await tx
    .select({
      id: accountingPeriods.id,
      status: accountingPeriods.status,
    })
    .from(accountingPeriods)
    .where(and(...closedConditions))
    .limit(1);

  if (closedPeriod) {
    throw APIError.failedPrecondition(
      `PERIOD_CLOSED: Không thể ghi sổ vào kỳ kế toán đã đóng (ngày ${dateStr})`
    );
  }

  // 2. Tìm kỳ OPEN bao phủ ngày này và lock FOR SHARE để serialize với close period
  const openConditions = [
    eq(accountingPeriods.workspaceId, wsId),
    eq(accountingPeriods.status, "OPEN"),
    lte(accountingPeriods.startDate, dateStr),
    gte(accountingPeriods.endDate, dateStr),
  ];
  if (legalEntityId) {
    openConditions.push(eq(accountingPeriods.legalEntityId, legalEntityId));
  }

  const openPeriods = await tx
    .select({
      id: accountingPeriods.id,
      status: accountingPeriods.status,
    })
    .from(accountingPeriods)
    .where(and(...openConditions))
    .for("share");

  if (openPeriods.length > 0) {
    const period = openPeriods[0];
    if (period.status !== "OPEN") {
      throw APIError.failedPrecondition(
        `PERIOD_CLOSED: Kỳ kế toán chứa ngày ghi sổ ${dateStr} đã bị đóng`
      );
    }
    return;
  }

  // 3. Nếu không có kỳ nào bao phủ:
  // Kiểm tra xem workspace đã có kỳ kế toán nào được thiết lập chưa.
  const anyConditions = [eq(accountingPeriods.workspaceId, wsId)];
  if (legalEntityId) {
    anyConditions.push(eq(accountingPeriods.legalEntityId, legalEntityId));
  }

  const [anyPeriod] = await tx
    .select({ id: accountingPeriods.id })
    .from(accountingPeriods)
    .where(and(...anyConditions))
    .limit(1);

  if (anyPeriod) {
    throw APIError.failedPrecondition(
      `NO_OPEN_PERIOD: Không tìm thấy kỳ kế toán mở cho ngày ghi sổ ${dateStr}`
    );
  }

  // Nếu workspace chưa hề khởi tạo kỳ kế toán nào, cho phép ghi (legacy fallback)
}
