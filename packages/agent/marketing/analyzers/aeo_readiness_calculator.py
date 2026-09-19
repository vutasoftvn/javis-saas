"""Bộ tính toán độ sẵn sàng tối ưu tìm kiếm AI / AEO (100% Python Standard Library).

Đánh giá mức độ tối ưu để được các công cụ tìm kiếm ngôn ngữ lớn (Perplexity,
ChatGPT Search, Claude, Google AI Overviews) trích dẫn làm nguồn thẩm quyền.
Đo lường E-E-A-T, mật độ sự thật (Factual Density), và Fact-First Lede.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = [
    "AEODimensionScore",
    "AEOReadinessCalculator",
    "AEOReadinessReport",
]


@dataclass(frozen=True)
class AEODimensionScore:
    """Điểm số cho từng khía cạnh E-E-A-T."""

    dimension: str
    score: float  # 0.0 -> 100.0
    weight: float
    evidence_found: list[str] = field(default_factory=list)
    missing_signals: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AEOReadinessReport:
    """Báo cáo đánh giá mức độ sẵn sàng AEO."""

    overall_score: float  # 0.0 -> 100.0
    grade: str  # A, B, C, D
    dimension_scores: dict[str, float]
    factual_density_per_1000: float  # Số luận điểm sự thật trên 1000 từ
    fact_count: int
    has_fact_first_lede: bool
    question_header_count: int
    schema_ready: bool
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AEOReadinessCalculator:
    """Bộ tính toán độ sẵn sàng AEO tất định thuần Python."""

    @classmethod
    def calculate(cls, text: str) -> AEOReadinessReport:
        raw_text = text.strip()
        if not raw_text:
            return AEOReadinessReport(
                overall_score=0.0,
                grade="D",
                dimension_scores={
                    "experience": 0.0,
                    "expertise": 0.0,
                    "authoritativeness": 0.0,
                    "trustworthiness": 0.0,
                },
                factual_density_per_1000=0.0,
                fact_count=0,
                has_fact_first_lede=False,
                question_header_count=0,
                schema_ready=False,
                recommendations=["Văn bản rỗng. Không có dữ liệu để đánh giá AEO."],
            )

        words = re.findall(r"\b\w+\b", raw_text)
        word_count = max(1, len(words))

        # 1. Đo lường Mật độ sự thật (Factual Density)
        # Tìm các con số, phần trăm, năm, tiền tệ, trích dẫn số [1], đơn vị đo
        facts_patterns = [
            r"\b\d+(?:\.\d+)?%\b",  # 25%, 3.5%
            r"[\$€£₫¥]\s*\d+(?:,\d+)*(?:\.\d+)?\b",  # $1,000, 500₫
            r"\b\d+(?:,\d+)*(?:\.\d+)?\s*(?:USD|VND|EUR|users|leads|seconds|minutes|hours|days|percent|lần|phút|giờ|ngày|khách hàng)\b",
            r"\b20(?:1\d|2\d|30)\b",  # Mốc năm: 2018 - 2030
            r"\[\d+\]",  # Dấu trích dẫn [1], [2]
            r"\b(?:Case Study|Nghiên cứu điển hình|Báo cáo|Benchmark|Survey)\b",
        ]
        found_facts: list[str] = []
        for pat in facts_patterns:
            matches = re.findall(pat, raw_text, re.IGNORECASE)
            found_facts.extend(matches)

        fact_count = len(found_facts)
        factual_density = round((fact_count / word_count) * 1000, 2)

        # 2. Fact-First Lede (200 từ đầu tiên có chứa sự thật)
        first_200_words = " ".join(words[:200])
        first_200_facts = sum(
            len(re.findall(pat, first_200_words, re.IGNORECASE))
            for pat in facts_patterns
        )
        has_fact_first_lede = first_200_facts >= 2

        # 3. Tiêu đề dạng câu hỏi (Question-style headings) — cực kỳ thân thiện với LLM Q&A
        headers = re.findall(r"^(?:#{1,4})\s+(.+)$", raw_text, re.MULTILINE)
        question_header_count = sum(
            1
            for h in headers
            if h.strip().endswith("?")
            or re.match(r"^(?:How|What|Why|When|Where|Who|Làm sao|Tại sao|Là gì|Khi nào)\b", h.strip(), re.IGNORECASE)
        )

        # 4. Kiểm tra sẵn sàng Schema / Dữ liệu có cấu trúc
        schema_ready = bool(
            re.search(r"@context|schema\.org|\"application/ld\+json\"|FAQPage|Article|HowTo", raw_text, re.IGNORECASE)
            or (headers and any("faq" in h.lower() or "câu hỏi" in h.lower() for h in headers))
        )

        # 5. Chấm điểm 4 trụ cột E-E-A-T
        # Experience: Ngôi thứ nhất ("chúng tôi đã thử nghiệm", "in our tests", "our data")
        exp_signals = re.findall(
            r"\b(we tested|our team|we found|in our experience|chúng tôi đã|thực tế thử nghiệm|dữ liệu nội bộ|our data)\b",
            raw_text,
            re.IGNORECASE,
        )
        score_exp = min(100.0, len(exp_signals) * 25.0 + (25.0 if fact_count >= 3 else 0.0) + (20.0 if has_fact_first_lede else 0.0))

        # Expertise: Chiều sâu kỹ thuật, tiêu đề dạng câu hỏi Q&A, cấu trúc phân đoạn
        score_expert = min(
            100.0,
            (len(headers) * 12.0)
            + (question_header_count * 15.0)
            + (25.0 if fact_count >= 3 else 0.0)
            + min(30.0, word_count / 15.0),
        )

        # Authoritativeness: Trích dẫn, nguồn tham chiếu, đối chiếu bên ngoài, schema
        auth_signals = len(re.findall(r"(?:https?://|\[\d+\]|nguồn:|source:|theo nghiên cứu|schema:)", raw_text, re.IGNORECASE))
        score_auth = min(100.0, auth_signals * 25.0 + (25.0 if schema_ready else 0.0))

        # Trustworthiness: Mật độ sự thật cao, mở đầu minh bạch, không nói quá
        score_trust = min(100.0, factual_density * 3.0 + (30.0 if has_fact_first_lede else 0.0))

        # Điểm tổng hợp có trọng số
        overall = (score_exp * 0.25) + (score_expert * 0.25) + (score_auth * 0.25) + (score_trust * 0.25)
        overall = round(overall, 1)

        if overall >= 85.0:
            grade = "A"
        elif overall >= 70.0:
            grade = "B"
        elif overall >= 50.0:
            grade = "C"
        else:
            grade = "D"

        # Khuyến nghị
        recommendations: list[str] = []
        if not has_fact_first_lede:
            recommendations.append(
                "Fact-First Lede chưa đạt: Hãy đưa ít nhất 2 luận điểm kiểm chứng được (số liệu, mốc thời gian, kết quả) vào 200 từ mở đầu."
            )
        if factual_density < 10.0:
            recommendations.append(
                f"Mật độ sự thật thấp ({factual_density}/1000 từ). Bổ sung thêm số liệu cụ thể hoặc dẫn chứng trích dẫn để LLM dễ trích nguồn."
            )
        if question_header_count == 0:
            recommendations.append(
                "Nên định dạng một số đề mục (H2/H3) dưới dạng câu hỏi trực diện (VD: '... là gì?', 'Làm sao để...?') để khớp với truy vấn người dùng trên Perplexity/ChatGPT."
            )
        if not schema_ready:
            recommendations.append(
                "Bổ sung cấu trúc dữ liệu JSON-LD (Schema FAQPage hoặc TechArticle) để tăng thẩm quyền nhận diện của bộ máy tìm kiếm AI."
            )

        return AEOReadinessReport(
            overall_score=overall,
            grade=grade,
            dimension_scores={
                "experience": round(score_exp, 1),
                "expertise": round(score_expert, 1),
                "authoritativeness": round(score_auth, 1),
                "trustworthiness": round(score_trust, 1),
            },
            factual_density_per_1000=factual_density,
            fact_count=fact_count,
            has_fact_first_lede=has_fact_first_lede,
            question_header_count=question_header_count,
            schema_ready=schema_ready,
            recommendations=recommendations,
        )
