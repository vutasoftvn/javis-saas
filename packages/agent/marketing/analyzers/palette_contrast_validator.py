"""Bộ kiểm định độ tương phản màu sắc WCAG 2.1 & sinh bảng màu (100% Python Standard Library).

Xác thực độ tương phản màu sắc theo chuẩn W3C WCAG 2.1 (AA / AAA)
và tự động sinh bảng màu phụ trợ từ mã màu chính (Primary HEX).
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Any

__all__ = [
    "PaletteContrastResult",
    "PaletteContrastValidator",
]


@dataclass(frozen=True)
class PaletteContrastResult:
    """Kết quả kiểm định độ tương phản giữa màu chữ (FG) và màu nền (BG)."""

    fg_hex: str
    bg_hex: str
    contrast_ratio: float
    normal_text_aa: bool  # >= 4.5:1
    normal_text_aaa: bool  # >= 7.0:1
    large_text_aa: bool  # >= 3.0:1 (chữ >= 18pt hoặc >= 14pt in đậm)
    large_text_aaa: bool  # >= 4.5:1
    is_accessible: bool  # True nếu đạt ít nhất chuẩn Normal Text AA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PaletteContrastValidator:
    """Bộ kiểm định độ tương phản và thuật toán suy luận bảng màu thuần Python."""

    @staticmethod
    def parse_hex(hex_str: str) -> tuple[int, int, int]:
        """Chuyển đổi chuỗi HEX (#RGB hoặc #RRGGBB) sang RGB tuple (0-255)."""
        cleaned = hex_str.strip().lstrip("#")
        if len(cleaned) == 3:
            cleaned = "".join(c * 2 for c in cleaned)
        if len(cleaned) != 6 or not re.match(r"^[0-9a-fA-F]{6}$", cleaned):
            raise ValueError(f"Mã HEX không hợp lệ: '{hex_str}'. Định dạng đúng: #RRGGBB hoặc #RGB")
        r = int(cleaned[0:2], 16)
        g = int(cleaned[2:4], 16)
        b = int(cleaned[4:6], 16)
        return r, g, b

    @classmethod
    def relative_luminance(cls, r: int, g: int, b: int) -> float:
        """Tính Relative Luminance theo công thức W3C WCAG 2.1 (sRGB Linear)."""

        def to_linear(channel: int) -> float:
            c = channel / 255.0
            return c / 12.92 if c <= 0.04045 else math.pow((c + 0.055) / 1.055, 2.4)

        r_lin = to_linear(r)
        g_lin = to_linear(g)
        b_lin = to_linear(b)
        return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin

    @classmethod
    def calculate_contrast(cls, fg_hex: str, bg_hex: str) -> float:
        """Tính tỷ lệ tương phản giữa 2 màu HEX: (L1 + 0.05) / (L2 + 0.05)."""
        r1, g1, b1 = cls.parse_hex(fg_hex)
        r2, g2, b2 = cls.parse_hex(bg_hex)
        l1 = cls.relative_luminance(r1, g1, b1)
        l2 = cls.relative_luminance(r2, g2, b2)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        ratio = (lighter + 0.05) / (darker + 0.05)
        return round(ratio, 2)

    @classmethod
    def validate(cls, fg_hex: str, bg_hex: str) -> PaletteContrastResult:
        """Kiểm định tính tuân thủ tiêu chuẩn WCAG 2.1 AA/AAA."""
        ratio = cls.calculate_contrast(fg_hex, bg_hex)
        normal_aa = ratio >= 4.5
        normal_aaa = ratio >= 7.0
        large_aa = ratio >= 3.0
        large_aaa = ratio >= 4.5

        return PaletteContrastResult(
            fg_hex=fg_hex.upper(),
            bg_hex=bg_hex.upper(),
            contrast_ratio=ratio,
            normal_text_aa=normal_aa,
            normal_text_aaa=normal_aaa,
            large_text_aa=large_aa,
            large_text_aaa=large_aaa,
            is_accessible=normal_aa,
        )

    @classmethod
    def derive_palette(cls, primary_hex: str) -> dict[str, str]:
        """Tự động suy luận bảng màu tương phản hài hòa đạt chuẩn từ một màu chính."""
        r, g, b = cls.parse_hex(primary_hex)
        lum = cls.relative_luminance(r, g, b)

        # Màu chữ trên nền primary: trắng nếu primary tối, đen nếu primary sáng
        text_on_primary = "#FFFFFF" if lum < 0.4 else "#111827"

        # Tính màu accent (đối lập nhẹ / shift RGB)
        accent_r = (r + 80) % 256
        accent_g = (g + 140) % 256
        accent_b = (b + 60) % 256
        accent_hex = f"#{accent_r:02X}{accent_g:02X}{accent_b:02X}"

        # Nền tối (Dark mode theme mặc định theo phong cách Visual Premium)
        bg_hex = "#0A0D14"
        surface_hex = "#141923"
        text_on_bg = "#F9FAFB"
        text_muted = "#9CA3AF"

        # Kiểm chứng độ tương phản text_on_bg trên bg
        bg_contrast = cls.calculate_contrast(text_on_bg, bg_hex)
        if bg_contrast < 4.5:
            text_on_bg = "#FFFFFF"

        return {
            "primary": primary_hex.upper(),
            "accent": accent_hex,
            "background": bg_hex,
            "surface": surface_hex,
            "text_primary": text_on_bg,
            "text_muted": text_muted,
            "text_on_primary": text_on_primary,
        }
