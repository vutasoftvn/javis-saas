"""
Academy Simulation Engine

Accepts scenario fixtures and learner choices; returns deterministic/advisory scoring.

ISOLATION INVARIANTS (enforced by design):
1. SimulationEngine does NOT receive CosaAgentPlane, CompanyServiceClient,
   CapabilityGateway, connector grants, or live artifact repositories.
2. Simulation results are always marked synthetic=True.
3. Results carry a permanent disclaimer in Vietnamese.
4. Live workspace_id, project_id, evidence_id, pilot_id, metric_contract_id
   are rejected in learner input — treated as hostile text, not routing keys.
5. Scenario text is parsed as structured YAML data; never executed as agent instructions.
"""
from __future__ import annotations

import inspect
import re
import uuid
from typing import Any

from apps.cosa.academy.simulation.contracts import (
    ACADEMY_ARTIFACT_SCHEME,
    SYNTHETIC_DISCLAIMER,
    SimulationAttempt,
    SimulationFeedback,
    SyntheticArtifact,
)
from apps.cosa.academy.simulation.scenario_store import InMemoryScenarioStore


# Patterns that indicate a learner is trying to pass live routing IDs
_LIVE_ID_PATTERNS = re.compile(
    r"(?:"
    r"ws-[a-zA-Z0-9\-]+"            # workspace IDs
    r"|proj-[a-zA-Z0-9\-]+"         # project IDs
    r"|ev-[a-zA-Z0-9\-]+"           # evidence IDs
    r"|gate-[a-zA-Z0-9\-]+"         # gate evaluation IDs
    r"|pilot-[a-zA-Z0-9\-]+"        # pilot IDs
    r"|mc-[a-zA-Z0-9\-]+"           # metric contract IDs
    r")"
)


class SimulationEngine:
    """
    Deterministic simulation engine for Academy learning scenarios.

    Constructor accepts ONLY:
    - scenario_store: InMemoryScenarioStore (never CosaAgentPlane or CapabilityGateway)

    This is enforced both by type annotations and by the acceptance test that
    inspects inspect.signature(SimulationEngine).parameters.
    """

    def __init__(self, scenario_store: InMemoryScenarioStore) -> None:
        self._store = scenario_store

    async def start(
        self,
        scenario_ref: str,
        learner_id: str,
        learner_choices: dict[str, Any] | None = None,
    ) -> SimulationAttempt:
        """
        Start a simulation attempt.

        Returns a SimulationAttempt with:
        - artifact_ref starting with 'academy-artifact://'
        - synthetic=True
        - disclaimer in Vietnamese

        Raises ValueError for:
        - Unknown scenario_ref
        - learner_id not starting with 'academy_'
        - learner_choices containing live routing IDs
        """
        if not learner_id.startswith("academy_"):
            raise ValueError(
                f"learner_id must start with 'academy_' to ensure isolation; "
                f"got: {learner_id!r}"
            )

        scenario = self._store.get(scenario_ref)
        if scenario is None:
            raise ValueError(f"Scenario not found: {scenario_ref!r}")

        # Reject hostile live IDs in learner choices
        if learner_choices:
            self._reject_live_ids_in_input(learner_choices)

        attempt_id = f"sim_{uuid.uuid4().hex[:12]}"
        artifact_ref = f"{ACADEMY_ARTIFACT_SCHEME}{scenario_ref}/{attempt_id}"

        artifact = SyntheticArtifact(
            artifact_ref=artifact_ref,
            scenario_version=scenario.version,
            synthetic=True,
            disclaimer=SYNTHETIC_DISCLAIMER,
            body={
                "scenario_title": scenario.title,
                "learner_id": learner_id,
                "choices": learner_choices or {},
            },
        )

        return SimulationAttempt(
            id=attempt_id,
            learner_id=learner_id,
            scenario_ref=scenario_ref,
            scenario_version=scenario.version,
            artifact=artifact,
            synthetic=True,
        )

    async def evaluate(self, attempt: SimulationAttempt) -> SimulationFeedback:
        """
        Produce deterministic advisory scoring for a completed attempt.

        Score is a learning rubric only — NEVER a PMF score, maturity assessment,
        gate input, or metric snapshot.
        """
        scenario = self._store.get(attempt.scenario_ref)
        rubric_notes = []
        score = 0.5  # default neutral score

        if scenario and scenario.checkpoints:
            matched = sum(
                1 for cp in scenario.checkpoints
                if any(
                    kw.lower() in str(attempt.artifact.body.get("choices", {})).lower()
                    for kw in cp.expected_reasoning_keywords
                )
            )
            score = min(1.0, matched / max(len(scenario.checkpoints), 1))
            rubric_notes.append(f"Matched {matched}/{len(scenario.checkpoints)} reasoning checkpoints")

        rubric_notes.append(SYNTHETIC_DISCLAIMER)

        return SimulationFeedback(
            attempt_id=attempt.id,
            score=score,
            rubric_notes=rubric_notes,
            synthetic=True,
            disclaimer=SYNTHETIC_DISCLAIMER,
        )

    def _reject_live_ids_in_input(self, choices: dict[str, Any]) -> None:
        """Reject learner choices that appear to contain live routing IDs."""
        flat = str(choices)
        if _LIVE_ID_PATTERNS.search(flat):
            raise ValueError(
                "Simulation input contains patterns that look like live workspace/project/evidence IDs. "
                "Simulation inputs must be synthetic only. Live IDs are treated as hostile input."
            )
