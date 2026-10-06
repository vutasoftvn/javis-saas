import json
import re
from types import SimpleNamespace

import pytest
from agent.runs.models import RunStatus

from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.models.resolver import ModelRouteNotFound
from apps.cosa.worker import wga_verify
from apps.cosa.worker.run_core import RunCoreError

pytestmark = pytest.mark.asyncio

_RUBRIC = [{"id": "c1", "description": "d", "required": True, "check": "rubric", "rubric": "r"}]
_TASK_RUN = "wga_task_123_ab12cd34"


def _args(**over):
    base = dict(
        producer_spec=COSA_OPERATIONS_AGENT_SPEC,
        workspace_id="ws1",
        project_id="p1",
        task_run_id=_TASK_RUN,
        task_title="T",
        decision_reason="R",
        rubric_criteria=_RUBRIC,
        output_text="out",
    )
    base.update(over)
    return base


def _result(text, status=RunStatus.COMPLETED):
    return SimpleNamespace(
        status=status,
        final_output={"response": text} if text is not None else None,
        errors=[],
        usage={},
    )


@pytest.fixture
def stub_core(monkeypatch):
    calls = {"prepare": [], "run": []}

    async def fake_prepare(plane, **kw):
        calls["prepare"].append(kw)
        return SimpleNamespace(spec=kw["local_spec"])

    outputs = []

    async def fake_run(plane, prep, *, workspace_id, run_id):
        calls["run"].append(run_id)
        out = outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out, 0.1

    monkeypatch.setattr(wga_verify, "prepare_run", fake_prepare)
    monkeypatch.setattr(wga_verify, "run_kernel", fake_run)
    return SimpleNamespace(calls=calls, outputs=outputs)


def _ok(verdict="pass", reason="ok"):
    return _result(json.dumps({"results": [{"id": "c1", "verdict": verdict, "reason": reason}]}))


async def test_judge_success_uses_verifier_spec_and_producer_compliance(stub_core):
    stub_core.outputs.append(_ok())
    res = await wga_verify.run_judge(SimpleNamespace(), **_args())
    assert res.error is None and res.verdicts["c1"][1] == "ok"
    kw = stub_core.calls["prepare"][0]
    assert kw["local_spec"].id == "cosa.agents.verifier"
    assert kw["compliance_spec"].id == COSA_OPERATIONS_AGENT_SPEC.id
    assert list(kw["compliance_spec"].capability_refs) == []
    assert kw["run_id"] == "wga_task_123_ab12cd34__verify" and len(kw["run_id"]) <= 64
    assert kw["conversation_id"] == "wga_verify_wga_task_123_ab12cd34"
    assert len(kw["conversation_id"]) <= 64
    assert kw["project_id"] == "p1"
    assert kw["principal"] == "system:wga:ws1" and kw["policy_snapshot"] is None
    assert res.verifier_run_id == "wga_task_123_ab12cd34__verify"


async def test_verifier_run_ids_never_match_wga_task_run_pattern(stub_core):
    from apps.cosa.worker.wga_run import _WGA_TASK_RUN_RE

    stub_core.outputs += [_result("nope"), _ok()]
    await wga_verify.run_judge(SimpleNamespace(), **_args())
    assert len(stub_core.calls["run"]) == 2
    for rid in stub_core.calls["run"]:
        assert _WGA_TASK_RUN_RE.match(rid) is None
        assert len(rid) <= 64
    assert re.match(r"^wga_task_(\d+)_[0-9a-f]+$", _TASK_RUN)


async def test_judge_retries_once_on_bad_json(stub_core):
    stub_core.outputs += [_result("not json"), _ok("fail", "x")]
    res = await wga_verify.run_judge(SimpleNamespace(), **_args())
    assert res.verdicts["c1"][0].value == "fail"
    assert len(stub_core.calls["run"]) == 2
    assert stub_core.calls["run"][1].endswith("__verify_retry1")


async def test_judge_gives_up_after_two_bad_outputs(stub_core):
    stub_core.outputs += [_result("nope"), _result("still nope")]
    res = await wga_verify.run_judge(SimpleNamespace(), **_args())
    assert res.verdicts is None and "judge_output_invalid" in res.error


async def test_judge_never_raises_on_budget_errors(stub_core):
    stub_core.outputs.append(RunCoreError("usage_budget_exceeded"))
    res = await wga_verify.run_judge(SimpleNamespace(), **_args())
    assert res.verdicts is None and "usage_budget_exceeded" in res.error


async def test_judge_never_raises_on_route_not_found(stub_core):
    stub_core.outputs.append(ModelRouteNotFound("no route"))
    res = await wga_verify.run_judge(SimpleNamespace(), **_args())
    assert res.verdicts is None and "ModelRouteNotFound" in res.error


async def test_judge_failed_run_is_an_error_not_a_verdict(stub_core):
    stub_core.outputs.append(_result(None, status=RunStatus.FAILED))
    res = await wga_verify.run_judge(SimpleNamespace(), **_args())
    assert res.verdicts is None and res.error.startswith("judge_run_failed:")


async def test_judge_prepare_failure_is_an_error(monkeypatch):
    async def boom(plane, **kw):
        raise RunCoreError("compliance_denied", compliance_code="x")

    monkeypatch.setattr(wga_verify, "prepare_run", boom)
    res = await wga_verify.run_judge(SimpleNamespace(), **_args())
    assert res.verdicts is None and "compliance_denied" in res.error


async def test_judge_marks_run_read_only(stub_core):
    from apps.cosa.policies.evaluator import READ_ONLY_RUN_KEY

    stub_core.outputs.append(_ok())
    await wga_verify.run_judge(SimpleNamespace(), **_args())
    assert stub_core.calls["prepare"][0]["extra_metadata"][READ_ONLY_RUN_KEY] is True


async def test_model_route_falls_back_to_system_default_for_verifier_spec():
    from apps.cosa.models.contracts import ProviderType, SystemDefaultModelProfile
    from apps.cosa.models.repository import InMemoryModelRoutingRepository
    from apps.cosa.models.resolver import ModelRouteResolver

    sd = SystemDefaultModelProfile(
        profile_id="system-default",
        provider_type=ProviderType.LOCAL_OPENAI_COMPATIBLE,
        model_id="local-general-model",
        credential_ref=None,
        allowed_models=("local-general-model",),
    )
    resolver = ModelRouteResolver(InMemoryModelRoutingRepository(), sd)
    route = await resolver.resolve_route("ws-no-policy", "cosa.agents.verifier")
    assert route.profile_id == "system-default"


async def test_compliance_spec_keeps_model_input_capability(stub_core):
    stub_core.outputs.append(_ok())
    await wga_verify.run_judge(SimpleNamespace(), **_args())
    cs = stub_core.calls["prepare"][0]["compliance_spec"]
    assert list(cs.capability_refs) == [] and cs.model_input_capability_ref

    stub_core.outputs.append(_ok())
    bare = COSA_OPERATIONS_AGENT_SPEC.model_copy(update={"model_input_capability_ref": None})
    await wga_verify.run_judge(SimpleNamespace(), **_args(producer_spec=bare))
    cs2 = stub_core.calls["prepare"][1]["compliance_spec"]
    assert cs2.model_input_capability_ref


async def test_malformed_criteria_do_not_crash_expected_ids(stub_core):
    stub_core.outputs.append(_ok())
    crit = [*_RUBRIC, {"description": "no id"}, {"id": 7}, "junk", {"id": "  "}]
    res = await wga_verify.run_judge(SimpleNamespace(), **_args(rubric_criteria=crit))
    assert res.error is None and list(res.verdicts) == ["c1"]
