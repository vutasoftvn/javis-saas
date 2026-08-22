import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://javis:javis@localhost:5432/javis")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Mọi model đã schema-qualify tường minh (schema="..." trong __table_args__,
# FK string đã có tiền tố schema) sau khi tách 280 bảng khỏi `public` thành
# agent_runtime/integrations + 11 schema domain (finance, sales, marketing,
# legal, validation, strategy, operating, knowledge, policy_funding, core,
# runtime_ops) - search_path này chỉ là lớp phòng hờ cho raw SQL/thư viện
# bên thứ ba (vd. Alembic tooling) tham chiếu tên bảng không schema-qualify.
_connect_args = {}
if DATABASE_URL.startswith("postgresql://"):
    _connect_args["options"] = (
        "-csearch_path=public,agent_runtime,integrations,"
        "finance,sales,marketing,legal,validation,strategy,operating,"
        "knowledge,policy_funding,core,runtime_ops"
    )

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
