from unittest.mock import MagicMock, patch

from app.core.snowflake import generate_snowflake_id
from app.integrations.devices.service import create_developer_job
from app.founder_os.outcomes.models import Outcome


def test_developer_job_tags_scoped_outcome_as_tech():
    db = MagicMock()
    outcome = Outcome(id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), title="Ship", desired_result="Done", requested_by=generate_snowflake_id())
    db.query.return_value.filter.return_value.first.return_value = outcome
    with patch("app.integrations.devices.service.write_audit_log"), patch("app.integrations.devices.service.publish_event"):
        create_developer_job(db, outcome.workspace_id, outcome.requested_by, "Implement", outcome_id=outcome.id)
    assert outcome.function == "TECH"
