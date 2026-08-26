from __future__ import annotations

from agent_core.evals.artifacts import EvalSuite
from agent_core.governance.contracts import PinnedSpecIdentity


def test_eval_suite_has_sensible_defaults():
    suite = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder")

    assert suite.version == "1.0.0"
    assert suite.case_ids == []
    assert suite.scorer_version == "1.0"
    assert suite.definition_hash is None


def test_eval_suite_compute_hash_is_deterministic():
    a = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c1", "c2"])
    b = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c1", "c2"])

    assert a.compute_hash() == b.compute_hash()


def test_eval_suite_compute_hash_ignores_case_ids_order():
    a = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c1", "c2"])
    b = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c2", "c1"])

    assert a.compute_hash() == b.compute_hash()


def test_eval_suite_compute_hash_changes_when_case_ids_change():
    a = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c1"])
    b = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c1", "c2"])

    assert a.compute_hash() != b.compute_hash()


def test_eval_suite_compute_hash_changes_when_scorer_version_changes():
    a = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", scorer_version="1.0")
    b = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", scorer_version="2.0")

    assert a.compute_hash() != b.compute_hash()


def test_eval_suite_with_hash_returns_a_copy_with_definition_hash_set():
    suite = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder")

    pinned = suite.with_hash()

    assert suite.definition_hash is None
    assert pinned.definition_hash == suite.compute_hash()


def test_eval_suite_to_pinned_identity_uses_eval_suite_kind():
    suite = EvalSuite(id="cofounder-core", version="24", target_kind="agent", target_id="cofounder").with_hash()

    identity = suite.to_pinned_identity()

    assert identity == PinnedSpecIdentity(
        spec_kind="eval_suite", spec_id="cofounder-core", spec_version="24", definition_hash=suite.definition_hash
    )
