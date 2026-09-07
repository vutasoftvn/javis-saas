"""agent_app phải INSERT được vào event_inbox sau migrate-all (bug B2)."""

from __future__ import annotations

import os
import uuid

import psycopg2
import pytest

# `make agent-test` truyền AGENT_TEST_DATABASE_URL="" (chuỗi rỗng) khi dev chưa
# export biến — `dict.get(key, default)` KHÔNG trả default cho chuỗi rỗng, nên
# phải fallback bằng `or` để không vô tình gọi psycopg2.connect("") (→ unix
# socket mặc định, luôn fail trên máy dev dùng TCP).
#
# `psycopg2` cần scheme `postgresql://` trần — nhiều test file Postgres khác
# trong cùng lần chạy `make agent-test` lại quy ước `AGENT_TEST_DATABASE_URL`
# theo scheme `postgresql+asyncpg://` (SQLAlchemy). Chuẩn hoá scheme ở đây
# (KHÔNG đổi role/credentials — test này cố tình cần đúng role trong biến môi
# trường được truyền, không tự ý đổi sang role khác) để chạy đúng bất kể
# caller export theo format nào.
_APP_URL = (
    os.environ.get("AGENT_TEST_DATABASE_URL")
    or "postgresql://agent_app:change-me-agent-app@127.0.0.1:5432/agent?sslmode=disable"
).replace("postgresql+asyncpg://", "postgresql://")


@pytest.mark.integration
def test_agent_app_can_insert_into_event_inbox() -> None:
    conn = psycopg2.connect(_APP_URL, connect_timeout=5)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO event_inbox
                  (workspace_id, event_id, consumer_name, event_type, correlation_id, outcome)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                ("ws-b2", str(uuid.uuid4()), "b2-consumer", "test.evt", "corr-b2", "accepted"),
            )
            cur.execute("SELECT count(*) FROM event_trigger_rules")
            # Kiểm tra thật là: SELECT/INSERT phía trên KHÔNG raise InsufficientPrivilege.
            # count(*) chỉ cần trả về một int hợp lệ (>= 0 luôn đúng, vô nghĩa).
            assert isinstance(cur.fetchone()[0], int)
    finally:
        conn.close()
