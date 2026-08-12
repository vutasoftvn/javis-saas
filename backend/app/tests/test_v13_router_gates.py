from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.snowflake import generate_snowflake_id
from app.modules.marketing.router import require_marketing_feature
from app.modules.strategy.okrs_router import require_okrs_feature


@pytest.mark.parametrize("guard", [require_marketing_feature, require_okrs_feature])
def test_v13_router_guard_rejects_disabled_feature(guard):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        guard(workspace_id=generate_snowflake_id(), db=db)

    assert exc.value.status_code == 403
