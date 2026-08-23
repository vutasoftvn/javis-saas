from __future__ import annotations

import os
from pathlib import Path
import uuid
import pytest

from agentos.connectors.vault import InMemoryVaultStore, SecretNotFoundError
from agentos.core.approval import ApprovalAlreadyDecidedError, ApprovalNotFoundError, ApprovalService
from agentos.core.audit_sink import SqliteAuditSink
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.policy import DataScope, ExecutionMode, PermissionLevel, PolicyDecision, PolicyEngine, ToolRiskLevel
from agentos.core.redaction import REDACTED_PLACEHOLDER, redact_payload
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.providers.tencent_agent_memory import TencentAgentMemoryStore
from agentos.memory.store import InMemoryMemoryStore
from agentos.tools.registry import ToolRegistry


REPO_ROOT = Path(__file__).resolve().parents[3]


# -----------------------------------------------------------------------------
# 12a.1: Forbidden directions (§3.1)
# -----------------------------------------------------------------------------
def test_security_forbidden_directions_zero_occurrences():
    # Check services/ and agentos/ for unwanted imports
    agentos_dir = REPO_ROOT / "agentos"
    for py_file in agentos_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        # Ensure no real import of cosa_core
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("import cosa_core") or line_str.startswith("from cosa_core"):
                pytest.fail(f"Found forbidden cosa_core import in {py_file}: {line_str}")

    # Check adk directory for legacy imports
    adk_dir = agentos_dir / "orchestration" / "adk"
    for py_file in adk_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            line_str = line.strip()
            if "from legacy." in line_str or "import legacy." in line_str:
                pytest.fail(f"Found forbidden legacy import in ADK node {py_file}: {line_str}")

    # Check frontend/lib for database driver imports
    frontend_lib = REPO_ROOT / "frontend" / "lib"
    if frontend_lib.exists():
        for dart_file in frontend_lib.rglob("*.dart"):
            content = dart_file.read_text(encoding="utf-8")
            for db_pkg in ["package:postgres", "package:sqflite", "package:drift"]:
                if db_pkg in content:
                    pytest.fail(f"Found direct database import in Flutter frontend {dart_file}: {db_pkg}")


# -----------------------------------------------------------------------------
# 12a.2: Trace redaction coverage (§7.4)
# -----------------------------------------------------------------------------
def test_security_trace_redaction_comprehensive_coverage():
    sensitive_dict = {
        "api_key": "sk-secret-key-12345",
        "access_token": "ghp_1234567890abcdefghij",
        "password": "SuperSecretPassword!",
        "client_secret": "my-client-secret",
        "nested": {
            "token": "xoxb-9876543210-abcdef123456",
            "session_token": "sess-xyz-999",
        },
    }
    redacted = redact_payload(sensitive_dict)
    assert redacted["api_key"] == REDACTED_PLACEHOLDER
    assert redacted["access_token"] == REDACTED_PLACEHOLDER
    assert redacted["password"] == REDACTED_PLACEHOLDER
    assert redacted["nested"]["token"] == REDACTED_PLACEHOLDER
    assert redacted["nested"]["session_token"] == REDACTED_PLACEHOLDER


# -----------------------------------------------------------------------------
# 12a.3: No silent no-op (§14.3)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_security_no_silent_noop_on_missing_dependencies():
    # Tencent provider stub must fail loudly (NotImplementedError), never silent no-op
    provider = TencentAgentMemoryStore()
    item = MemoryItem(
        workspace_id="ws1",
        agent_key="bot",
        kind=MemoryKind.WORKING,
        content="test memory",
    )
    with pytest.raises(NotImplementedError):
        await provider.put(item)

    # Vault store must fail loudly on missing secrets
    vault = InMemoryVaultStore()
    with pytest.raises(SecretNotFoundError):
        await vault.get_secret("non_existent_key")


# -----------------------------------------------------------------------------
# 12a.4: Tenant isolation (cross-workspace / cross-company)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_security_tenant_isolation_cross_workspace_separation():
    store = InMemoryMemoryStore()
    await store.put(
        MemoryItem(
            workspace_id="ws_acme",
            agent_key="co_founder",
            kind=MemoryKind.SEMANTIC,
            content="Acme proprietary strategy data",
        )
    )
    await store.put(
        MemoryItem(
            workspace_id="ws_beta",
            agent_key="co_founder",
            kind=MemoryKind.SEMANTIC,
            content="Beta Corp confidential data",
        )
    )

    # Acme cannot see Beta data
    acme_items = await store.search(workspace_id="ws_acme")
    assert len(acme_items) == 1
    assert "Acme" in acme_items[0].content
    assert "Beta" not in acme_items[0].content

    # Beta cannot see Acme data
    beta_items = await store.search(workspace_id="ws_beta")
    assert len(beta_items) == 1
    assert "Beta" in beta_items[0].content


# -----------------------------------------------------------------------------
# 12a.5: Governance bypass check
# -----------------------------------------------------------------------------
def test_security_governance_enforces_read_only_scope_override():
    engine = PolicyEngine()
    # Write tool must be denied when DataScope is READ_ONLY
    decision = engine.evaluate_access(
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
        tool_risk_level=ToolRiskLevel.LOW,
        tool_permission="scoped_write",
        data_scope=DataScope.READ_ONLY,
    )
    assert decision == PolicyDecision.DENY


# -----------------------------------------------------------------------------
# 12a.6: Approval integrity & replay prevention
# -----------------------------------------------------------------------------
def test_security_approval_integrity_and_replay_rejection():
    svc = ApprovalService()
    app = svc.request_approval(action="deploy", subject="production", requester="agent_1")

    # Non-existent approval ID lookup throws
    with pytest.raises(ApprovalNotFoundError):
        svc.decide("fake-non-existent-approval-id", reviewer="admin", approved=True)

    # Decide once succeeds
    svc.decide(app.id, reviewer="admin", approved=True)

    # Replay/duplicate decision must be rejected
    with pytest.raises(ApprovalAlreadyDecidedError):
        svc.decide(app.id, reviewer="attacker", approved=False)


# -----------------------------------------------------------------------------
# 12a.7: Secret & credential isolation
# -----------------------------------------------------------------------------
def test_security_vault_does_not_leak_secrets_into_audit():
    audit_sink = SqliteAuditSink()
    vault = InMemoryVaultStore()
    vault.set_secret("slack_bot_token", "xoxb-super-secret-bot-token-9999", workspace_id="ws1")

    test_run_id = f"run_secret_test_{uuid.uuid4().hex}"

    # Record event in audit sink with token field
    audit_sink.record(
        event_type="connector.invoked",
        run_id=test_run_id,
        tool_name="commercial.notification.slack_send",
        input_payload={"channel": "general", "token": "xoxb-super-secret-bot-token-9999"},
    )

    logs = audit_sink.export_run(test_run_id)
    assert len(logs) == 1
    assert "xoxb-super-secret-bot-token-9999" not in str(logs[0]["input_payload"])
    assert REDACTED_PLACEHOLDER in str(logs[0]["input_payload"])
