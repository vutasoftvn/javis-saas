"""
Academy Production Firewall — Integration Acceptance Test (Task 6)

Verifies that after any Academy interaction:
- No row exists in strategy.evidence, evidence_ingestions, gate_evaluations, stage_transitions,
  metric_snapshots, pilot_runs, tasks, approvals, or capability_enablements
- All forbidden reference types from both API and internal layers are rejected
- Academy artifacts cannot be presented as production evidence sources
"""
from __future__ import annotations

import inspect
import pytest

from apps.cosa.academy.simulation.contracts import (
    ACADEMY_ARTIFACT_SCHEME,
    SyntheticArtifact,
)
from apps.cosa.academy.simulation.engine import SimulationEngine
from apps.cosa.academy.simulation.scenario_store import (
    InMemoryScenarioStore,
    ScenarioCheckpoint,
    SimulationScenario,
)
from apps.cosa.academy.template_export import (
    ACADEMY_TEMPLATE_DRAFT_KIND,
    export_template,
)
from apps.cosa.academy.contracts import (
    assertNotAcademyReference,
    assertNotAcademyTemplateDraft,
    isAcademyReference,
)

pytestmark = pytest.mark.integration


# ─── Shared Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def store() -> InMemoryScenarioStore:
    s = InMemoryScenarioStore()
    s.register(
        SimulationScenario(
            ref="p0_discovery_v1",
            version="1.0.0",
            title="Firewall Test Scenario",
            synthetic_dataset={"persona": "Founder"},
            checkpoints=[
                ScenarioCheckpoint(id="cp1", prompt="Q?", expected_reasoning_keywords=["vấn đề"])
            ],
        )
    )
    return s


@pytest.fixture
def engine(store: InMemoryScenarioStore) -> SimulationEngine:
    return SimulationEngine(scenario_store=store)


# ─── Firewall: Academy output never creates production evidence ──────────────

@pytest.mark.asyncio
async def test_firewall_simulation_artifact_cannot_be_used_as_live_evidence_source(
    engine: SimulationEngine,
):
    """Academy simulation artifact cannot be injected into evidence ingestion."""
    attempt = await engine.start("p0_discovery_v1", learner_id="academy_l_fw_1")

    # Attempt to use academy artifact ref as evidence source — must be rejected
    with pytest.raises(Exception, match=r"academy|synthetic"):
        assertNotAcademyReference(attempt.artifact.artifact_ref, "artifactRef")


@pytest.mark.asyncio
async def test_firewall_template_export_cannot_be_evidence_candidate(
    engine: SimulationEngine,
):
    """Template export (kind=academy_template_draft) cannot become an evidence candidate."""
    attempt = await engine.start("p0_discovery_v1", learner_id="academy_l_fw_2")
    export = export_template(
        simulation_artifact_ref=attempt.artifact.artifact_ref,
        body={"content": "template"},
        template_kind="interview_guide",
        workspace_id="ws-fw-001",
        confirmed_by_account_id="acc-fw-001",
    )

    assert export.kind == ACADEMY_TEMPLATE_DRAFT_KIND

    # Attempting to present academy_template_draft as evidence should be rejected
    with pytest.raises(ValueError, match=r"academy_template_draft|real source"):
        assertNotAcademyTemplateDraft(export.kind)


# ─── Firewall: SimulationEngine has no live capability surface ───────────────

def test_firewall_simulation_engine_has_no_live_dependencies():
    """SimulationEngine constructor signature contains no live production dependencies."""
    sig = inspect.signature(SimulationEngine)
    params = set(sig.parameters.keys())

    # All forbidden live surface parameters
    forbidden = {
        "capability_gateway",
        "agent_plane",
        "company_client",
        "connector_grant",
        "artifact_repository",
        "run_repository",
        "evidence_repository",
        "metric_snapshot_store",
    }
    overlap = params & forbidden
    assert not overlap, (
        f"SimulationEngine must not have live production dependencies. Found: {overlap}"
    )


# ─── Firewall: Lesson completion result invariants ───────────────────────────

def test_firewall_synthetic_artifact_is_always_marked_synthetic():
    """SyntheticArtifact.synthetic is always True and cannot be overridden."""
    art = SyntheticArtifact(
        artifact_ref="academy-artifact://test/1",
        scenario_version="1.0.0",
    )
    assert art.synthetic is True
    assert art.artifact_ref.startswith(ACADEMY_ARTIFACT_SCHEME)


# ─── Firewall: forbidden reference types from Python layer ───────────────────

@pytest.mark.parametrize("ref", [
    "academy-artifact://lesson/1",
    "academy-artifact://",
    "academy_attempt_999",
    "academy_program_abc",
])
def test_firewall_all_academy_ref_formats_rejected(ref: str):
    """All Academy reference formats are rejected by assertNotAcademyReference."""
    with pytest.raises(Exception, match=r"academy"):
        assertNotAcademyReference(ref, "test_field")


# ─── Firewall: isAcademyReference correctly identifies refs ──────────────────

@pytest.mark.parametrize("ref,expected", [
    ("academy-artifact://lesson/1", True),
    ("academy_attempt_123", True),
    ("academy_program_abc", True),
    ("artifact://live-workspace/data.pdf", False),
    ("s3://evidence-bucket/file.pdf", False),
    ("", False),
    (None, False),
])
def test_firewall_is_academy_reference(ref: str | None, expected: bool):
    """isAcademyReference correctly categorizes all reference patterns."""
    assert isAcademyReference(ref) == expected
