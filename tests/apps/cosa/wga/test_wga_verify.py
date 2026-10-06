import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.verification.models import CriterionVerdict, Verdict
from agent.verification.repository import InMemoryVerificationReportRepository

from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.worker import wga_verify

pytestmark = pytest.mark.asyncio

_RUN = "wga_task_123_ab12cd34"


def _crit(cid, check="rubric", required=True, **extra):
    base = {"id": cid, "description": "d", "required": required, "check": check}
    if check == "rubric":
        base["rubric"] = "r"
    base.update(extra)
    return base


def _dc(*criteria):
    return {"version": 1, "criteria": list(criteria)}


def _plane(artifacts=()):
    return SimpleNamespace(
        verification_report_repository=InMemoryVerificationReportRepository(),
        artifact_repository=SimpleNamespace(
            list_for_conversation=AsyncMock(return_value=list(artifacts))
        ),
        run_repository=SimpleNamespace(append_event=AsyncMock()),
    )


def _run_result(final_output="out"):
    return SimpleNamespace(final_output=final_output, status=None, errors=[], usage={})


async def _verify(plane, dc, *, output_text="out", run_result=None):
    return await wga_verify.verify_task_result(
        plane,
        producer_spec=COSA_OPERATIONS_AGENT_SPEC,
        workspace_id="ws1",
        project_id="p1",
        task_id="123",
        task_run_id=_RUN,
        task_title="T",
        decision_reason="R",
        done_criteria=dc,
        run_result=run_result or _run_result(),
        output_text=output_text,
    )


def _art(kind="report", name="WGA task output", run_id=_RUN, status="available", archived=None):
    return SimpleNamespace(
        artifact_kind=kind, display_name=name, run_id=run_id, status=status, archived_at=archived
    )


_ART_EXISTS = _crit("c1", "deterministic", predicate={"kind": "artifact_exists", "args": {}})


async def test_deterministic_only_pass_does_not_call_judge(monkeypatch):
    judge = AsyncMock()
    monkeypatch.setattr(wga_verify, "run_judge", judge)
    plane = _plane([_art()])
    dc = _dc(
        _crit(
            "c1", "deterministic", predicate={"kind": "artifact_exists", "args": {"kind": "report"}}
        )
    )
    out = await _verify(plane, dc)
    assert out.verdict is Verdict.PASS and out.report_id
    judge.assert_not_awaited()
    saved = await plane.verification_report_repository.get_for_run("ws1", _RUN)
    assert saved.mode == "deterministic" and saved.verdict == "PASS"
    assert saved.report_id == out.report_id and saved.report_id.startswith("vr_")
    assert len(saved.output_hash) == 64 and len(saved.criteria_hash) == 64
    plane.artifact_repository.list_for_conversation.assert_awaited_once_with(
        "ws1", f"wga_task_{_RUN}"
    )
    event = plane.run_repository.append_event.await_args.args[0]
    assert event.event_type == "verification.completed" and event.run_id == _RUN
    assert event.payload["verdict"] == "PASS" and event.payload["report_id"] == out.report_id
    assert event.payload["mode"] == "deterministic"
    assert "out" not in json.dumps(event.payload).replace("verdict", "")


async def test_rubric_pass_and_fail_come_from_judge(monkeypatch):
    seen = {}

    async def fake_judge(plane, **kw):
        seen.update(kw)
        return wga_verify.JudgeResult(
            {"c1": (CriterionVerdict.PASS, "ok"), "c2": (CriterionVerdict.FAIL, "thiếu biện pháp")},
            f"{_RUN}__verify",
            None,
        )

    monkeypatch.setattr(wga_verify, "run_judge", fake_judge)
    plane = _plane()
    out = await _verify(plane, _dc(_crit("c1"), _crit("c2")))
    assert out.verdict is Verdict.FAIL
    assert "c2" in out.summary and len(out.summary) <= 300
    assert [c["id"] for c in seen["rubric_criteria"]] == ["c1", "c2"]
    saved = await plane.verification_report_repository.get_for_run("ws1", _RUN)
    assert saved.mode == "deterministic+judge" and saved.verifier_run_id == f"{_RUN}__verify"
    ev = plane.run_repository.append_event.await_args.args[0]
    assert ev.payload["failed"] == ["c2"] and ev.payload["unclear"] == []
    assert "thiếu biện pháp" not in json.dumps(ev.payload, ensure_ascii=False)


async def test_judge_error_makes_required_rubric_inconclusive(monkeypatch):
    async def fake_judge(plane, **kw):
        return wga_verify.JudgeResult(None, "x__verify", "judge_run_failed:usage_budget_exceeded")

    monkeypatch.setattr(wga_verify, "run_judge", fake_judge)
    out = await _verify(_plane(), _dc(_crit("c1")))
    assert out.verdict is Verdict.INCONCLUSIVE and "usage_budget_exceeded" in out.summary


async def test_optional_rubric_error_does_not_block(monkeypatch):
    async def fake_judge(plane, **kw):
        return wga_verify.JudgeResult(None, "x__verify", "judge_run_failed:x")

    monkeypatch.setattr(wga_verify, "run_judge", fake_judge)
    out = await _verify(_plane([_art()]), _dc(_ART_EXISTS, _crit("c2", required=False)))
    assert out.verdict is Verdict.PASS


