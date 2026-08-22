"""cosa_core dùng chung Base/metadata với app để 1 Alembic env hiện có
(`backend/alembic/`) tự thấy các bảng cosa_core — không tạo migration env riêng."""
from db.base_class import Base

__all__ = ["Base"]
