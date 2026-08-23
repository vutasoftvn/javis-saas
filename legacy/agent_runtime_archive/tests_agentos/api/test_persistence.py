import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agentos.api.db.models import Base
from agentos.api.db.repository import ChatRepository


@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "test_chat.sqlite3"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_conversation_and_message_crud_and_persistence_across_sessions(tmp_path):
    db_file = tmp_path / "test_persist.sqlite3"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    SessionFactory = sessionmaker(bind=engine)

    # 1. Session 1: Create conversation and messages
    s1 = SessionFactory()
    repo1 = ChatRepository(s1)
    conv = repo1.create_conversation(
        company_id="company-100",
        workspace_id="workspace-200",
        created_by_principal="user:founder-1",
        title="Q3 Strategy",
        active_agent_profile="founder_agent",
    )
    conv_id = conv.id

    msg1 = repo1.create_message(
        conversation_id=conv_id,
        role="user",
        content="What is our burn rate?",
    )
    msg2 = repo1.create_message(
        conversation_id=conv_id,
        role="assistant",
        content="Burn rate is $10k/mo.",
    )
    s1.close()

    # 2. Session 2 (simulate process restart with new DB session)
    s2 = SessionFactory()
    repo2 = ChatRepository(s2)
    loaded_conv = repo2.get_conversation(conv_id, company_id="company-100", workspace_id="workspace-200")
    assert loaded_conv is not None
    assert loaded_conv.title == "Q3 Strategy"

    loaded_msgs = repo2.list_messages(conv_id)
    assert len(loaded_msgs) == 2
    assert loaded_msgs[0].content == "What is our burn rate?"
    assert loaded_msgs[1].content == "Burn rate is $10k/mo."
    s2.close()


def test_attachment_persistence_only_stores_reference(db_session):
    repo = ChatRepository(db_session)
    conv = repo.create_conversation(
        company_id="comp-1",
        workspace_id="ws-1",
        created_by_principal="user:1",
        title="File Test",
    )
    msg = repo.create_message(conversation_id=conv.id, role="user", content="Here is my document")

    att = repo.create_attachment(
        message_id=msg.id,
        object_ref="s3://storage-bucket/reports/q3.pdf",
        media_type="application/pdf",
        file_name="q3.pdf",
        size=1048576,
        checksum="sha256:abcd1234ef",
    )

    assert att.id is not None
    assert att.object_ref == "s3://storage-bucket/reports/q3.pdf"
    assert att.file_name == "q3.pdf"
    assert att.size == 1048576
    # Verify no raw binary is stored
    assert not hasattr(att, "binary_data")


def test_run_event_redaction_before_persistence(db_session):
    repo = ChatRepository(db_session)
    sensitive_payload = {
        "user_goal": "Check balance",
        "api_key": "sk-secret-12345",
        "authorization": "Bearer secret-token-xyz",
        "password": "super-secret-password",
        "nested": {
            "access_token": "oauth-token-999",
            "safe_data": "public-info",
        },
    }

    event = repo.save_run_event(
        run_id="run-sec-1",
        sequence=1,
        event_type="tool.requested",
        payload=sensitive_payload,
    )

    loaded_events = repo.get_run_events("run-sec-1")
    assert len(loaded_events) == 1
    stored_json = json.loads(loaded_events[0].payload_redacted)

    assert stored_json["api_key"] == "***REDACTED***"
    assert stored_json["authorization"] == "***REDACTED***"
    assert stored_json["password"] == "***REDACTED***"
    assert stored_json["nested"]["access_token"] == "***REDACTED***"
    assert stored_json["nested"]["safe_data"] == "public-info"
    assert stored_json["user_goal"] == "Check balance"
