"""Bộ phân tích giọng điệu thương hiệu & văn phong (100% Python Standard Library).

Phân tích điểm đọc dễ hiểu (Flesch Reading Ease), chỉ số trang trọng (Formality Index),
tỷ lệ câu bị động và phát hiện các từ sáo rỗng AI (AI Clichés / Buzzwords).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = [
    "BrandVoiceAnalyzer",
    "BrandVoiceReport",
]

# Danh sách đen các từ AI sáo rỗng & từ vựng quản trị AI phổ biến 2025-2026
AI_CLICHES: tuple[str, ...] = (
    "revolutionize",
    "revolutionary",
    "seamless",
    "seamlessly",
    "tapestry",
    "delve",
    "delving",
    "game-changer",
    "game changer",
    "foster",
    "fostering",
    "testament",
    "beacon",
    "elevate",
    "elevating",
    "unleash",
    "unleashing",
    "supercharge",
    "cutting-edge",
    "paradigm shift",
    "synergy",
    "holistic",
    "empower",
    "empowering",
    "robust",
    "ever-evolving",
    "transformative",
    "spearhead",
    "breathtaking",
    "groundbreaking",
    # Bổ sung các từ vựng AI quản trị 2026 (durable corporate AI tells)
    "crucial",
    "comprehensive",
    "notably",
    "leverage",
    "leveraging",
    "landscape",
    "nuanced",
    "multifaceted",
    "streamline",
    "streamlining",
    "insights",
)


@dataclass(frozen=True)
class BrandVoiceReport:
    """Kết quả phân tích giọng điệu và văn phong bản thảo."""

    word_count: int
    sentence_count: int
    syllable_count: int
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    reading_level: str
    formality_score: float  # 0.0 (rất thân mật/suồng sã) -> 100.0 (rất trang trọng)
    passive_sentence_count: int
    passive_ratio: float  # 0.0 -> 1.0
    flagged_cliches: list[str] = field(default_factory=list)
    average_words_per_sentence: float = 0.0
    max_paragraph_ai_density: int = 0
    forced_burstiness_detected: bool = False
    staccato_sequences: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BrandVoiceAnalyzer:
    """Bộ phân tích văn phong thuần túy không dùng thư viện ngoài."""

    @staticmethod
    def count_syllables(word: str) -> int:
        """Đếm số âm tiết của một từ tiếng Anh theo quy tắc ngữ âm cơ bản."""
        cleaned = re.sub(r"[^a-zA-Z]", "", word).lower()
        if not cleaned:
            return 1
        if len(cleaned) <= 3:
            return 1

        # Xóa 'e' câm ở cuối từ (trừ trường hợp 'le' sau phụ âm)
        if cleaned.endswith("e") and not cleaned.endswith("le"):
            cleaned = cleaned[:-1]

        # Đếm nhóm nguyên âm liên tiếp
        groups = re.findall(r"[aeiouy]+", cleaned)
        count = len(groups)
        return max(1, count)

    @classmethod
    def analyze(cls, text: str) -> BrandVoiceReport:
        """Phân tích văn bản và trả về báo cáo chi tiết."""
        raw_text = text.strip()
        if not raw_text:
            return BrandVoiceReport(
                word_count=0,
                sentence_count=0,
                syllable_count=0,
                flesch_reading_ease=100.0,
                flesch_kincaid_grade=0.0,
                reading_level="Very Easy",
                formality_score=50.0,
                passive_sentence_count=0,
                passive_ratio=0.0,
                flagged_cliches=[],
                average_words_per_sentence=0.0,
                max_paragraph_ai_density=0,
                forced_burstiness_detected=False,
                staccato_sequences=[],
                recommendations=["Văn bản rỗng. Vui lòng cung cấp nội dung."],
            )

        # 1. Tách câu
        sentences = [s.strip() for s in re.split(r"[.!?]+(?:\s+|$)", raw_text) if s.strip()]
        sentence_count = max(1, len(sentences))

        # 2. Tách từ
        words = re.findall(r"\b[a-zA-ZÀ-ỹ0-9'-]+\b", raw_text)
        word_count = max(1, len(words))

        # 3. Đếm âm tiết
        syllable_count = sum(cls.count_syllables(w) for w in words)

        # 4. Tính toán Flesch Reading Ease & Grade Level
        words_per_sentence = word_count / sentence_count
        syllables_per_word = syllable_count / word_count

        fre = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
        fre = round(max(0.0, min(100.0, fre)), 2)

        fkg = (0.39 * words_per_sentence) + (11.8 * syllables_per_word) - 15.59
        fkg = round(max(0.0, fkg), 2)

        if fre >= 80.0:
            reading_level = "Easy / Conversational"
        elif fre >= 60.0:
            reading_level = "Standard / Plain English"
        elif fre >= 40.0:
            reading_level = "Moderately Complex"
        else:
            reading_level = "Difficult / Academic"

        # 5. Phát hiện câu bị động (Passive voice)
        passive_regex = re.compile(
            r"\b(am|is|are|was|were|be|been|being)\s+([a-zA-Z]+ed|[a-zA-Z]+en|done|written|made|built|seen|known|taken)\b",
            re.IGNORECASE,
        )
        passive_count = sum(1 for s in sentences if passive_regex.search(s))
        passive_ratio = round(passive_count / sentence_count, 2)

        # 6. Phát hiện từ AI clichés / buzzwords & tính mật độ theo đoạn
        lower_text = raw_text.lower()
        found_cliches: list[str] = []
        for cliche in AI_CLICHES:
            pattern = rf"\b{re.escape(cliche)}\b"
            if re.search(pattern, lower_text):
                found_cliches.append(cliche)

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw_text) if p.strip()]
        max_para_density = 0
        for p in paragraphs:
            p_lower = p.lower()
            p_density = sum(1 for c in AI_CLICHES if re.search(rf"\b{re.escape(c)}\b", p_lower))
            max_para_density = max(max_para_density, p_density)

        # 7. Phát hiện nhịp điệu giật cục cưỡng ép (Forced Burstiness / Staccato sequences)
        staccato_runs: list[str] = []
        sentence_word_counts = [len(re.findall(r"\b[a-zA-ZÀ-ỹ0-9'-]+\b", s)) for s in sentences]
        for i in range(len(sentence_word_counts) - 2):
            if (
                sentence_word_counts[i] <= 4
                and sentence_word_counts[i + 1] <= 4
                and sentence_word_counts[i + 2] <= 4
            ):
                seq = " // ".join(sentences[i : i + 3])
                staccato_runs.append(seq)
        forced_burstiness = len(staccato_runs) > 0

        # 8. Tính Formality Index (0-100)
        # Các yếu tố tăng tính trang trọng: độ dài từ trung bình cao, câu bị động, không có viết tắt
        # Các yếu tố giảm tính trang trọng: viết tắt (don't, can't), đại từ nhân xưng ngôi thứ nhất (I, we, you)
        contractions = len(
            re.findall(r"\b[a-zA-Z]+'(?:t|s|re|ve|ll|d|m)\b", raw_text, re.IGNORECASE)
        )
        first_person = len(re.findall(r"\b(i|we|my|our|us|you|your)\b", raw_text, re.IGNORECASE))
        avg_word_len = sum(len(w) for w in words) / word_count

        formality = (
            50.0
            + (avg_word_len - 4.5) * 12.0
            + (passive_ratio * 20.0)
            - (contractions * 3.0)
            - (first_person * 1.5)
        )
        formality_score = round(max(0.0, min(100.0, formality)), 1)

        # 9. Khuyến nghị cải thiện
        recommendations: list[str] = []
        if max_para_density >= 3:
            recommendations.append(
                f"Mật độ từ vựng AI trong một đoạn văn cao ({max_para_density} từ/đoạn). "
                "Theo chuẩn 2026, mật độ từ $\ge 3$ kích hoạt bộ lọc AI-slop. Hãy phân tán hoặc thay bằng từ cụ thể."
            )
        elif found_cliches:
            recommendations.append(
                f"Phát hiện {len(found_cliches)} từ sáo rỗng AI: {', '.join(found_cliches[:5])}. Hãy thay bằng từ ngữ cụ thể, đời thường."
            )

        if forced_burstiness:
            recommendations.append(
                f"Phát hiện nhịp điệu giật cục cưỡng ép (Staccato): '{staccato_runs[0]}'. "
                "Chuỗi 3 câu siêu ngắn liên tiếp là dấu hiệu AI tell số 1 năm 2026. Hãy kết nối các vế câu một cách tự nhiên."
            )

        # Phát hiện false vulnerability
        false_vuln_pattern = r"\b(thú thật là|thành thật mà nói|let me be honest|confession:)\b"
        if re.search(false_vuln_pattern, lower_text):
            recommendations.append(
                "Phát hiện mẫu câu thú nhận gượng gạo ('thú thật là...', 'let me be honest'). "
                "Theo thực nghiệm 2026, đây là dấu hiệu giả tạo (false vulnerability). Hãy trình bày sự việc và số liệu trực diện."
            )

        if words_per_sentence > 22.0:
            recommendations.append(
                f"Độ dài câu trung bình cao ({words_per_sentence:.1f} từ/câu). Hãy chia nhỏ các câu dài để tăng tính lưu loát."
            )
        if passive_ratio > 0.20:
            recommendations.append(
                f"Tỷ lệ câu bị động cao ({passive_ratio * 100:.0f}%). Hãy chuyển sang thể chủ động để tăng sức thuyết phục."
            )
        if fre < 50.0:
            recommendations.append(
                f"Chỉ số Flesch thấp ({fre}), nội dung hơi hàn lâm. Hãy dùng từ đơn giản hơn cho độc giả đại chúng."
            )

        return BrandVoiceReport(
            word_count=word_count,
            sentence_count=sentence_count,
            syllable_count=syllable_count,
            flesch_reading_ease=fre,
            flesch_kincaid_grade=fkg,
            reading_level=reading_level,
            formality_score=formality_score,
            passive_sentence_count=passive_count,
            passive_ratio=passive_ratio,
            flagged_cliches=found_cliches,
            average_words_per_sentence=round(words_per_sentence, 1),
            max_paragraph_ai_density=max_para_density,
            forced_burstiness_detected=forced_burstiness,
            staccato_sequences=staccato_runs,
            recommendations=recommendations,
        )
