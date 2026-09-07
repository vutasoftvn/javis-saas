import { computeCanonicalSha256 } from "./compliance/canonical-hasher";

export type BookEntryCategory =
  | "capital"
  | "loan"
  | "internal_transfer"
  | "revenue"
  | "cogs"
  | "opex"
  | "inventory_purchase"
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
  | "revenue"
  | "cogs"
  | "opex"
  | "inventory";

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
        { bucket: "revenue", amountMinor },
      ];
    case "cogs":
      return [
        { bucket: "inventory", amountMinor: -amountMinor },
        { bucket: "cogs", amountMinor },
      ];
    case "opex":
      return [
        { bucket: "payable", amountMinor },
        { bucket: "opex", amountMinor },
      ];
    case "inventory_purchase":
      return [
        { bucket: "cash", amountMinor: -amountMinor },
        { bucket: "inventory", amountMinor },
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

export type DerivedLineKind = "gross_profit" | "corporate_income_tax" | "net_profit_after_tax";

export interface ReportMappingLine {
  reportCode: string;
  lineCode: string;
  officialCode: string;
  name: string;
  sourceRef: string;
  ruleType: ReportRuleType;
  bucket: LedgerBucket | null;
  derivedKind?: DerivedLineKind;
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
 * Nội dung mapping TT58 rút gọn — 12 dòng, phiên bản `v2`:
 *
 * - B01 (cân đối kế toán), 6 dòng: TS (cash), PHAI_THU (receivable),
 *   TON_KHO (inventory), NO_VAY (loan), VON_GOP (capital) và
 *   LOI_NHUAN_GIU_LAI (derived `net_profit_after_tax`).
 * - B02 (kết quả kinh doanh), 6 dòng: DOANH_THU_THUAN (revenue),
 *   GIA_VON (cogs), LOI_NHUAN_GOP (derived `gross_profit`),
 *   CHI_PHI_HDKD (opex), THUE_TNDN (derived `corporate_income_tax`) và
 *   LOI_NHUAN_SAU_THUE (derived `net_profit_after_tax`).
 *
 * Dòng derived có `bucket: null` và lấy số từ `computeDerivedLine` thay vì
 * từ một bucket sổ cái; bucket `profit` của v1 không còn tồn tại, đã tách
 * thành revenue/cogs/opex cộng các dòng derived ở trên.
 *
 * Founder PHẢI xác nhận qua POST
 * /finance/accounting-mapping/:regimeCode/:mappingVersion/confirm trước khi
 * report dùng mapping_version này đạt status=VERIFIED — cho tới lúc đó
 * report vẫn INCOMPLETE dù mọi dòng có đủ data.
 */
export const TT58_2026_MAPPING: RegimeMapping = {
  regimeCode: "TT58_2026",
  mappingVersion: "v2",
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
      lineCode: "TON_KHO",
      officialCode: "TON_KHO",
      name: "Hàng tồn kho",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: "inventory",
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
      reportCode: "B01",
      lineCode: "LOI_NHUAN_GIU_LAI",
      officialCode: "LOI_NHUAN_GIU_LAI",
      name: "Lợi nhuận giữ lại trong kỳ",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: null,
      derivedKind: "net_profit_after_tax",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "DOANH_THU_THUAN",
      officialCode: "DOANH_THU_THUAN",
      name: "Doanh thu thuần",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: "revenue",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "GIA_VON",
      officialCode: "GIA_VON",
      name: "Giá vốn hàng bán",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: "cogs",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "LOI_NHUAN_GOP",
      officialCode: "LOI_NHUAN_GOP",
      name: "Lợi nhuận gộp",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: null,
      derivedKind: "gross_profit",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "CHI_PHI_HDKD",
      officialCode: "CHI_PHI_HDKD",
      name: "Chi phí hoạt động kinh doanh",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: "opex",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "THUE_TNDN",
      officialCode: "THUE_TNDN",
      name: "Thuế thu nhập doanh nghiệp",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: null,
      derivedKind: "corporate_income_tax",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "LOI_NHUAN_SAU_THUE",
      officialCode: "LOI_NHUAN_SAU_THUE",
      name: "Lợi nhuận sau thuế",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: null,
      derivedKind: "net_profit_after_tax",
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
