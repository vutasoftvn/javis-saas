from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest
import yaml


def _load_eval_contract_module():
    try:
        return import_module("agent.skills.eval_contract")
    except ModuleNotFoundError:
        pytest.fail("Skill evaluation contract loader has not been implemented")


def _write_suite(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _valid_suite() -> dict[str, object]:
    return {
        "apiVersion": "cosa.ai/skill-eval/v1",
        "kind": "SkillEvalSuite",
        "skill": {"id": "operations.tasks", "version": "2.0.0"},
        "cases": [
            {
                "id": "accepts-governed-context",
                "input": {"workspace_id": "ws-eval", "project_id": "project-eval"},
                "expected": {"outcome": "accept"},
            },
            {
                "id": "cross-workspace",
                "input": {"workspace_id": "ws-other", "project_id": "project-eval"},
                "expected": {"outcome": "reject", "reason": "cross-workspace"},
            },
        ],
    }


def test_load_skill_eval_suite_parses_versioned_policy_contract(tmp_path: Path) -> None:
    contract = _load_eval_contract_module()

    suite = contract.load_skill_eval_suite(_write_suite(tmp_path / "suite.yaml", _valid_suite()))

    assert suite.skill_id == "operations.tasks"
    assert suite.skill_version == "2.0.0"
    assert [case.id for case in suite.cases] == ["accepts-governed-context", "cross-workspace"]
    assert suite.cases[1].expected.outcome == "reject"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda suite: suite.update(apiVersion="cosa.ai/skill-eval/v9"), "apiVersion"),
        (lambda suite: suite.update(kind="Other"), "kind"),
        (lambda suite: suite.update(cases=[]), "cases"),
        (lambda suite: suite["cases"].append(suite["cases"][0].copy()), "duplicate"),
        (lambda suite: suite["cases"][0].pop("expected"), "expected"),
        (lambda suite: suite["cases"][0]["expected"].update(outcome="unknown"), "outcome"),
    ],
)
def test_load_skill_eval_suite_rejects_invalid_contracts(
    tmp_path: Path, mutate, message: str
) -> None:
    contract = _load_eval_contract_module()
    payload = _valid_suite()
    mutate(payload)

    with pytest.raises(contract.SkillEvalContractError, match=message):
        contract.load_skill_eval_suite(_write_suite(tmp_path / "suite.yaml", payload))


def test_every_builtin_skillpack_has_a_valid_owned_eval_suite() -> None:
    contract = _load_eval_contract_module()
    repo_root = Path(__file__).resolve().parents[3]

    for manifest_path in sorted((repo_root / "skillpacks").rglob("manifest.yaml")):
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        suite = contract.load_skill_eval_suite(repo_root / manifest["quality"]["eval_suite"])
        assert suite.skill_id == manifest["metadata"]["id"]
        assert suite.skill_version == str(manifest["metadata"]["version"])
        rejected = {case.id for case in suite.cases if case.expected.outcome == "reject"}
        assert set(manifest["quality"]["required_negative_cases"]).issubset(rejected)
