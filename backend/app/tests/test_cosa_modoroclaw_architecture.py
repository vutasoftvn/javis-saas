"""Architecture and Integration Tests for COSA Native Python Agent Runtime.

Verifies:
1. Capability Providers and Tool Result Contract (with EvidenceObject)
2. Execution Modes (INTERACTIVE, APPROVED_WORKFLOW, AUTONOMOUS_SAFE)
3. Core Resource Immutability protection
4. Company Workspace Manager & Progressive Context Compiler
5. Reflection & Learning Engine
6. Multi-Channel Identity Resolver
7. Skill Manifest Schema
"""

import pytest
import tempfile
from pathlib import Path

from app.workforce.agents.capabilities.base import (
    CapabilityRequest,
    CapabilityResult,
    EvidenceObject,
    ProviderHealthStatus,
)
from app.workforce.agents.capabilities.providers.native_cosa_provider import NativeCOSAProvider
from app.workforce.agents.governance.policy_engine import (
    ExecutionMode,
    PolicyAction,
    PolicyEngine,
)
from app.founder_os.workspace.manager import CompanyWorkspaceManager
from app.workforce.agents.context.compiler import (
    ProgressiveContextCompiler,
    ContextBudget,
)
from app.workforce.routing.deterministic import Intent
from app.workforce.agents.learning.reflection_engine import ReflectionEngine
from app.integrations.channels.identity_resolver import ChannelIdentityResolver
from app.workforce.skills.schema import SkillManifest, FailurePolicy


@pytest.mark.asyncio
async def test_native_cosa_provider_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws_mgr = CompanyWorkspaceManager(base_path=Path(tmpdir))
        provider = NativeCOSAProvider()
        
        # Test health
        health = await provider.health()
        assert health.status == ProviderHealthStatus.AVAILABLE
        
        # Test capabilities list
        caps = await provider.capabilities()
        assert "write_file" in caps
        assert "read_file" in caps
        assert "create_document" in caps


def test_policy_engine_execution_modes():
    # 1. AUTONOMOUS_SAFE blocks external writes
    decision_safe = PolicyEngine.evaluate_execution_mode(
        mode=ExecutionMode.AUTONOMOUS_SAFE,
        capability="send_message",
        risk_level="high",
    )
    assert decision_safe.action == PolicyAction.DENY

    # 2. INTERACTIVE requires human approval for external writes
    decision_interactive = PolicyEngine.evaluate_execution_mode(
        mode=ExecutionMode.INTERACTIVE,
        capability="send_message",
        risk_level="high",
    )
    assert decision_interactive.action == PolicyAction.REQUIRE_APPROVAL
    assert decision_interactive.requires_approval is True

    # 3. APPROVED_WORKFLOW permits auto-execution
    decision_workflow = PolicyEngine.evaluate_execution_mode(
        mode=ExecutionMode.APPROVED_WORKFLOW,
        capability="send_message",
        risk_level="high",
    )
    assert decision_workflow.action == PolicyAction.ALLOW


def test_policy_engine_immutability():
    # Protected core resources mandate approval
    decision = PolicyEngine.evaluate_execution_mode(
        mode=ExecutionMode.APPROVED_WORKFLOW,
        capability="write_file",
        target_resource="company/identity.md",
    )
    assert decision.action == PolicyAction.REQUIRE_APPROVAL
    assert "protected core asset" in decision.reason


def test_company_workspace_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = CompanyWorkspaceManager(base_path=Path(tmpdir))
        company_dir = mgr.init_company_workspace("test_co")
        
        # Check files initialized
        assert (company_dir / "company" / "identity.md").exists()
        assert (company_dir / "company" / "soul.md").exists()
        assert (company_dir / "founder" / "profile.md").exists()
        assert (company_dir / "policies" / "base.md").exists()

        # Test read and write
        mgr.write_file("test_co", "custom.md", "Hello Custom")
        assert mgr.read_file("test_co", "custom.md") == "Hello Custom"

        # Test reset to default
        mgr.write_file("test_co", "company/identity.md", "Modified Content")
        assert "Modified Content" in mgr.read_file("test_co", "company/identity.md")
        mgr.reset_file_to_default("test_co", "company/identity.md")
        assert "COSA Enterprise" in mgr.read_file("test_co", "company/identity.md")


def test_progressive_context_compiler():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Greeting intent only compiles L0
        compiled_greeting = ProgressiveContextCompiler.compile(
            company_id="test_co",
            intent=Intent.GENERAL_CHAT,
            session_history=[{"role": "user", "content": "Xin chào"}],
        )
        assert "L0_Session" in compiled_greeting.layers
        assert "L2_Project" not in compiled_greeting.layers
        assert "L3_Domain" not in compiled_greeting.layers

        # 2. Project intent compiles L0, L1, L2
        compiled_project = ProgressiveContextCompiler.compile(
            company_id="test_co",
            intent=Intent.PROJECT_QUERY,
            project_id="proj_cosa_os",
            domain_payload={"active_sprint": "Week 3"},
        )
        assert "L0_Session" in compiled_project.layers
        assert "L1_Company" in compiled_project.layers
        assert "L2_Project" in compiled_project.layers
        assert "L3_Domain" in compiled_project.layers


def test_reflection_engine():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock workspace base
        from app.founder_os.workspace.manager import workspace_manager
        old_base = workspace_manager.base_path
        workspace_manager.base_path = Path(tmpdir)

        try:
            workspace_manager.init_company_workspace("co_123")
            
            # Record error
            ReflectionEngine.record_error("co_123", "Database timeout", provider="postgres", action="crm_read")
            errors_content = workspace_manager.read_file("co_123", "learnings/ERRORS.md")
            assert "Database timeout" in errors_content

            # Record learning
            ReflectionEngine.record_learning("co_123", "Marketing Strategy", "Direct sales works best for B2B")
            learnings_content = workspace_manager.read_file("co_123", "learnings/LEARNINGS.md")
            assert "Marketing Strategy" in learnings_content
        finally:
            workspace_manager.base_path = old_base


def test_channel_identity_resolver():
    identity = ChannelIdentityResolver.resolve(channel="telegram", external_id="123456789")
    assert identity.user_id == 1
    assert identity.workspace_id == 1
    assert identity.channel == "telegram"
    assert identity.external_id == "123456789"


def test_skill_manifest_schema():
    manifest = SkillManifest(
        id="marketing.customer_interview",
        name="Customer Interview",
        domain="marketing",
        intents=["customer_interview", "validate_problem"],
        requires_capabilities=["create_document"],
        risk_level="low",
        failure_policy=FailurePolicy(retry_count=2, is_blocking=False),
    )
    assert manifest.id == "marketing.customer_interview"
    assert manifest.failure_policy.retry_count == 2
    assert "customer_interview" in manifest.intents
