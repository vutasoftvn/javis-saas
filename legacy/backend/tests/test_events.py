import asyncio
import json
from core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from db.models import WorkspaceMember
from core.events import publish_event, event_broker, EventEnvelope
from platform_core.core.events_router import stream_workspace_events


@pytest.mark.asyncio
async def test_publish_event_and_subscribe():
    ws_id = generate_snowflake_id()
    actor_id = generate_snowflake_id()
    
    # Subscribe to broker
    sub_gen = event_broker.subscribe(str(ws_id))
    
    # Publish event
    envelope = publish_event(
        event_type="approval.resolved",
        workspace_id=ws_id,
        actor_id=actor_id,
        payload={"step_id": "test-step", "status": "approved"}
    )
    
    assert envelope.event_type == "approval.resolved"
    assert envelope.workspace_id == str(ws_id)
    assert envelope.actor_id == str(actor_id)
    
    # Receive from subscriber queue
    received = await anext(sub_gen)
    assert received.event_id == envelope.event_id
    assert received.event_type == "approval.resolved"
    assert received.payload["status"] == "approved"
    
    # Cleanup subscription
    await sub_gen.aclose()


@pytest.mark.asyncio
async def test_stream_workspace_events_cross_tenant_forbidden():
    ws_id_a = generate_snowflake_id()
    ws_id_b = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id_a
    
    with pytest.raises(HTTPException) as exc_info:
        await stream_workspace_events(workspace_id=ws_id_b, member=member)
        
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_stream_workspace_events_handshake():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    res = await stream_workspace_events(workspace_id=ws_id, member=member)
    assert res is not None
