from core.snowflake import generate_snowflake_id

from db.models import AIRun


def test_ai_run_preserves_chat_usage_metadata():
    workspace_id = generate_snowflake_id()
    chat_session_id = generate_snowflake_id()
    chat_message_id = generate_snowflake_id()

    run = AIRun(
        workspace_id=workspace_id,
        chat_session_id=chat_session_id,
        chat_message_id=chat_message_id,
        provider="deepseek",
        model="deepseek-chat",
        status="completed",
        input_tokens=123,
        output_tokens=45,
    )

    assert run.workspace_id == workspace_id
    assert run.chat_session_id == chat_session_id
    assert run.chat_message_id == chat_message_id
    assert run.status == "completed"
    assert run.input_tokens == 123
    assert run.output_tokens == 45
