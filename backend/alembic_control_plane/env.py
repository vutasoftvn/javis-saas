from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text as sa_text

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.platform.control_plane.db import ControlPlaneBase, CONTROL_PLANE_SCHEMA
import app.platform.control_plane.models  # noqa: F401  (đăng ký model vào metadata)

target_metadata = ControlPlaneBase.metadata


def _resolve_url() -> str:
    url = (
        os.environ.get("CONTROL_PLANE_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or config.get_main_option("sqlalchemy.url")
    )
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_resolve_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=CONTROL_PLANE_SCHEMA,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _resolve_url()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # `version_table_schema` bên dưới yêu cầu schema `control_plane` đã
        # tồn tại TRƯỚC KHI Alembic tạo bảng theo dõi revision
        # (`control_plane.alembic_version`) — tạo trước ở đây, ngoài vòng đời
        # migration, để tránh lỗi "schema does not exist" ở lần chạy đầu tiên
        # trên 1 database trống.
        connection.execute(sa_text(f"CREATE SCHEMA IF NOT EXISTS {CONTROL_PLANE_SCHEMA}"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=CONTROL_PLANE_SCHEMA,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
