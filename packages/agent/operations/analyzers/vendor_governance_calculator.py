from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_WEIGHTS: dict[str, float] = {
    "delivery": 0.30,
    "quality": 0.30,
    "security": 0.25,
    "support": 0.15,
}


@dataclass(frozen=True)
class VendorScorecard:
    vendor_id: str
    vendor_name: str
    delivery_score: float
    quality_score: float
    security_score: float
    support_score: float
    weighted_score: float
    grade: str  # "A" (>=90) | "B" (80-89) | "C" (70-79) | "D" (<70)
    weights: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SLABreachRecord:
    incident_id: str
    vendor_id: str
    severity: str  # "P1" | "P2" | "P3"
    target_mttr_minutes: float
    actual_mttr_minutes: float
    breach_minutes: float
    credit_percentage: float  # e.g. 0.05 for 5%
    credit_amount: float  # dollar amount
    remedy_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VendorRiskClassification:
    vendor_id: str
    vendor_name: str
    risk_tier: str  # "TIER_1_CRITICAL" | "TIER_2_HIGH" | "TIER_3_MEDIUM_LOW"
    break_glass_required: bool
    review_cadence_weeks: int
    compliance_standard: str  # "NIST SP 800-161 / ISO 27036"
    risk_factors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "risk_tier": self.risk_tier,
            "break_glass_required": self.break_glass_required,
            "review_cadence_weeks": self.review_cadence_weeks,
            "compliance_standard": self.compliance_standard,
            "risk_factors": list(self.risk_factors),
        }


class VendorGovernanceCalculator:
    """Bộ công cụ định lượng quản trị nhà cung cấp (Vendor Scorecard, SLA Breach, NIST Risk).
    100% Python stdlib tất định.
    """

    @classmethod
    def calculate_score(
        cls,
        vendor_id: str,
        vendor_name: str,
        scores: dict[str, float],
        weights: dict[str, float] | None = None,
    ) -> VendorScorecard:
        w = weights or DEFAULT_WEIGHTS
        total_w = sum(w.values())
        if total_w <= 0:
            raise ValueError("Tổng trọng số phải lớn hơn 0")

        del_s = float(scores.get("delivery", 0.0))
        qual_s = float(scores.get("quality", 0.0))
        sec_s = float(scores.get("security", 0.0))
        sup_s = float(scores.get("support", 0.0))

        weighted_sum = (
            del_s * (w.get("delivery", 0.3) / total_w)
            + qual_s * (w.get("quality", 0.3) / total_w)
            + sec_s * (w.get("security", 0.25) / total_w)
            + sup_s * (w.get("support", 0.15) / total_w)
        )
        weighted_score = round(weighted_sum, 2)

        if weighted_score >= 90.0:
            grade = "A"
        elif weighted_score >= 80.0:
            grade = "B"
        elif weighted_score >= 70.0:
            grade = "C"
        else:
            grade = "D"

        return VendorScorecard(
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            delivery_score=del_s,
            quality_score=qual_s,
            security_score=sec_s,
            support_score=sup_s,
            weighted_score=weighted_score,
            grade=grade,
            weights={k: round(v / total_w, 2) for k, v in w.items()},
        )

    @classmethod
    def track_sla_breach(
        cls,
        incident_id: str,
        vendor_id: str,
        severity: str,
        target_mttr_minutes: float,
        actual_mttr_minutes: float,
        monthly_spend: float,
    ) -> SLABreachRecord:
        breach_minutes = max(0.0, actual_mttr_minutes - target_mttr_minutes)
        credit_pct = 0.0

        if breach_minutes > 0:
            if severity.upper() == "P1":
                # P1: 5% cho 30m trễ đầu tiên, 10% nếu > 60m, tối đa 25%
                if breach_minutes > 120:
                    credit_pct = 0.25
                elif breach_minutes > 60:
                    credit_pct = 0.15
                elif breach_minutes > 30:
                    credit_pct = 0.10
                else:
                    credit_pct = 0.05
            elif severity.upper() == "P2":
                credit_pct = 0.05 if breach_minutes > 60 else 0.02
            else:
                credit_pct = 0.02 if breach_minutes > 120 else 0.01

        credit_amount = round(monthly_spend * credit_pct, 2)
        remedy = (
            f"Yêu cầu bồi hoàn dịch vụ {credit_pct * 100:.1f}% ({credit_amount:,.2f} USD) "
            f"do vi phạm MTTR {breach_minutes:.1f} phút."
            if credit_pct > 0
            else "Trong ngưỡng cam kết SLA; không phát sinh chế tài."
        )

        return SLABreachRecord(
            incident_id=incident_id,
            vendor_id=vendor_id,
            severity=severity.upper(),
            target_mttr_minutes=target_mttr_minutes,
            actual_mttr_minutes=actual_mttr_minutes,
            breach_minutes=round(breach_minutes, 1),
            credit_percentage=credit_pct,
            credit_amount=credit_amount,
            remedy_action=remedy,
        )

    @classmethod
    def classify_risk(
        cls,
        vendor_id: str,
        vendor_name: str,
        handles_pii_or_financial_data: bool,
        is_direct_production_dependency: bool,
        annual_spend: float,
    ) -> VendorRiskClassification:
        factors: list[str] = []

        if handles_pii_or_financial_data:
            factors.append("Xử lý dữ liệu cá nhân (PII) hoặc dữ liệu tài chính nhạy cảm")
        if is_direct_production_dependency:
            factors.append(
                "Phụ thuộc trực tiếp vào luồng production chính (Single Point of Failure)"
            )
        if annual_spend >= 50000.0:
            factors.append(f"Chi tiêu hàng năm lớn ({annual_spend:,.0f} USD)")

        # Phân tầng rủi ro
        if handles_pii_or_financial_data and is_direct_production_dependency:
            tier = "TIER_1_CRITICAL"
            break_glass = True
            cadence_weeks = 4  # Rà soát 4 tuần/lần
        elif (
            handles_pii_or_financial_data
            or is_direct_production_dependency
            or annual_spend >= 50000.0
        ):
            tier = "TIER_2_HIGH"
            break_glass = False
            cadence_weeks = 12  # Rà soát theo chu kỳ 12WY
        else:
            tier = "TIER_3_MEDIUM_LOW"
            break_glass = False
            cadence_weeks = 24  # Rà soát 2 chu kỳ 12WY/lần

        return VendorRiskClassification(
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            risk_tier=tier,
            break_glass_required=break_glass,
            review_cadence_weeks=cadence_weeks,
            compliance_standard="NIST SP 800-161 / ISO 27036",
            risk_factors=tuple(factors),
        )
