"""Session/engine riêng cho COSA Central Control Plane, tách biệt khỏi
`db.session` (Local Business DB). Đọc `CONTROL_PLANE_DATABASE_URL` - nếu
biến này trỏ vào database khác với `DATABASE_URL` (đúng topology mặc định
hiện tại: database riêng `cosa_control_plane`, xem .env.example), mọi query
PlatformUser/Company/CompanyMembership/Profile/... phải đi qua session này,
không phải `db.session.get_db`, nếu không sẽ đọc/ghi nhầm sang schema
`control_plane` bên trong DB Local Business (đã xảy ra thật - xem lịch sử)."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

CONTROL_PLANE_DATABASE_URL = os.environ.get(
    "CONTROL_PLANE_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://javis:javis@localhost:5432/javis"),
)
if CONTROL_PLANE_DATABASE_URL.startswith("postgres://"):
    CONTROL_PLANE_DATABASE_URL = CONTROL_PLANE_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(CONTROL_PLANE_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_control_plane_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
