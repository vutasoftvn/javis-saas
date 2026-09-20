#!/usr/bin/env python3
"""Market Sizing Triangulator - Compute TAM / SAM / SOM by BOTH top-down and bottoms-up methods.

100% Python Standard Library. Deterministic. No LLM dependencies.
Never returns a single unsourced number: computes both methods side-by-side,
reports triangulation divergence, and outputs mandatory method & assumptions block.

Top-down:   TAM = total_market_value
            SAM = TAM * serviceable_fraction
            SOM = SAM * reachable_share

Bottoms-up: TAM = total_potential_customers * annual_price
            SAM = TAM * serviceable_fraction
            SOM = SAM * realistic_adoption (capacity-constrained)

Triangulation Divergence:
            Delta = abs(TAM_top_down - TAM_bottoms_up) / TAM_top_down
            Flags TRIANGULATION FAILED if Delta exceeds industry profile tolerance.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any

PROFILES: dict[str, dict[str, Any]] = {
    "b2b-saas": {"tolerance": 0.30, "description": "B2B SaaS / Enterprise Cloud"},
    "consumer": {"tolerance": 0.40, "description": "Consumer Internet / Apps"},
    "enterprise": {"tolerance": 0.25, "description": "High-ticket Enterprise Software"},
    "marketplace": {"tolerance": 0.40, "description": "Two-sided Marketplaces"},
    "hardware": {"tolerance": 0.30, "description": "Connected Devices / Tech Hardware"},
    "services": {"tolerance": 0.35, "description": "Tech-enabled Professional Services"},
}

DEFAULT_ASSUMPTIONS = [
    "NEVER quote a single TAM number without stating the method and underlying assumptions.",
    "Top-down TAM = total market value based on credible industry reports/statistics.",
    "Bottoms-up TAM = total potential customers x annual price (ACV/ARPU).",
    "SAM = TAM x serviceable fraction (geography, tech stack, and customer segment reachable).",
    "SOM = SAM x realistic, capacity-constrained market share winnable in the planning horizon (12-24 months).",
]


@dataclass
class TopDownResult:
    method: str = "top-down"
    total_market_value: float = 0.0
    serviceable_fraction: float = 0.0
    reachable_share: float = 0.0
    tam: float = 0.0
    sam: float = 0.0
    som: float = 0.0


@dataclass
class BottomsUpResult:
    method: str = "bottoms-up"
    total_potential_customers: float = 0.0
    annual_price: float = 0.0
    serviceable_fraction: float = 0.0
    realistic_adoption: float = 0.0
    tam: float = 0.0
    sam: float = 0.0
    som: float = 0.0
    implied_customers_at_som: int | None = None


@dataclass
class TriangulationReport:
    market_name: str
    profile: str
    tolerance: float
    top_down: TopDownResult | None = None
    bottoms_up: BottomsUpResult | None = None
    tam_divergence: float | None = None
    triangulation_passed: bool = True
    flags: list[str] = field(default_factory=list)
    method_and_assumptions: list[str] = field(default_factory=lambda: list(DEFAULT_ASSUMPTIONS))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MarketSizingTriangulator:
    """Computes and triangulates TAM / SAM / SOM across dual methodologies."""

    def __init__(self, profile: str = "b2b-saas"):
        if profile not in PROFILES:
            raise ValueError(f"Unknown profile '{profile}'. Choose from {list(PROFILES.keys())}.")
        self.profile = profile
        self.tolerance = PROFILES[profile]["tolerance"]

    def calculate_top_down(
        self,
        total_market_value: float,
        serviceable_fraction: float,
        reachable_share: float,
    ) -> TopDownResult:
        if total_market_value < 0 or serviceable_fraction < 0 or reachable_share < 0:
            raise ValueError("All market sizing parameters must be non-negative.")
        if serviceable_fraction > 1.0 or reachable_share > 1.0:
            raise ValueError("Fractions and shares must be <= 1.0.")

        tam = round(total_market_value, 2)
        sam = round(tam * serviceable_fraction, 2)
        som = round(sam * reachable_share, 2)
        return TopDownResult(
            method="top-down",
            total_market_value=total_market_value,
            serviceable_fraction=serviceable_fraction,
            reachable_share=reachable_share,
            tam=tam,
            sam=sam,
            som=som,
        )

    def calculate_bottoms_up(
        self,
        total_potential_customers: float,
        annual_price: float,
        serviceable_fraction: float,
        realistic_adoption: float,
    ) -> BottomsUpResult:
        if (
            total_potential_customers < 0
            or annual_price < 0
            or serviceable_fraction < 0
            or realistic_adoption < 0
        ):
            raise ValueError("All bottoms-up parameters must be non-negative.")
        if serviceable_fraction > 1.0 or realistic_adoption > 1.0:
            raise ValueError("Fractions and adoption rates must be <= 1.0.")

        tam = round(total_potential_customers * annual_price, 2)
        sam = round(tam * serviceable_fraction, 2)
        som = round(sam * realistic_adoption, 2)
        implied_customers = math.floor(som / annual_price) if annual_price > 0 else 0

        return BottomsUpResult(
            method="bottoms-up",
            total_potential_customers=total_potential_customers,
            annual_price=annual_price,
            serviceable_fraction=serviceable_fraction,
            realistic_adoption=realistic_adoption,
            tam=tam,
            sam=sam,
            som=som,
            implied_customers_at_som=implied_customers,
        )

    def triangulate(
        self,
        market_name: str,
        top_down_input: dict[str, float] | None = None,
        bottoms_up_input: dict[str, float] | None = None,
    ) -> TriangulationReport:
        td_result: TopDownResult | None = None
        bu_result: BottomsUpResult | None = None

        if top_down_input:
            td_result = self.calculate_top_down(
                total_market_value=float(top_down_input.get("total_market_value", 0.0)),
                serviceable_fraction=float(top_down_input.get("serviceable_fraction", 0.0)),
                reachable_share=float(top_down_input.get("reachable_share", 0.0)),
            )

        if bottoms_up_input:
            bu_result = self.calculate_bottoms_up(
                total_potential_customers=float(
                    bottoms_up_input.get("total_potential_customers", 0.0)
                ),
                annual_price=float(bottoms_up_input.get("annual_price", 0.0)),
                serviceable_fraction=float(bottoms_up_input.get("serviceable_fraction", 0.0)),
                realistic_adoption=float(bottoms_up_input.get("realistic_adoption", 0.0)),
            )

        flags: list[str] = []
        divergence: float | None = None
        passed: bool = True

        if td_result and bu_result:
            if td_result.tam > 0:
                divergence = round(abs(td_result.tam - bu_result.tam) / td_result.tam, 4)
                if divergence > self.tolerance:
                    passed = False
                    flags.append(
                        f"TRIANGULATION FAILED: Top-down TAM (${td_result.tam:,.0f}) and "
                        f"Bottoms-up TAM (${bu_result.tam:,.0f}) diverge by {divergence:.1%}, "
                        f"exceeding allowable tolerance {self.tolerance:.1%} for {self.profile}. "
                        f"Reconcile customer counts or pricing assumptions before quoting."
                    )
                else:
                    flags.append(
                        f"Triangulation OK: Dual TAM estimates align within {divergence:.1%} "
                        f"(threshold: {self.tolerance:.1%})."
                    )
            else:
                flags.append("Warning: Top-down TAM is zero; cannot compute divergence.")
        elif td_result and not bu_result:
            flags.append("Caution: Only Top-down TAM provided. Bottoms-up validation missing.")
        elif bu_result and not td_result:
            flags.append(
                "Caution: Only Bottoms-up TAM provided. Top-down industry validation missing."
            )
        else:
            flags.append("Error: Neither Top-down nor Bottoms-up data provided.")
            passed = False

        return TriangulationReport(
            market_name=market_name,
            profile=self.profile,
            tolerance=self.tolerance,
            top_down=td_result,
            bottoms_up=bu_result,
            tam_divergence=divergence,
            triangulation_passed=passed,
            flags=flags,
            method_and_assumptions=list(DEFAULT_ASSUMPTIONS),
        )


def _fmt(n: float | None) -> str:
    if n is None:
        return "N/A"
    return f"${n:,.0f}" if isinstance(n, (int, float)) else str(n)


def render_human_report(report: TriangulationReport) -> str:
    lines = [
        f"=== Báo Cáo Định Quy Mô Thị Trường: {report.market_name} ===",
        f"Profile: {report.profile} (Dung sai cho phép: {report.tolerance:.0%})",
        "",
    ]
    if report.top_down:
        td = report.top_down
        lines.append(
            f"  [Top-Down]   TAM: {_fmt(td.tam)} | SAM: {_fmt(td.sam)} | SOM: {_fmt(td.som)}"
        )
    if report.bottoms_up:
        bu = report.bottoms_up
        lines.append(
            f"  [Bottoms-Up] TAM: {_fmt(bu.tam)} | SAM: {_fmt(bu.sam)} | SOM: {_fmt(bu.som)}"
        )
        if bu.implied_customers_at_som is not None:
            lines.append(
                f"               -> Số khách hàng ngụ ý tại SOM: {bu.implied_customers_at_som:,}"
            )

    if report.tam_divergence is not None:
        lines.append(f"  Độ lệch tam giác (TAM Divergence): {report.tam_divergence:.1%}")

    lines.append("")
    lines.append("Kết Luận & Cảnh Báo:")
    for f in report.flags:
        prefix = "[!]" if "FAILED" in f or "Caution" in f else "[OK]"
        lines.append(f"  {prefix} {f}")

    lines.append("")
    lines.append("Khối Giả Định & Phương Pháp Luận:")
    for a in report.method_and_assumptions:
        lines.append(f"  - {a}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Triangulate TAM/SAM/SOM market sizing.")
    parser.add_argument("--input", help="Path to JSON input file")
    parser.add_argument("--profile", default="b2b-saas", choices=list(PROFILES.keys()))
    parser.add_argument("--output", choices=["human", "json"], default="human")
    args = parser.parse_args()

    data: dict[str, Any]
    if not args.input:
        sample_data: dict[str, Any] = {
            "market_name": "Mid-market B2B HR Analytics (US)",
            "top_down": {
                "total_market_value": 4500000000,
                "serviceable_fraction": 0.35,
                "reachable_share": 0.04,
            },
            "bottoms_up": {
                "total_potential_customers": 65000,
                "annual_price": 20000,
                "serviceable_fraction": 0.35,
                "realistic_adoption": 0.03,
            },
        }
        data = sample_data
    else:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)

    triangulator = MarketSizingTriangulator(profile=args.profile)
    report = triangulator.triangulate(
        market_name=data.get("market_name", "UNSPECIFIED"),
        top_down_input=data.get("top_down"),
        bottoms_up_input=data.get("bottoms_up"),
    )

    if args.output == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_human_report(report))

    return 0 if report.triangulation_passed else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
