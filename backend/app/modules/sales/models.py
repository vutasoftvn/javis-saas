from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.snowflake import generate_snowflake_id
from app.db.base_class import Base


class SalesLead(Base):
    __tablename__ = "sales_leads"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    key_result_id: Mapped[Optional[int]] = mapped_column(ForeignKey("key_results.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stage: Mapped[str] = mapped_column(String(30), default="NEW")
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
