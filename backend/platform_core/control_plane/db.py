"""Declarative base riêng cho COSA Central Control Plane (Quyết định 2,
docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md dòng 176-197).

KHÔNG dùng chung `app.db.base_class.Base`/`app.db.base.Base` của Local
Business DB. Central Control Plane là 1 trong 3 vai trò DB tách biệt
(Personal Business DB / Team Business DB / Central Control Plane) — xem
Quyết định 2. Khi tạm thời co-locate cùng 1 Postgres instance với Local
Business DB (cấu hình mặc định hiện tại của `docker-compose.yml` gốc, biến
`CONTROL_PLANE_DATABASE_URL`), mọi bảng nằm trong schema Postgres
`control_plane` — KHÔNG phải `public` — để tránh trùng tên bảng với Local
Business DB. Va chạm cụ thể đã verify: `app.platform.core.deployment_models
.Deployment.__tablename__ == "deployments"` (Local, schema `public`) trùng
tên với bảng control-plane `deployments` (VPS deployment registry, cột hoàn
toàn khác) nếu cả 2 cùng nằm `public` trong cùng 1 database.
"""
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

CONTROL_PLANE_SCHEMA = "cosa"

convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
}


class ControlPlaneBase(DeclarativeBase):
    metadata = MetaData(schema=CONTROL_PLANE_SCHEMA, naming_convention=convention)

