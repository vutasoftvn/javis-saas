from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.verification.models import Verdict
from agent.verification.repository import InMemoryVerificationReportRepository

from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.capabilities.client import CompanyServiceError
from apps.cosa.worker import wga_run, wga_verify

pytestmark = pytest.mark.asyncio

_RUN = "wga_task_123_ab12cd34"


def _metric_criterion(cid="m1", kr="7", threshold=3, **args):
    return {
        "id": cid,
        "description": "d",
        "required": True,
        "check": "deterministic",
        "predicate": {
            "kind": "metric_gte",
            "args": {"key_result_id": kr, "threshold": threshold, **args},
        },
    }


def _dc(*criteria):
    return {"version": 1, "criteria": list(criteria)}


def _plane(client=None):
    return SimpleNamespace(
        verification_report_repository=InMemoryVerificationReportRepository(),
        artifact_repository=SimpleNamespace(list_for_conversation=AsyncMock(return_value=[])),
        run_repository=SimpleNamespace(append_event=AsyncMock()),
        company_client=client,
    )


async def _verify(plane, dc, **over):
    kwargs = dict(
        producer_spec=COSA_OPERATIONS_AGENT_SPEC,
        workspace_id="ws1",
        project_id="p1",
        task_id="123",
        task_run_id=_RUN,
        task_title="T",
        decision_reason="R",
        done_criteria=dc,
        run_result=SimpleNamespace(final_output="out", status=None, errors=[], usage={}),
        output_text="out",
    )
    kwargs.update(over)
    return await wga_verify.verify_task_result(plane, **kwargs)


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setenv("COSA_COMPANY_DELEGATION_SECRET", "x" * 40)


async def test_fetch_kr_values_maps_ids_and_marks_missing_as_none():
    # Hình dạng thật của listKeyResults: MvpSuccess = {"data": [...], "meta": {...}}
    client = SimpleNamespace(
        get=AsyncMock(
            return_value={
                "data": [{"id": "7", "currentValue": 4.5}, {"id": "8", "currentValue": None}],
                "meta": {"dataState": "populated", "observedAt": "t", "sources": []},
            }
        )
    )
    plane = SimpleNamespace(company_client=client)
    out = await wga_verify.fetch_kr_values(
        plane,
        workspace_id="ws1",
        sub="7",
        run_id="wga_task_1_ab",
        key_result_ids={"7", "8", "9"},
    )
    assert out == {"7": 4.5, "8": None, "9": None}
    call = client.get.await_args
    assert call.args[0] == "/operations/key-results"
    assert call.kwargs["headers"]["X-Workspace-Id"] == "ws1"
    assert call.kwargs["headers"]["Authorization"].startswith("Bearer ")


async def test_fetch_kr_values_never_raises_on_company_error():
    client = SimpleNamespace(get=AsyncMock(side_effect=CompanyServiceError("boom")))
    out = await wga_verify.fetch_kr_values(
        SimpleNamespace(company_client=client),
        workspace_id="ws1",
        sub="7",
        run_id="r",
        key_result_ids={"7"},
    )
    assert out == {"7": None}


async def test_fetch_kr_values_tolerates_malformed_response_and_bool_values():
    for resp in ({}, {"data": "nope"}, {"data": [None, 3, {"id": "7", "currentValue": True}]}):
        client = SimpleNamespace(get=AsyncMock(return_value=resp))
        out = await wga_verify.fetch_kr_values(
            SimpleNamespace(company_client=client),
            workspace_id="ws1",
            sub="7",
            run_id="r",
            key_result_ids=["7"],
        )
        assert out == {"7": None}


async def test_fetch_kr_values_skips_the_call_for_no_ids():
    client = SimpleNamespace(get=AsyncMock())
    out = await wga_verify.fetch_kr_values(
        SimpleNamespace(company_client=client),
        workspace_id="ws1",
        sub="7",
        run_id="r",
        key_result_ids=[],
    )
    assert out == {}
    client.get.assert_not_awaited()


