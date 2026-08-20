from sqlalchemy import BigInteger, Column, Integer, String, JSON
from sqlalchemy.schema import UniqueConstraint
from app.db.base_class import Base

class ExtensionRegistration(Base):
    __tablename__ = "extension_registrations"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(BigInteger, nullable=False)
    extension_id = Column(String, nullable=False)
    version = Column(String, nullable=False)
    status = Column(String, nullable=False)
    disabled_reason = Column(String, nullable=True)
    manifest_jsonb = Column(JSON, nullable=False)
    capabilities_jsonb = Column(JSON, nullable=True)
    health_jsonb = Column(JSON, nullable=False, default={})

    __table_args__ = (
        UniqueConstraint("workspace_id", "extension_id", name="uq_extension_workspace"),
    )
