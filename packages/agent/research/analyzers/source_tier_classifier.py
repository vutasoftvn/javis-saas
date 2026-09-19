#!/usr/bin/env python3
"""Source Tier Classifier - Deterministic URL & Domain Reliability Tiering.

100% Python Standard Library. Deterministic. No LLM dependencies.
Classifies research source URLs into 3 hierarchical reliability tiers:

  - PRIMARY (Tier 1, Weight 1.0):
      Official government, SEC/filings, regulatory, court records, patent offices,
      academic peer-reviewed, official company filings & investor relations (.gov, .mil, .edu).
  - SECONDARY (Tier 2, Weight 0.7):
      Reputable financial press, major mainstream news, tier-1 tech publications,
      and established management consultancy reports (WSJ, Reuters, Bloomberg, TechCrunch, VnExpress).
  - TERTIARY (Tier 3, Weight 0.4):
      Forums, social media, user-generated content, uncurated blogs (Reddit, HN, Medium, Voz).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

PRIMARY_DOMAIN_EXACT = {
    "sec.gov",
    "data.sec.gov",
    "www.sec.gov",
    "courtlistener.com",
    "pacer.gov",
    "uspto.gov",
    "patents.google.com",
    "fda.gov",
    "cdc.gov",
    "nih.gov",
    "grants.nih.gov",
    "reporter.nih.gov",
    "federalregister.gov",
    "regulations.gov",
    "gao.gov",
    "irs.gov",
    "propublica.org",
    "chinhphu.vn",
    "gso.gov.vn",
    "mof.gov.vn",
    "sbv.gov.vn",
    "noip.gov.vn",
    "dantaichinh.gov.vn",
    "who.int",
    "worldbank.org",
    "imf.org",
    "oecd.org",
}

PRIMARY_SUFFIXES = [
    ".gov",
    ".gov.vn",
    ".mil",
    ".edu",
    ".edu.vn",
    ".ac.uk",
]

SECONDARY_DOMAINS = {
    "reuters.com",
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "cnbc.com",
    "forbes.com",
    "fortune.com",
    "economist.com",
    "nytimes.com",
    "washingtonpost.com",
    "techcrunch.com",
    "theinformation.com",
    "venturebeat.com",
    "wired.com",
    "arstechnica.com",
    "stratechery.com",
    "gartner.com",
    "forrester.com",
    "mckinsey.com",
    "bcg.com",
    "bain.com",
    "statista.com",
    "vnexpress.net",
    "tuoitre.vn",
    "thanhnien.vn",
    "cafef.vn",
    "cafebiz.vn",
    "vneconomy.vn",
    "vietnamnet.vn",
    "vietstock.vn",
    "baodautu.vn",
}

TERTIARY_DOMAINS = {
    "reddit.com",
    "news.ycombinator.com",
    "medium.com",
    "substack.com",
    "quora.com",
    "twitter.com",
    "x.com",
    "threads.net",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "voz.vn",
    "tinhte.vn",
    "otofun.net",
    "webtretho.com",
    "discord.com",
    "github.com/discussions",
}

TIER_WEIGHTS: Dict[str, float] = {
    "PRIMARY": 1.0,
    "SECONDARY": 0.7,
    "TERTIARY": 0.4,
}


@dataclass
class SourceClassification:
    url: str
    domain: str
    tier: str  # PRIMARY, SECONDARY, TERTIARY
    weight: float
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceInventoryReport:
    total_sources: int
    primary_count: int
    secondary_count: int
    tertiary_count: int
    primary_ratio: float
    average_credibility_score: float
    quality_verdict: str  # HIGH_INTEGRITY, ACCEPTABLE, UNRELIABLE
    sources: List[SourceClassification] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SourceTierClassifier:
    """Classifies source URLs deterministically into reliability tiers."""

    def extract_domain(self, url: str) -> str:
        url_clean = url.strip()
        if not url_clean.startswith(("http://", "https://")):
            url_clean = "https://" + url_clean
        parsed = urlparse(url_clean)
        domain = (parsed.netloc or "").lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    def classify_url(self, url: str) -> SourceClassification:
        domain = self.extract_domain(url)
        url_lower = url.lower()

        # 1. Check Primary Exact Domains & Subdomains
        for pd in PRIMARY_DOMAIN_EXACT:
            if domain == pd or domain.endswith("." + pd):
                return SourceClassification(
                    url=url,
                    domain=domain,
                    tier="PRIMARY",
                    weight=TIER_WEIGHTS["PRIMARY"],
                    rationale="Trang cơ quan chính phủ, cổng dữ liệu báo cáo tài chính/sáng chế chính thức.",
                )

        # 2. Check Primary Suffixes (.gov, .edu, .mil)
        for suffix in PRIMARY_SUFFIXES:
            if domain.endswith(suffix):
                return SourceClassification(
                    url=url,
                    domain=domain,
                    tier="PRIMARY",
                    weight=TIER_WEIGHTS["PRIMARY"],
                    rationale=f"Tên miền cơ quan công quyền / học thuật ({suffix}).",
                )

        # 3. Check Substack / Medium / User-generated
        if "medium.com" in domain or "substack.com" in domain:
            return SourceClassification(
                url=url,
                domain=domain,
                tier="TERTIARY",
                weight=TIER_WEIGHTS["TERTIARY"],
                rationale="Nền tảng blog cá nhân, ý kiến quan điểm chưa qua thẩm định độc lập.",
            )

        # 4. Check Tertiary Domains
        for td in TERTIARY_DOMAINS:
            if domain == td or domain.endswith("." + td):
                return SourceClassification(
                    url=url,
                    domain=domain,
                    tier="TERTIARY",
                    weight=TIER_WEIGHTS["TERTIARY"],
                    rationale="Diễn đàn, mạng xã hội hoặc nội dung do cộng đồng người dùng tự đăng tải.",
                )

        # 5. Check Secondary Domains
        for sd in SECONDARY_DOMAINS:
            if domain == sd or domain.endswith("." + sd):
                return SourceClassification(
                    url=url,
                    domain=domain,
                    tier="SECONDARY",
                    weight=TIER_WEIGHTS["SECONDARY"],
                    rationale="Cơ quan báo chí chính thống uy tín, tổ chức tư vấn phân tích chuyên ngành.",
                )

        # 6. Heuristic for Investor Relations or Corporate Official Pages
        if any(kw in domain or kw in url_lower for kw in ["investor.", "investors.", "/ir/", "/annual-report"]):
            return SourceClassification(
                url=url,
                domain=domain,
                tier="PRIMARY",
                weight=TIER_WEIGHTS["PRIMARY"],
                rationale="Trang công bố thông tin quan hệ nhà đầu tư (IR) chính thức của doanh nghiệp.",
            )

        # Default fallback: Secondary if clean website, else Tertiary
        return SourceClassification(
            url=url,
            domain=domain,
            tier="SECONDARY",
            weight=TIER_WEIGHTS["SECONDARY"],
            rationale="Trang thông tin / website doanh nghiệp tổng quát.",
        )

    def evaluate_inventory(self, urls: List[str]) -> SourceInventoryReport:
        if not urls:
            return SourceInventoryReport(
                total_sources=0,
                primary_count=0,
                secondary_count=0,
                tertiary_count=0,
                primary_ratio=0.0,
                average_credibility_score=0.0,
                quality_verdict="UNRELIABLE",
                sources=[],
            )

        classified = [self.classify_url(u) for u in urls]
        p_count = sum(1 for c in classified if c.tier == "PRIMARY")
        s_count = sum(1 for c in classified if c.tier == "SECONDARY")
        t_count = sum(1 for c in classified if c.tier == "TERTIARY")
        total = len(classified)

        avg_score = round(sum(c.weight for c in classified) / total, 3)
        p_ratio = round(p_count / total, 3)

        if avg_score >= 0.80 or (p_count >= 2 and p_ratio >= 0.40):
            verdict = "HIGH_INTEGRITY"
        elif avg_score >= 0.60 and t_count <= (total * 0.40):
            verdict = "ACCEPTABLE"
        else:
            verdict = "UNRELIABLE"

        return SourceInventoryReport(
            total_sources=total,
            primary_count=p_count,
            secondary_count=s_count,
            tertiary_count=t_count,
            primary_ratio=p_ratio,
            average_credibility_score=avg_score,
            quality_verdict=verdict,
            sources=classified,
        )


def render_human_inventory(r: SourceInventoryReport) -> str:
    lines = [
        "=== Báo Cáo Phân Tầng Nguồn Tin (Source Tier Reliability) ===",
        f"Tổng số nguồn trích dẫn: {r.total_sources}",
        f"  - Primary (Cấp 1 - Hồ sơ gốc, .gov, SEC): {r.primary_count} ({r.primary_ratio:.1%})",
        f"  - Secondary (Cấp 2 - Báo chí uy tín):     {r.secondary_count}",
        f"  - Tertiary (Cấp 3 - Diễn đàn, MXH):       {r.tertiary_count}",
        f"Điểm tin cậy trung bình: {r.average_credibility_score:.2f} / 1.00",
        f"Đánh giá chất lượng chứng cứ: [{r.quality_verdict}]",
        "",
        "Chi tiết danh mục nguồn:",
    ]
    for s in r.sources:
        lines.append(f"  [{s.tier:9s}] {s.domain:25s} -> {s.url[:60]}")
        lines.append(f"               Lý do: {s.rationale}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify source URLs into reliability tiers.")
    parser.add_argument("--url", help="Single URL to classify")
    parser.add_argument("--input", help="Path to JSON or text file with list of URLs")
    parser.add_argument("--output", choices=["human", "json"], default="human")
    args = parser.parse_args()

    classifier = SourceTierClassifier()

    if args.url:
        res = classifier.classify_url(args.url)
        if args.output == "json":
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(f"[{res.tier}] {res.domain} (Weight: {res.weight}) -> {res.rationale}")
        return 0

    urls: List[str] = []
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("["):
                urls = json.loads(content)
            else:
                urls = [line.strip() for line in content.splitlines() if line.strip()]
    else:
        urls = [
            "https://www.sec.gov/edgar/searchedgar/companysearch",
            "https://techcrunch.com/2026/05/10/enterprise-ai-growth/",
            "https://www.reddit.com/r/SaaS/comments/xyz123/pricing_troubles/",
            "https://chinhphu.vn/nghi-dinh-chinh-sach-moi",
        ]

    report = classifier.evaluate_inventory(urls)
    if args.output == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_human_inventory(report))

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
