from __future__ import annotations

import pytest

from apps.cosa.academy.simulation.contracts import SyntheticArtifact, ACADEMY_ARTIFACT_SCHEME
from apps.cosa.academy.simulation.engine import SimulationEngine
from apps.cosa.academy.simulation.scenario_store import (
    InMemoryScenarioStore,
    ScenarioCheckpoint,
    SimulationScenario,
)


@pytest.fixture
def scenario_store() -> InMemoryScenarioStore:
    store = InMemoryScenarioStore()
    store.register(
        SimulationScenario(
            ref="p0_discovery_v1",
            version="1.0.0",
            title="Khám phá Vấn đề",
            synthetic_dataset={"persona": "Founder"},
            checkpoints=[
                ScenarioCheckpoint(
                    id="cp1",
                    prompt="Câu hỏi?",
                    expected_reasoning_keywords=["vấn đề"],
                )
            ],
        )
    )
    return store


@pytest.fixture
def engine(scenario_store: InMemoryScenarioStore) -> SimulationEngine:
    return SimulationEngine(scenario_store=scenario_store)


def test_synthetic_artifact_requires_academy_scheme():
    """SyntheticArtifact rejects refs that don't start with 'academy-artifact://'."""
    with pytest.raises(ValueError, match=r"academy-artifact://"):
        SyntheticArtifact(
            artifact_ref="artifact://live-workspace/data.pdf",
            scenario_version="1.0.0",
        )


def test_synthetic_artifact_synthetic_flag_must_be_true():
    """SyntheticArtifact.synthetic cannot be set to False."""
    with pytest.raises((ValueError, TypeError)):
        SyntheticArtifact(
            artifact_ref="academy-artifact://lesson/1",
            scenario_version="1.0.0",
            synthetic=False,  # type: ignore
        )


@pytest.mark.asyncio
async def test_hostile_live_workspace_id_in_choices_rejected(engine: SimulationEngine):
    """Simulation rejects learner choices that contain live workspace routing IDs."""
    with pytest.raises(ValueError, match=r"live workspace|hostile"):
        await engine.start(
            "p0_discovery_v1",
            learner_id="academy_l_1",
            learner_choices={"workspace": "ws-live-production-123"},
        )


@pytest.mark.asyncio
async def test_hostile_project_id_in_choices_rejected(engine: SimulationEngine):
    """Simulation rejects learner choices containing live project IDs."""
    with pytest.raises(ValueError, match=r"live workspace|hostile"):
        await engine.start(
            "p0_discovery_v1",
            learner_id="academy_l_1",
            learner_choices={"project": "proj-my-real-project"},
        )


@pytest.mark.asyncio
async def test_evidence_id_in_choices_rejected(engine: SimulationEngine):
    """Simulation rejects learner choices containing live evidence IDs."""
    with pytest.raises(ValueError, match=r"live workspace|hostile"):
        await engine.start(
            "p0_discovery_v1",
            learner_id="academy_l_1",
            learner_choices={"evidence_source": "ev-customer-interview-001"},
        )


@pytest.mark.asyncio
async def test_random_learner_input_is_safe(engine: SimulationEngine):
    """Random text learner input (no live IDs) passes safely."""
    attempt = await engine.start(
        "p0_discovery_v1",
        learner_id="academy_l_2",
        learner_choices={
            "answer": "Khách hàng thường xuyên gặp vấn đề với quy trình thủ công",
            "follow_up": "Vấn đề này xảy ra bao nhiêu lần mỗi tuần?",
        },
    )
    assert attempt.artifact.artifact_ref.startswith(ACADEMY_ARTIFACT_SCHEME)
    assert attempt.synthetic is True


@pytest.mark.asyncio
async def test_simulation_result_contains_disclaimer(engine: SimulationEngine):
    """Every simulation result contains the standard synthetic disclaimer."""
    attempt = await engine.start("p0_discovery_v1", learner_id="academy_l_3")
    assert attempt.artifact.disclaimer != ""
    # Disclaimer must be non-trivially long (not just a placeholder)
    assert len(attempt.artifact.disclaimer) > 20
