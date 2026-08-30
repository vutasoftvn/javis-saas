"""
Academy Simulation Contracts

All types produced by the simulation engine are permanently marked as synthetic.
These types MUST NOT be used as inputs to:
- Evidence ingestion or recording
- Gate evaluation
- Metric snapshots
- Stage transitions
- Pilot runs
- Capability enablements
- Task creation in live workspaces
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ACADEMY_ARTIFACT_SCHEME = "academy-artifact://"
SYNTHETIC_DISCLAIMER = (
    "Đây là nội dung tổng hợp từ mô phỏng học thuật COSA Academy. "
    "KHÔNG phải evidence sản xuất. Không được sử dụng làm bằng chứng trong dự án thực."
)


@dataclass(frozen=True)
class SyntheticArtifact:
    """
    An artifact produced by the simulation engine.

    INVARIANTS:
    - artifact_ref MUST start with 'academy-artifact://'
    - synthetic is always True
    - disclaimer is always a non-empty string
    - scenario_version identifies which synthetic dataset was used
    """
    artifact_ref: str          # must start with 'academy-artifact://'
    scenario_version: str
    synthetic: bool = True
    disclaimer: str = SYNTHETIC_DISCLAIMER
    body: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.artifact_ref.startswith(ACADEMY_ARTIFACT_SCHEME):
            raise ValueError(
                f"SyntheticArtifact.artifact_ref must start with 'academy-artifact://', "
                f"got: {self.artifact_ref!r}"
            )
        if not self.synthetic:
            raise ValueError("SyntheticArtifact.synthetic must always be True")
        if not self.disclaimer.strip():
            raise ValueError("SyntheticArtifact.disclaimer must not be empty")


@dataclass(frozen=True)
class SimulationAttempt:
    """
    A learner's attempt at a simulation scenario.

    INVARIANTS:
    - learner_id must start with 'academy_' (e.g. 'academy_l_1')
    - No live workspace_id, project_id, evidence_id, or connector_grant allowed
    - artifact_ref starts with 'academy-artifact://'
    """
    id: str
    learner_id: str
    scenario_ref: str
    scenario_version: str
    artifact: SyntheticArtifact
    synthetic: bool = True

    def __post_init__(self) -> None:
        if not self.learner_id.startswith("academy_"):
            raise ValueError(
                f"SimulationAttempt.learner_id must start with 'academy_', got: {self.learner_id!r}"
            )
        if not self.synthetic:
            raise ValueError("SimulationAttempt.synthetic must always be True")


@dataclass(frozen=True)
class SimulationFeedback:
    """
    Advisory scoring produced by the simulation engine.

    INVARIANTS:
    - synthetic is always True
    - score is a learning rubric score — NOT a PMF, maturity, or gate score
    - No capability_enablement or stage_transition is triggered
    """
    attempt_id: str
    score: float           # 0.0–1.0 learning rubric
    rubric_notes: list[str]
    synthetic: bool = True
    disclaimer: str = SYNTHETIC_DISCLAIMER

    def __post_init__(self) -> None:
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"SimulationFeedback.score must be between 0.0 and 1.0, got: {self.score}")
        if not self.synthetic:
            raise ValueError("SimulationFeedback.synthetic must always be True")
