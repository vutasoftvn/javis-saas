from unittest.mock import MagicMock, patch

from app.core.snowflake import generate_snowflake_id
from app.modules.devices.service import create_developer_job
from app.modules.outcomes.models import Outcome


def test_developer_job_tags_scoped_outcome_as_tech():
    db = MagicMock()
    outcome = Outcome(id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), title="Ship", desired_result="Done", requested_by=generate_snowflake_id())
    db.query.return_value.filter.return_value.first.return_value = outcome
    with patch("app.modules.devices.service.write_audit_log"), patch("app.modules.devices.service.publish_event"):
        create_developer_job(db, outcome.workspace_id, outcome.requested_by, "Implement", outcome_id=outcome.id)
    assert outcome.function == "TECH"
