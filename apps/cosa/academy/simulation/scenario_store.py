"""
Academy Simulation Scenario Store

Loads scenario definitions from YAML fixture files.
Scenarios contain synthetic datasets and decision checkpoints only.

ISOLATION RULE:
- Scenario store NEVER receives live workspace sources, connector grants, or production evidence.
- Scenario text is treated as data (never executed as code or agent instruction).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ScenarioCheckpoint:
    """A decision point within a simulation scenario."""

    id: str
    prompt: str
    expected_reasoning_keywords: list[str] = field(default_factory=list)
    permitted_output_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SimulationScenario:
    """
    A versioned synthetic scenario for simulation.

    Fields:
    - version: semantic version of the scenario dataset
    - title: human-readable name
    - synthetic_dataset: curated fixture data (no live customer/financial data)
    - checkpoints: decision points requiring learner reasoning
    - disclaimer: permanent provenance notice
    """

    ref: str
    version: str
    title: str
    synthetic_dataset: dict[str, Any]
    checkpoints: list[ScenarioCheckpoint]
    disclaimer: str = (
        "Dữ liệu tình huống này là tổng hợp và được tạo ra để học tập. "
        "Không phải dữ liệu khách hàng, tài chính, hoặc vận hành thực."
    )


class InMemoryScenarioStore:
    """In-memory scenario store for testing and development."""

    def __init__(self) -> None:
        self._scenarios: dict[str, SimulationScenario] = {}

    def register(self, scenario: SimulationScenario) -> None:
        self._scenarios[scenario.ref] = scenario

    def get(self, ref: str) -> SimulationScenario | None:
        return self._scenarios.get(ref)

    def list_refs(self) -> list[str]:
        return list(self._scenarios.keys())


class FileScenarioStore:
    """
    File-based scenario store that reads YAML scenario fixtures.

    Scenario YAML must have: ref, version, title, synthetic_dataset, checkpoints.
    Any field referencing live_workspace, live_project, connector, or live_evidence
    is rejected at load time.
    """

    FORBIDDEN_FIELDS = frozenset(
        [
            "live_workspace_id",
            "live_project_id",
            "connector_grant",
            "live_evidence",
            "live_customer_data",
        ]
    )

    def __init__(self, scenarios_dir: Path) -> None:
        self._scenarios_dir = scenarios_dir
        self._cache: dict[str, SimulationScenario] = {}

    def _load(self, ref: str) -> SimulationScenario:
        path = self._scenarios_dir / f"{ref}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Scenario not found: {ref} (looked at {path})")

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

        # Reject any forbidden fields to guarantee isolation
        for forbidden in self.FORBIDDEN_FIELDS:
            if forbidden in raw:
                raise ValueError(
                    f"Scenario {ref!r} contains forbidden live-data field: {forbidden!r}. "
                    f"Scenarios must use only synthetic fixtures."
                )

        checkpoints = [
            ScenarioCheckpoint(
                id=cp["id"],
                prompt=cp["prompt"],
                expected_reasoning_keywords=cp.get("expected_reasoning_keywords", []),
                permitted_output_fields=cp.get("permitted_output_fields", []),
            )
            for cp in raw.get("checkpoints", [])
        ]

        return SimulationScenario(
            ref=raw["ref"],
            version=raw["version"],
            title=raw["title"],
            synthetic_dataset=raw.get("synthetic_dataset", {}),
            checkpoints=checkpoints,
            disclaimer=raw.get(
                "disclaimer",
                "Dữ liệu tình huống này là tổng hợp, không phải dữ liệu thực.",
            ),
        )

    def get(self, ref: str) -> SimulationScenario | None:
        if ref not in self._cache:
            try:
                self._cache[ref] = self._load(ref)
            except FileNotFoundError:
                return None
        return self._cache[ref]

    def list_refs(self) -> list[str]:
        return [p.stem for p in self._scenarios_dir.glob("*.yaml") if p.is_file()]
