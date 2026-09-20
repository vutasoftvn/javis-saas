"""Bộ kiểm định bài viết LinkedIn (100% Python Standard Library).

Thực hiện kiểm tra cơ học bài viết: độ dài hook mở đầu trước điểm ngắt "Xem thêm",
chặn đứng ký tự Unicode pseudo-bold (Accessibility Gate), kiểm tra khoảng trắng,
số lượng hashtag và cảnh báo đặt link ngoài trong thân bài.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = [
    "LinkedInPostLinter",
    "LinkedInPostReport",
    "LintFinding",
]


@dataclass(frozen=True)
class LintFinding:
    """Một vi phạm hoặc cảnh báo được phát hiện khi lint bài viết."""

    code: str
    message: str
    severity: str  # "BLOCKING" | "WARNING" | "INFO"
    line_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LinkedInPostReport:
    """Báo cáo kiểm định toàn diện bài viết LinkedIn."""

    is_valid: bool  # False nếu có bất kỳ lỗi BLOCKING nào
    total_characters: int
    hook_text: str
    hook_length: int
    has_early_fold_break: bool
    findings: list[LintFinding] = field(default_factory=list)
    hashtag_count: int = 0
    link_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "total_characters": self.total_characters,
            "hook_text": self.hook_text,
            "hook_length": self.hook_length,
            "has_early_fold_break": self.has_early_fold_break,
            "hashtag_count": self.hashtag_count,
            "link_count": self.link_count,
            "findings": [f.to_dict() for f in self.findings],
        }


class LinkedInPostLinter:
    """Linter bài viết LinkedIn theo tiêu chuẩn tiếp cận & thuật toán hữu cơ."""

    # Dải Unicode Mathematical Alphanumeric Symbols (pseudo-bold, pseudo-italic)
    # Ví dụ: 𝗮 𝗯 𝗰, 𝐚 𝐛 𝐜, 𝒂 𝒃 𝒄  # noqa: RUF003
    PSEUDO_UNICODE_PATTERN = re.compile(r"[\U0001D400-\U0001D7FF]")

    @classmethod
    def lint(cls, text: str) -> LinkedInPostReport:
        raw_text = text.strip()
        findings: list[LintFinding] = []

        if not raw_text:
            findings.append(
                LintFinding(
                    code="EMPTY_POST",
                    message="Nội dung bài viết rỗng.",
                    severity="BLOCKING",
                )
            )
            return LinkedInPostReport(
                is_valid=False,
                total_characters=0,
                hook_text="",
                hook_length=0,
                has_early_fold_break=False,
                findings=findings,
            )

        total_chars = len(raw_text)

        # 1. Giới hạn độ dài tổng thể (LinkedIn post cap là 3000 ký tự)
        if total_chars > 3000:
            findings.append(
                LintFinding(
                    code="EXCEEDS_LENGTH_LIMIT",
                    message=f"Bài viết dài {total_chars} ký tự, vượt quá giới hạn 3000 ký tự của LinkedIn.",
                    severity="BLOCKING",
                )
            )
        elif total_chars < 40:
            findings.append(
                LintFinding(
                    code="TOO_SHORT",
                    message="Bài viết quá ngắn (< 40 ký tự) để tạo ra chiều sâu thảo luận hữu cơ.",
                    severity="WARNING",
                )
            )

        # 2. Cổng kiểm soát khả năng tiếp cận (Accessibility Gate): Unicode Pseudo-Bold
        pseudo_chars = cls.PSEUDO_UNICODE_PATTERN.findall(raw_text)
        if pseudo_chars:
            sample = "".join(pseudo_chars[:5])
            findings.append(
                LintFinding(
                    code="BLOCKING_UNICODE_PSEUDO_BOLD",
                    message=(
                        f"Phát hiện ký tự Unicode pseudo-bold/italic ('{sample}...'). "
                        "Đây là lỗi chặn (BLOCKING) vì gây hỏng trình đọc màn hình cho người khiếm thị "
                        "và khiến bộ máy tìm kiếm của LinkedIn không thể lập chỉ mục từ khóa."
                    ),
                    severity="BLOCKING",
                )
            )

        # 3. Phân tích Hook trước điểm ngắt "Xem thêm" (See more fold)
        # Mobile: ~140 ký tự; Desktop: ~210 ký tự
        lines = raw_text.splitlines()
        first_paragraph = lines[0] if lines else ""
        hook_length = len(first_paragraph)

        has_early_fold_break = hook_length <= 160 and len(lines) > 1 and lines[1].strip() == ""
        if hook_length > 210:
            findings.append(
                LintFinding(
                    code="HOOK_TOO_LONG",
                    message=(
                        f"Dòng mở đầu (Hook) dài {hook_length} ký tự, sẽ bị nút 'Xem thêm' cắt ngang lưng chừng. "
                        "Nên ngắt dòng trước 140 ký tự để tạo tò mò trọn vẹn."
                    ),
                    severity="WARNING",
                    line_number=1,
                )
            )

        # 4. Kiểm tra luật nghiệm thuật toán 2026 cho Dòng mở đầu (Hook)
        clean_first_para = first_paragraph.strip().lower()
        is_question_hook = clean_first_para.endswith("?") or bool(
            re.match(
                r"^(tại sao|liệu|bạn có biết|ai là|why|how|what|ever wondered|did you know|have you ever)\b",
                clean_first_para,
            )
        )
        if is_question_hook:
            findings.append(
                LintFinding(
                    code="QUESTION_FIRST_HOOK",
                    message=(
                        "Dòng mở đầu là câu hỏi. Nghiên cứu thực nghiệm 2026 cho thấy mở bài bằng câu hỏi "
                        "làm giảm 34% median likes. Khuyến nghị đổi dòng 1 thành con số hoặc tuyên bố khẳng định, "
                        "và chuyển câu hỏi thảo luận xuống dòng kết bài (+3% tương tác)."
                    ),
                    severity="WARNING",
                    line_number=1,
                )
            )

        # Phát hiện số liệu ở dòng 1 (Tín hiệu tích cực +34% median likes)
        has_number_in_hook = bool(re.search(r"(\$|€|£|₫)?\b\d+([.,]\d+)?\b%?", clean_first_para))
        if has_number_in_hook and not is_question_hook:
            findings.append(
                LintFinding(
                    code="NUMBER_FIRST_HOOK",
                    message=(
                        "Dòng mở đầu chứa số liệu cụ thể. Đây là tín hiệu hook rất mạnh "
                        "theo nghiên cứu thuật toán 2026 (+34% median likes)."
                    ),
                    severity="INFO",
                    line_number=1,
                )
            )

        # 5. Phát hiện thủ thuật câu tương tác (Comment-Gate Bait)
        comment_gate_patterns = [
            r"\b(comment|bình luận)\s+(bên dưới|để nhận|xuống dưới|x để|để lấy)\b",
            r"\bcomment\s+(below|to get|for link)\b",
            r"\bagree\?\s+comment\b",
        ]
        lower_raw = raw_text.lower()
        if any(re.search(p, lower_raw) for p in comment_gate_patterns):
            findings.append(
                LintFinding(
                    code="COMMENT_GATE_BAIT",
                    message=(
                        "Phát hiện mẫu câu kéo tương tác (Comment-Gate Bait). "
                        "Thuật toán LinkedIn 2026 xử phạt giảm khoảng 40% hiển thị đối với bài viết kêu gọi "
                        "'comment để nhận tài liệu'. Hãy cung cấp giá trị trực tiếp hoặc đặt link ở bình luận đầu tiên."
                    ),
                    severity="WARNING",
                )
            )

        # 6. Kiểm tra quy tắc mật độ cấu trúc (Density Rule) & Cầu nối lộ liễu
        reveal_bridges = [
            r"(kết quả là\?|the result\?|plot twist:|here's what|here's how|điều bất ngờ là:)",
        ]
        found_bridges = [p for p in reveal_bridges if re.search(p, lower_raw)]
        if found_bridges:
            findings.append(
                LintFinding(
                    code="REVEAL_BRIDGE_USED",
                    message=(
                        "Phát hiện câu nối dẫn dắt lộ liễu kiểu AI ('The result?', 'Plot twist:', 'Here's what'). "
                        "Thuật toán và người đọc 2026 phản ứng tiêu cực với mẫu câu này. Hãy viết tự nhiên liền mạch."
                    ),
                    severity="WARNING",
                )
            )

        # 7. Giới hạn mật độ Em-dash (không quá 1 dấu / 100 từ)
        words_count = len(re.findall(r"\b\w+\b", raw_text))
        em_dashes = len(re.findall(r"(—|--)", raw_text))
        if words_count > 0:
            em_dash_density = (em_dashes / words_count) * 100
            if em_dash_density > 1.5 and em_dashes > 2:
                findings.append(
                    LintFinding(
                        code="EXCESSIVE_EM_DASH",
                        message=(
                            f"Phát hiện {em_dashes} dấu gạch ngang em-dash ({em_dash_density:.1f}/100 từ). "
                            "Mật độ tối ưu là tối đa 1 dấu/100 từ. Hãy thay bớt bằng dấu phẩy, hai chấm hoặc ngoặc đơn."
                        ),
                        severity="WARNING",
                    )
                )

        # 8. Kiểm tra liên kết ngoài trong thân bài
        links = re.findall(r"https?://\S+", raw_text)
        if links:
            findings.append(
                LintFinding(
                    code="IN_BODY_EXTERNAL_LINK",
                    message=(
                        f"Phát hiện {len(links)} liên kết ngoài trong thân bài. "
                        "Theo kinh nghiệm thuật toán LinkedIn, bài viết dẫn link ngoài có thể giảm thời gian dừng (dwell time). "
                        "Cân nhắc đưa link xuống bình luận đầu tiên hoặc giải thích đầy đủ giá trị ngay trong bài."
                    ),
                    severity="WARNING",
                )
            )

        # 9. Kiểm tra mật độ Hashtag
        hashtags = re.findall(r"#\w+", raw_text)
        if len(hashtags) > 5:
            findings.append(
                LintFinding(
                    code="HASHTAG_OVERUSE",
                    message=f"Phát hiện {len(hashtags)} hashtags. Sử dụng quá 5 hashtags làm bài viết trông giống thư rác.",
                    severity="WARNING",
                )
            )

        # 10. Kiểm tra cấu trúc phân đoạn (Tránh khối văn bản dầy đặc - Wall of Text)
        for i, line in enumerate(lines, start=1):
            if len(line) > 350:
                findings.append(
                    LintFinding(
                        code="WALL_OF_TEXT_LINE",
                        message=f"Đoạn {i} quá dài ({len(line)} ký tự) không ngắt nhịp. Hãy chia thành các câu ngắn 1-2 dòng.",
                        severity="WARNING",
                        line_number=i,
                    )
                )

        has_blocking = any(f.severity == "BLOCKING" for f in findings)
        is_valid = not has_blocking

        return LinkedInPostReport(
            is_valid=is_valid,
            total_characters=total_chars,
            hook_text=first_paragraph[:100] + ("..." if len(first_paragraph) > 100 else ""),
            hook_length=hook_length,
            has_early_fold_break=has_early_fold_break,
            findings=findings,
            hashtag_count=len(hashtags),
            link_count=len(links),
        )
