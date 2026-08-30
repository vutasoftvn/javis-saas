from __future__ import annotations

import inspect
import pytest

from apps.cosa.academy.simulation.contracts import (
    ACADEMY_ARTIFACT_SCHEME,
    SimulationAttempt,
    SimulationFeedback,
    SyntheticArtifact,
)
from apps.cosa.academy.simulation.engine import SimulationEngine
from apps.cosa.academy.simulation.scenario_store import (
    InMemoryScenarioStore,
    ScenarioCheckpoint,
    SimulationScenario,
)


@pytest.fixture
def store_with_p0() -> InMemoryScenarioStore:
    store = InMemoryScenarioStore()
    store.register(
        SimulationScenario(
            ref="p0_discovery_v1",
            version="1.0.0",
            title="Khám phá Vấn đề",
            synthetic_dataset={"persona": "Co-founder B2B SaaS"},
            checkpoints=[
                ScenarioCheckpoint(
                    id="cp1",
                    prompt="Bạn sẽ đặt câu hỏi gì?",
                    expected_reasoning_keywords=["pain", "vấn đề", "hằng ngày"],
                    permitted_output_fields=["question_text", "rationale"],
                )
            ],
        )
    )
    return store


@pytest.fixture
def engine(store_with_p0: InMemoryScenarioStore) -> SimulationEngine:
    return SimulationEngine(scenario_store=store_with_p0)


@pytest.mark.asyncio
async def test_simulation_start_returns_academy_artifact(engine: SimulationEngine):
    """SimulationEngine.start() produces artifact_ref starting with 'academy-artifact://'."""
    attempt = await engine.start("p0_discovery_v1", learner_id="academy_l_1")

    assert attempt.artifact.artifact_ref.startswith(ACADEMY_ARTIFACT_SCHEME)
    assert attempt.synthetic is True
    assert "không phải evidence" in attempt.artifact.disclaimer.lower() or "synthetic" in attempt.artifact.disclaimer.lower()


@pytest.mark.asyncio
async def test_simulation_evaluate_returns_rubric_score(engine: SimulationEngine):
    """SimulationEngine.evaluate() produces a rubric score between 0.0 and 1.0, marked synthetic."""
    attempt = await engine.start(
        "p0_discovery_v1",
        learner_id="academy_l_1",
        learner_choices={"cp1": "Khách hàng thường xuyên gặp vấn đề gì hằng ngày?"},
    )
    feedback = await engine.evaluate(attempt)

    assert 0.0 <= feedback.score <= 1.0
    assert feedback.synthetic is True
    assert isinstance(feedback.rubric_notes, list) and len(feedback.rubric_notes) > 0


def test_engine_does_not_accept_capability_gateway_in_signature():
    """SimulationEngine constructor must NOT have capability_gateway in its parameters."""
    sig = inspect.signature(SimulationEngine)
    params = set(sig.parameters.keys())

    forbidden = {"capability_gateway", "agent_plane", "company_client", "connector_grant"}
    assert params.isdisjoint(forbidden), (
        f"SimulationEngine must not accept production dependency params. Found: {params & forbidden}"
    )


@pytest.mark.asyncio
async def test_learner_id_must_start_with_academy(engine: SimulationEngine):
    """Simulation rejects learner_id not prefixed with 'academy_'."""
    with pytest.raises(ValueError, match=r"academy_"):
        await engine.start("p0_discovery_v1", learner_id="user-founder-123")


@pytest.mark.asyncio
async def test_unknown_scenario_ref_raises(engine: SimulationEngine):
    """Simulation raises ValueError for unknown scenario ref."""
    with pytest.raises(ValueError, match=r"Scenario not found"):
        await engine.start("nonexistent_scenario_v99", learner_id="academy_l_1")


@pytest.mark.asyncio
async def test_simulation_with_file_based_scenarios():
    """FileScenarioStore loads real YAML fixtures and produces valid scenarios."""
    from pathlib import Path
    from apps.cosa.academy.simulation.scenario_store import FileScenarioStore

    scenarios_dir = Path(__file__).parent.parent.parent.parent.parent / "apps/cosa/academy/simulation/scenarios"
    file_store = FileScenarioStore(scenarios_dir)
    engine = SimulationEngine(scenario_store=file_store)  # type: ignore[arg-type]

    # The file store is compatible with InMemoryScenarioStore interface
    p0 = file_store.get("p0_discovery_v1")
    assert p0 is not None
    assert p0.version == "1.0.0"
    assert len(p0.checkpoints) >= 1

    p3 = file_store.get("p3_pilot_v1")
    assert p3 is not None
    assert len(p3.checkpoints) >= 2