@pytest.mark.parametrize("exc", [RuntimeError("boom"), ConnectionError("db"), OSError("net")])
async def test_judge_infrastructure_error_never_escapes(monkeypatch, exc):
    monkeypatch.setattr(wga_verify, "run_judge", AsyncMock(side_effect=exc))
    out = await _verify(_plane(), _dc(_crit("c1")))
    assert out.verdict is Verdict.INCONCLUSIVE
    assert out.report_id is None
    assert out.summary == f"verification_error:{type(exc).__name__}"
    assert out.results == []


async def test_invalid_criteria_is_inconclusive():
    out = await _verify(_plane(), {"version": 9})
    assert out.verdict is Verdict.INCONCLUSIVE and "criteria_invalid" in out.summary


async def test_invalid_criterion_id_is_visible_unclear_and_not_sent_to_judge(monkeypatch):
    seen = {}

    async def fake_judge(plane, **kw):
        seen.update(kw)
        return wga_verify.JudgeResult({"c1": (CriterionVerdict.PASS, "ok")}, "v", None)

    monkeypatch.setattr(wga_verify, "run_judge", fake_judge)
    bad = {"id": 5, "description": "d", "required": True, "check": "rubric", "rubric": "r"}
    monkeypatch.setattr(
        wga_verify,
        "parse_done_criteria",
        lambda raw: {"version": 1, "criteria": [_crit("c1"), bad]},
    )
    plane = _plane()
    out = await _verify(plane, _dc(_crit("c1")))
    assert [c["id"] for c in seen["rubric_criteria"]] == ["c1"]
    assert out.verdict is Verdict.INCONCLUSIVE
    invalid = [r for r in out.results if r.reason == "invalid_criterion"]
    assert len(invalid) == 1 and invalid[0].verdict is CriterionVerdict.UNCLEAR


async def test_artifact_read_failure_means_no_artifacts():
    plane = _plane()
    plane.artifact_repository.list_for_conversation = AsyncMock(side_effect=RuntimeError("db down"))
    out = await _verify(plane, _dc(_ART_EXISTS))
    assert out.verdict is Verdict.FAIL


async def test_missing_artifact_repository_means_no_artifacts():
    plane = _plane()
    del plane.artifact_repository
    out = await _verify(plane, _dc(_ART_EXISTS))
    assert out.verdict is Verdict.FAIL


async def test_artifacts_are_filtered_by_run_and_archive():
    plane = _plane([_art(run_id="other_run"), _art(archived="2026-01-01"), _art(status="archived")])
    out = await _verify(plane, _dc(_ART_EXISTS))
    assert out.verdict is Verdict.FAIL
    plane2 = _plane([_art(run_id="other_run"), _art()])
    assert (await _verify(plane2, _dc(_ART_EXISTS))).verdict is Verdict.PASS


async def test_unexpected_error_is_fail_closed(monkeypatch):
    monkeypatch.setattr(
        wga_verify, "collect_run_facts", AsyncMock(side_effect=RuntimeError("boom"))
    )
    out = await _verify(_plane(), _dc(_ART_EXISTS))
    assert out.verdict is Verdict.INCONCLUSIVE and "verification_error" in out.summary
    assert out.summary == "verification_error:RuntimeError"


async def test_structured_output_is_exposed_only_for_real_dicts():
    dc = _dc(
        _crit("c1", "deterministic", predicate={"kind": "field_present", "args": {"path": "title"}})
    )
    out_text = await _verify(_plane(), dc, run_result=_run_result({"response": "text"}))
    assert out_text.verdict is Verdict.INCONCLUSIVE
    out_struct = await _verify(_plane(), dc, run_result=_run_result({"title": "x"}))
    assert out_struct.verdict is Verdict.PASS


async def test_report_is_idempotent_per_run():
    plane = _plane([_art()])
    a = await _verify(plane, _dc(_ART_EXISTS))
    b = await _verify(plane, _dc(_ART_EXISTS))
    assert a.report_id == b.report_id


async def test_report_store_failure_keeps_verdict_but_no_report_id():
    plane = _plane([_art()])
    plane.verification_report_repository = SimpleNamespace(
        create_if_absent=AsyncMock(side_effect=RuntimeError("db"))
    )
    out = await _verify(plane, _dc(_ART_EXISTS))
    assert out.verdict is Verdict.PASS and out.report_id is None


async def test_missing_report_repository_keeps_verdict():
    plane = _plane([_art()])
    del plane.verification_report_repository
    out = await _verify(plane, _dc(_ART_EXISTS))
    assert out.verdict is Verdict.PASS and out.report_id is None


async def test_event_failure_does_not_change_verdict():
    plane = _plane([_art()])
    plane.run_repository.append_event = AsyncMock(side_effect=RuntimeError("db"))
    out = await _verify(plane, _dc(_ART_EXISTS))
    assert out.verdict is Verdict.PASS and out.report_id


async def test_flag_is_read_at_call_time(monkeypatch):
    monkeypatch.delenv("WGA_VERIFY_ON_COMPLETE", raising=False)
    assert wga_verify.verification_enabled() is False
    monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "1")
    assert wga_verify.verification_enabled() is True
    monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "true")
    assert wga_verify.verification_enabled() is False
