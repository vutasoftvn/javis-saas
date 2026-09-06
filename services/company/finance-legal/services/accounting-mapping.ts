import { computeCanonicalSha256 } from "./compliance/canonical-hasher";

export type BookEntryCategory =
  | "capital"
  | "loan"
  | "internal_transfer"
  | "revenue"
  | "cost"
  | "advance"
  | "payable"
  | "receivable";

export type LedgerBucket =
  | "cash"
  | "receivable"
  | "payable"
  | "loan"
  | "advance"
  | "capital"
  | "profit";

export interface BucketEffect {
  bucket: LedgerBucket;
  amountMinor: bigint;
}

/**
 * Phân loại một book entry thành các bucket bị ảnh hưởng. capital/loan là
 * tiền mặt nhận ngay; revenue/cost là dồn tích (chưa chạm cash cho tới khi
 * có dòng receivable/payable settlement riêng); receivable/payable ở đây
 * đại diện cho SỰ KIỆN THANH TOÁN (thu/chi tiền mặt đối trừ công nợ đã dồn
 * tích trước đó), không phải công nợ mới phát sinh không có nguồn gốc.
 */
export function classifyBookEntry(
  category: BookEntryCategory,
  amountMinor: bigint
): BucketEffect[] {
  switch (category) {
    case "capital":
      return [
        { bucket: "cash", amountMinor },
        { bucket: "capital", amountMinor },
      ];
    case "loan":
      return [
        { bucket: "cash", amountMinor },
        { bucket: "loan", amountMinor },
      ];
    case "revenue":
      return [
        { bucket: "receivable", amountMinor },
        { bucket: "profit", amountMinor },
      ];
    case "cost":
      return [
        { bucket: "payable", amountMinor },
        { bucket: "profit", amountMinor: -amountMinor },
      ];
    case "receivable":
      return [
        { bucket: "receivable", amountMinor: -amountMinor },
        { bucket: "cash", amountMinor },
      ];
    case "payable":
      return [
        { bucket: "payable", amountMinor: -amountMinor },
        { bucket: "cash", amountMinor: -amountMinor },
      ];
    case "internal_transfer":
      return [{ bucket: "cash", amountMinor }];
    case "advance":
      return [
        { bucket: "cash", amountMinor: -amountMinor },
        { bucket: "advance", amountMinor },
      ];
  }
}

export type ReportRuleType = "opening" | "movement" | "closing";

export interface ReportMappingLine {
  reportCode: string;
  lineCode: string;
  officialCode: string;
  name: string;
  sourceRef: string;
  ruleType: ReportRuleType;
  bucket: LedgerBucket;
  sign: 1 | -1;
  rounding: "VND_INTEGER";
}

export interface RegimeMapping {
  regimeCode: string;
  mappingVersion: string;
  lines: ReportMappingLine[];
}

const UNVERIFIED_SOURCE =
  "CHƯA XÁC MINH — chờ founder xác nhận đối chiếu văn bản Thông tư 58/2024 " +
  "(https://www.mof.gov.vn/tin-tuc-tai-chinh/tin-chinh-sach-tai-chinh/quy-dinh-moi-ve-che-do-ke-toan-cho-doanh-nghiep-sieu-nho) " +
  "trước khi coi report dùng mapping này là VERIFIED.";

/**
 * Nội dung mapping TT58 rút gọn — chỉ đủ 5 dòng cần cho bộ fixture chính
 * thức trong spec (cash/receivable/loan/capital+profit/assets). Founder
 * PHẢI xác nhận qua POST /finance/accounting-mapping/:regimeCode/:mappingVersion/confirm
 * trước khi report dùng mapping_version này đạt status=VERIFIED — cho tới
 * lúc đó report vẫn INCOMPLETE dù mọi dòng có đủ data.
 */
export const TT58_2026_MAPPING: RegimeMapping = {
  regimeCode: "TT58_2026",
  mappingVersion: "v1",
  lines: [
    {
      reportCode: "B01",
      lineCode: "TS",
      officialCode: "TS",
      name: "Tiền và tương đương tiền",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: "cash",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B01",
      lineCode: "PHAI_THU",
      officialCode: "PHAI_THU",
      name: "Phải thu khách hàng",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: "receivable",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B01",
      lineCode: "NO_VAY",
      officialCode: "NO_VAY",
      name: "Nợ vay",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: "loan",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B01",
      lineCode: "VON_GOP",
      officialCode: "VON_GOP",
      name: "Vốn góp chủ sở hữu",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: "capital",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "LOI_NHUAN",
      officialCode: "LOI_NHUAN",
      name: "Lợi nhuận kỳ (doanh thu - chi phí đã ghi nhận)",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: "profit",
      sign: 1,
      rounding: "VND_INTEGER",
    },
  ],
};

export function computeMappingDefinitionHash(mapping: RegimeMapping): string {
  return computeCanonicalSha256({
    regimeCode: mapping.regimeCode,
    mappingVersion: mapping.mappingVersion,
    lines: mapping.lines,
  });
}