async def test_metric_criteria_ids_ignores_other_kinds_and_bad_args():
    dc = {
        "version": 1,
        "criteria": [
            {
                "id": "a",
                "description": "d",
                "check": "deterministic",
                "predicate": {"kind": "metric_gte", "args": {"key_result_id": "7", "threshold": 1}},
            },
            {
                "id": "b",
                "description": "d",
                "check": "deterministic",
                "predicate": {"kind": "artifact_exists", "args": {}},
            },
            {
                "id": "c",
                "description": "d",
                "check": "deterministic",
                "predicate": {"kind": "metric_gte", "args": {"key_result_id": 9, "threshold": 1}},
            },
            {
                "id": "d",
                "description": "d",
                "check": "deterministic",
                "predicate": {"kind": "metric_gte", "args": {"key_result_id": "7", "threshold": 2}},
            },
        ],
    }
    assert wga_verify.metric_criteria_ids(dc) == ["7"]
    assert wga_verify.metric_criteria_ids({}) == []
    assert wga_verify.metric_criteria_ids({"criteria": "x"}) == []


async def test_verify_reads_metrics_only_when_a_metric_criterion_exists(monkeypatch):
    fetch = AsyncMock(return_value={"7": 4.0})
    monkeypatch.setattr(wga_verify, "fetch_kr_values", fetch)
    plane = _plane()

    no_metric = {
        "id": "c1",
        "description": "d",
        "required": True,
        "check": "deterministic",
        "predicate": {"kind": "artifact_exists", "args": {}},
    }
    await _verify(plane, _dc(no_metric))
    fetch.assert_not_awaited()

    out = await _verify(_plane(), _dc(_metric_criterion(kr="7", threshold=3)), sub="42")
    assert out.verdict is Verdict.PASS
    fetch.assert_awaited_once()
    kwargs = fetch.await_args.kwargs
    assert set(kwargs["key_result_ids"]) == {"7"}
    assert kwargs["workspace_id"] == "ws1" and kwargs["run_id"] == _RUN and kwargs["sub"] == "42"


async def test_verify_fails_below_threshold(monkeypatch):
    monkeypatch.setattr(wga_verify, "fetch_kr_values", AsyncMock(return_value={"7": 2.0}))
    out = await _verify(_plane(), _dc(_metric_criterion(kr="7", threshold=3)))
    assert out.verdict is Verdict.FAIL


async def test_verify_is_inconclusive_when_metric_unavailable(monkeypatch):
    monkeypatch.setattr(wga_verify, "fetch_kr_values", AsyncMock(return_value={"7": None}))
    out = await _verify(_plane(), _dc(_metric_criterion(kr="7", threshold=3)))
    assert out.verdict is Verdict.INCONCLUSIVE


async def test_verify_must_change_uses_metrics_before(monkeypatch):
    monkeypatch.setattr(wga_verify, "fetch_kr_values", AsyncMock(return_value={"7": 5.0}))
    dc = _dc(_metric_criterion(kr="7", threshold=3, must_change=True))

    unchanged = await _verify(_plane(), dc, metrics_before={"7": 5.0})
    assert unchanged.verdict is Verdict.FAIL

    changed = await _verify(_plane(), dc, metrics_before={"7": 1.0})
    assert changed.verdict is Verdict.PASS

    no_baseline = await _verify(_plane(), dc)
    assert no_baseline.verdict is Verdict.INCONCLUSIVE


async def test_wants_change_only_for_must_change_true_on_that_kr():
    dc = _dc(
        _metric_criterion(cid="a", kr="7", must_change=True),
        _metric_criterion(cid="b", kr="8"),
        _metric_criterion(cid="c", kr="9", must_change="yes"),
    )
    assert wga_run._wants_change(dc, "7") is True
    assert wga_run._wants_change(dc, "8") is False
    assert wga_run._wants_change(dc, "9") is False
    assert wga_run._wants_change({}, "7") is False


async def test_verify_end_to_end_through_company_client_stub():
    client = SimpleNamespace(
        get=AsyncMock(return_value={"data": [{"id": "7", "currentValue": 9}], "meta": {}})
    )
    out = await _verify(_plane(client), _dc(_metric_criterion(kr="7", threshold=3)))
    assert out.verdict is Verdict.PASS
    client.get.assert_awaited_once()
