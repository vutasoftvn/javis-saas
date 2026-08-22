export type EvidenceSourceType =
  | "financial_transaction" // Highest fidelity: real money paid
  | "customer_interview"   // High fidelity: deep qualitative feedback
  | "prototype_test"       // Medium-high fidelity: behavioral test
  | "experiment_metric"    // Medium-high: analytics / behavioral metrics
  | "survey"               // Medium: stated preference
  | "3rd_party_data"       // Low: secondary research
  | "observation"          // Medium-low: anecdotal observation
  | string;

export interface EvidenceScoreInput {
  sourceType: EvidenceSourceType;
  rawStrength?: number; // 0.0 - 1.0 if provided
  rawConfidence?: number; // 0.0 - 1.0 if provided
  sampleSize?: number;
  supportsOrRefutes?: "supports" | "refutes" | "neutral" | string;
}

export interface EvidenceScoreResult {
  sourceType: string;
  strength: number; // 0.0 to 1.0
  confidence: number; // 0.0 to 1.0
  compositeScore: number; // strength * confidence
  sourceWeightBaseline: number;
}

/**
 * Trọng số cơ sở theo loại nguồn dữ liệu (Source Type Baseline Weights).
 * TODO [Business Ops / Methodology]: Tinh chỉnh các trọng số này dựa trên thực nghiệm vận hành thực tế.
 */
export const SOURCE_TYPE_BASE_WEIGHTS: Record<string, { baseStrength: number; defaultConfidence: number }> = {
  // Thực tế giao dịch tiền mặt/hợp đồng ký thật: độ tin cậy tối đa
  financial_transaction: { baseStrength: 0.95, defaultConfidence: 0.90 },
  payment: { baseStrength: 0.95, defaultConfidence: 0.90 },

  // Phỏng vấn khách hàng trực tiếp định tính sâu
  customer_interview: { baseStrength: 0.85, defaultConfidence: 0.80 },
  interview: { baseStrength: 0.85, defaultConfidence: 0.80 },

  // Thử nghiệm tương tác sản phẩm/prototype hành vi thực tế
  prototype_test: { baseStrength: 0.80, defaultConfidence: 0.75 },
  experiment_metric: { baseStrength: 0.75, defaultConfidence: 0.75 },

  // Khảo sát định lượng (ý định khai báo)
  survey: { baseStrength: 0.60, defaultConfidence: 0.65 },

  // Quan sát tại chỗ
  observation: { baseStrength: 0.50, defaultConfidence: 0.50 },

  // Báo cáo/dữ liệu từ bên thứ 3 (secondary research)
  "3rd_party_data": { baseStrength: 0.40, defaultConfidence: 0.40 },
  market_report: { baseStrength: 0.40, defaultConfidence: 0.40 },
};

const DEFAULT_FALLBACK_WEIGHT = { baseStrength: 0.50, defaultConfidence: 0.50 };

/**
 * Chuẩn hoá điểm Strength và Confidence của Evidence về thang [0.0, 1.0] hoàn toàn tất định.
 */
export function scoreEvidence(input: EvidenceScoreInput): EvidenceScoreResult {
  const normType = input.sourceType.toLowerCase().trim();
  const baseConfig = SOURCE_TYPE_BASE_WEIGHTS[normType] || DEFAULT_FALLBACK_WEIGHT;

  // Tính strength
  let strength = input.rawStrength !== undefined
    ? Math.max(0.0, Math.min(1.0, Number(input.rawStrength)))
    : baseConfig.baseStrength;

  // Tính confidence kết hợp sampleSize nếu có
  let confidence = input.rawConfidence !== undefined
    ? Math.max(0.0, Math.min(1.0, Number(input.rawConfidence)))
    : baseConfig.defaultConfidence;

  if (input.sampleSize !== undefined && input.sampleSize > 0) {
    // Scaling confidence theo kích thước mẫu: mẫu >= 20 đạt tối đa boost +0.15
    const sampleBoost = Math.min(0.15, (input.sampleSize / 20) * 0.15);
    confidence = Math.min(1.0, confidence + sampleBoost);
  }

  // Làm tròn 4 chữ số thập phân tất định
  strength = Math.round(strength * 10000) / 10000;
  confidence = Math.round(confidence * 10000) / 10000;
  const compositeScore = Math.round(strength * confidence * 10000) / 10000;

  return {
    sourceType: input.sourceType,
    strength,
    confidence,
    compositeScore,
    sourceWeightBaseline: baseConfig.baseStrength,
  };
}
