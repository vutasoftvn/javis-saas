"""Chứng minh: tạo cluster disposable -> migrate-all -> connect bằng *_app role
-> teardown DROP sạch. Fail rõ nếu Postgres admin không reachable (không skip)."""

from __future__ import annotations

import os
import secrets

import pytest

from tests.e2e.stack.disposable_postgres import (
    apply_migrations,
    create_disposable_cluster,
    drop_disposable_cluster,
)

# psycopg2 chỉ được cài ở job `e2e-cross-plane-smoke`; các job khác collect
# `tests/e2e` mà không có nó, nên import module-scope sẽ làm đỏ collection.
# Marker `cross_plane` chỉ deselect SAU khi module đã import → phải import cục bộ.
pytestmark = pytest.mark.cross_plane


@pytest.fixture()
def cluster():
    # run_id ngẫu nhiên: các lần chạy song song / bị ngắt không bao giờ đụng tên.
    c = create_disposable_cluster(run_id=secrets.token_hex(4))
    try:
        apply_migrations(c)
        yield c
    finally:
        drop_disposable_cluster(c)


def test_app_role_can_read_migrated_schema(cluster) -> None:
    # agent_app phải truy vấn được bảng do migration tạo trong schema có tên
    # (không phải public) — chứng minh _grant_application_access đã chạy.
    import psycopg2

    conn = psycopg2.connect(cluster.agent_app_url, connect_timeout=5)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('knowledge.source_versions')")
            assert cur.fetchone()[0] is not None
    finally:
        conn.close()


def test_databases_are_dropped_on_teardown() -> None:
    import psycopg2

    c = create_disposable_cluster(run_id=secrets.token_hex(4))
    try:
        apply_migrations(c)
        drop_disposable_cluster(c)
        # Admin creds đọc từ env cho portable — máy dev dùng superuser khác
        # `postgres/postgres` (xem task brief env note); CI vẫn set PGPASSWORD=postgres.
        admin = psycopg2.connect(
            dbname="postgres",
            host=os.environ.get("PGHOST", "127.0.0.1"),
            port=int(os.environ.get("PGPORT", "5432")),
            user=os.environ.get("PGUSER", "postgres"),
            password=os.environ.get("PGPASSWORD", "postgres"),
            connect_timeout=5,
        )
        try:
            with admin.cursor() as cur:
                cur.execute(
                    "SELECT datname FROM pg_database WHERE datname LIKE %s",
                    (f"%{c.run_id}%",),
                )
                assert cur.fetchall() == []
        finally:
            admin.close()
    finally:
        # Dọn kể cả khi apply_migrations / assert giữa chừng fail.
        drop_disposable_cluster(c)
