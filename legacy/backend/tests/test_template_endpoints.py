from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from core.snowflake import generate_snowflake_id
from founder_os.strategy.routers.template_router import reset_workspace_template


def _member(role: str):
    m = MagicMock()
    m.workspace_id = generate_snowflake_id()
    m.user_id = generate_snowflake_id()
    m.role = role
    return m


def test_reset_endpoint_rejects_non_admin():
    member = _member(role="member")

    with pytest.raises(HTTPException) as exc_info:
        reset_workspace_template(
            template_id=generate_snowflake_id(),
            workspace_id=member.workspace_id,
            member=member,
            db=MagicMock(),
        )

    assert exc_info.value.status_code == 403
