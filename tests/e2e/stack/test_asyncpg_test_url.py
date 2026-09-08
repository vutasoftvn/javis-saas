"""Test đơn vị cho `asyncpg_test_url()` — không cần Postgres/Encore thật, đây
là thao tác chuỗi thuần (parse/rewrite URL).

Task 7 (plan platform-authority-durability-hardening) Step 1: normalizer dùng
chung phải (1) đổi scheme sang `postgresql+asyncpg`, (2) bỏ RIÊNG param
`sslmode` (asyncpg không hiểu, raise `unexpected keyword argument 'sslmode'`),
(3) giữ nguyên các param khác (vd. `application_name`) cùng credential/host/
database.
"""

from __future__ import annotations

from tests.e2e.stack.subprocess_stack import asyncpg_test_url


def test_asyncpg_test_url_strips_sslmode_and_keeps_other_params() -> None:
    result = asyncpg_test_url("postgresql://u:p@host/db?sslmode=disable&application_name=cosa")

    assert result == "postgresql+asyncpg://u:p@host/db?application_name=cosa"


def test_asyncpg_test_url_normalizes_bare_postgres_scheme() -> None:
    assert asyncpg_test_url("postgres://u:p@host:5432/db") == "postgresql+asyncpg://u:p@host:5432/db"


def test_asyncpg_test_url_is_idempotent_on_already_asyncpg_scheme() -> None:
    already = "postgresql+asyncpg://u:p@host/db?application_name=cosa"
    assert asyncpg_test_url(already) == already
