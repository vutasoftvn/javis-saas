from __future__ import annotations

import asyncio
import json
import jwt
import pytest
from starlette.testclient import TestClient

from agentos.api.app import app
from agentos.api.auth import JWT_SECRET
from agentos.api.chat.routes import set_agent_runtime
from agentos.api.db.session import reset_db_for_testing
from agentos.core.embedding_provider import StubEmbeddingProvider
from agentos.core.factory import build_cosa_agent_plane
from agentos.core.model_provider import ModelResponse, StubModelProvider
from agentos.knowledge.ingest import KnowledgeIngestPipeline
from agentos.knowledge.models import KnowledgeSource, KnowledgeSourceType
from agentos.knowledge.store import InMemoryKnowledgeStore


def make_token(user_id="user_1", workspace_id="ws_test", company_id="comp_1", role="founder"):
    return jwt.encode(
        {
            "sub": user_id,
            "workspace_id": workspace_id,
            "company_id": company_id,
            "role": role,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def test_chat_turn_emits_structured_citation_events():
    reset_db_for_testing("sqlite:///:memory:")

    # Set up KnowledgeStore with ingested document
    embedding_provider = StubEmbeddingProvider(dimensions=4)
    knowledge_store = InMemoryKnowledgeStore()
    pipeline = KnowledgeIngestPipeline(embedding_provider, knowledge_store)

    source = KnowledgeSource(
        id="src-policy-1",
        workspace_id="ws_test",
        title="Privacy Policy",
        source_type=KnowledgeSourceType.POLICY,
        uri="https://company.example.com/privacy",
    )
    # Ingest document
    asyncio.run(
        pipeline.ingest(source, "Data is retained for 30 days before automatic deletion.")
    )

    model_provider = StubModelProvider([ModelResponse(text="According to the policy, data is deleted after 30 days.")])
    runtime = build_cosa_agent_plane(
        model_provider=model_provider,
        knowledge_store=knowledge_store,
        embedding_provider=embedding_provider,
    )

    set_agent_runtime(runtime)

    client = TestClient(app)
    token = make_token()
    headers = {
        "Authorization": f"Bearer {token}",
    }

    # Create conversation
    create_resp = client.post(
        "/agent/conversations",
        json={"title": "Policy Question"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    conv_id = create_resp.json()["id"]

    # Send message referencing ingested knowledge
    msg_resp = client.post(
        f"/agent/conversations/{conv_id}/messages",
        json={"content": "Data retention policy duration"},
        headers=headers,
    )
    assert msg_resp.status_code == 202
    run_id = msg_resp.json()["run_id"]

    # Read events from stream
    events_resp = client.get(
        f"/agent/runs/{run_id}/events",
        headers=headers,
    )
    assert events_resp.status_code == 200
    lines = events_resp.text.strip().split("\n")

    events = []
    current_event = {}
    for line in lines:
        if line.startswith("event:"):
            current_event["event"] = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            current_event["data"] = json.loads(line.split(":", 1)[1].strip())
            events.append(current_event)
            current_event = {}

    citation_events = [e for e in events if e.get("event") == "citation"]
    assert len(citation_events) >= 1
    citation_payload = citation_events[0]["data"]["payload"]
    assert citation_payload["source_id"] == "src-policy-1"
    assert "Data is retained" in citation_payload["text"]
    assert citation_payload["score"] > 0
