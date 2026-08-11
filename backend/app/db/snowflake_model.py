from datetime import datetime
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.snowflake import generate_snowflake_id, parse_snowflake, snowflake_to_datetime


class SnowflakeIDMixin:
    """Mixin cung cấp khóa chính Snowflake ID 64-bit tối ưu B-Tree Index cho SQLAlchemy Models."""

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        index=True,
        doc="64-bit k-ordered Snowflake ID"
    )

    @property
    def id_str(self) -> str:
        """Trả về ID dạng chuỗi (String) an toàn khi serialize JSON."""
        return str(self.id)

    @property
    def created_at_from_id(self) -> datetime:
        """Trích xuất thời điểm tạo trực tiếp từ 41 bits timestamp của Snowflake ID."""
        return snowflake_to_datetime(self.id)

    def parse_id(self) -> dict:
        """Phân tích các trường thông tin (timestamp, node_id, sequence) trong ID."""
        return parse_snowflake(self.id)
