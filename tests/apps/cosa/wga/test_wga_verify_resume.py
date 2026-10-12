from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.verification import Verdict

from apps.cosa.worker import wga_run
from apps.cosa.worker.wga_verify import VerificationOutcome

pytestmark = pytest.mark.asyncio

_CTX = {
    "taskId": "123",
    "workspaceId": "ws1",
    "title": "T",
    "projectId": "p1",
    "autonomyClass": "NEEDS_APPROVAL",
    "ownerAgentProfile": "operations",
    "decisionReason": "R",
    "doneCriteria": {
        "version": 1,
        "criteria": [
            {"id": "c1", "description": "d", "required": True, "check": "rubric", "rubric": "r"}
        ],
    },
}
_RUN = "wga_task_123_ab12cd34"
_REAL_FETCH = wga_run.fetch_task_agent_context


@pytest.fixture
def stubs(monkeypatch):
    s = SimpleNamespace(
        ctx=AsyncMock(return_value=dict(_CTX)),
        verify=AsyncMock(),
        evidence=AsyncMock(return_value=["artifact:a1", f"run:{_RUN}"]),
        advance=AsyncMock(return_value=True),
        finalize=AsyncMock(return_value=True),
    )
    monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "1")
    monkeypatch.setattr(wga_run, "fetch_task_agent_context", s.ctx)
    monkeypatch.setattr(wga_run, "verify_task_result", s.verify)
    monkeypatch.setattr(wga_run, "record_wga_task_evidence", s.evidence)
    monkeypatch.setattr(wga_run, "_advance_task", s.advance)
    monkeypatch.setattr(wga_run, "finalize_wga_task_completion", s.finalize)
    return s


async def _go(**over):
    kw = dict(run_id=_RUN, workspace_id="ws1", sub="7", output_text="kết quả")
    kw.update(over)
    await wga_run.advance_wga_task_after_resume(SimpleNamespace(), **kw)


async def test_pass_closes_with_verification_evidence(stubs):
    stubs.verify.return_value = VerificationOutcome(Verdict.PASS, "vr_1", "ok", [])
    await _go()
    kw = stubs.finalize.await_args.kwargs
    assert "verification:vr_1" in kw["evidence_refs"]


async def test_fail_keeps_in_progress_and_never_finalizes(stubs):
    stubs.verify.return_value = VerificationOutcome(Verdict.FAIL, "vr_1", "0/1 c1(fail)", [])
    await _go()
    stubs.finalize.assert_not_awaited()
    kw = stubs.advance.await_args.kwargs
    assert kw["to_status"] == "in_progress" and kw["note"].startswith("verification_fail")


async def test_inconclusive_keeps_in_progress(stubs):
    stubs.verify.return_value = VerificationOutcome(Verdict.INCONCLUSIVE, None, "judge_timeout", [])
    await _go()
    stubs.finalize.assert_not_awaited()
    assert stubs.advance.await_args.kwargs["note"].startswith("verification_inconclusive")


async def test_context_unavailable_is_fail_closed_when_flag_on(stubs):
    stubs.ctx.return_value = None
    await _go()
    stubs.finalize.assert_not_awaited()
    assert "context_unavailable" in stubs.advance.await_args.kwargs["note"]


async def test_flag_off_keeps_legacy_behaviour_and_skips_context_fetch(stubs, monkeypatch):
    monkeypatch.delenv("WGA_VERIFY_ON_COMPLETE")
    await _go()
    stubs.ctx.assert_not_awaited()
    stubs.verify.assert_not_awaited()
    stubs.finalize.assert_awaited_once()


async def test_no_criteria_means_no_verification(stubs):
    stubs.ctx.return_value = {**_CTX, "doneCriteria": None}
    await _go()
    stubs.verify.assert_not_awaited()
    stubs.finalize.assert_awaited_once()


async def test_structured_final_output_reaches_the_verifier(stubs):
    stubs.verify.return_value = VerificationOutcome(Verdict.PASS, "vr_1", "ok", [])
    await _go(final_output={"summary": "x"})
    assert stubs.verify.await_args.kwargs["run_result"].final_output == {"summary": "x"}


async def test_non_wga_run_id_is_a_noop(stubs):
    await _go(run_id="chat_run_1")
    stubs.ctx.assert_not_awaited()
    stubs.finalize.assert_not_awaited()


@pytest.mark.parametrize("verdict", [Verdict.PASS, Verdict.FAIL])
async def test_advance_token_is_minted_after_verification(stubs, monkeypatch, verdict):
    order: list[str] = []

    async def _verify(*_a, **_k):
        order.append("verify")
        return VerificationOutcome(verdict, "vr_1", "s", [])

    def _mint(**kw):
        order.append("mint")
        return f"tok{len(order)}"

    stubs.verify.side_effect = _verify
    monkeypatch.setattr(wga_run, "mint_company_delegation", _mint)
    await _go()
    # mint đầu thuộc fetch_task_agent_context (đã stub nên không có); chỉ còn mint cho advance, sau verify.
    assert order == ["verify", "mint"]
    target = stubs.finalize if verdict is Verdict.PASS else stubs.advance
    assert target.await_args.kwargs["token"] == "tok2"


async def test_context_fetch_exception_is_fail_closed(monkeypatch):
    monkeypatch.setenv("COSA_COMPANY_DELEGATION_SECRET", "x" * 40)
    client = SimpleNamespace(get=AsyncMock(side_effect=ValueError("not json")))
    out = await wga_run.fetch_task_agent_context(
        SimpleNamespace(company_client=client),
        workspace_id="ws1",
        task_id="123",
        sub="7",
        run_id=_RUN,
    )
    assert out is None


async def test_token_mint_failure_is_fail_closed(monkeypatch):
    def _boom(**_kw):
        raise RuntimeError("no secret")

    monkeypatch.setattr(wga_run, "mint_company_delegation", _boom)
    client = SimpleNamespace(get=AsyncMock())
    out = await wga_run.fetch_task_agent_context(
        SimpleNamespace(company_client=client),
        workspace_id="ws1",
        task_id="123",
        sub="7",
        run_id=_RUN,
    )
    assert out is None
    client.get.assert_not_awaited()


async def test_non_company_exception_lands_in_progress_with_context_unavailable(stubs, monkeypatch):
    monkeypatch.setenv("COSA_COMPANY_DELEGATION_SECRET", "x" * 40)
    # Dùng fetch_task_agent_context THẬT (bỏ stub của fixture).
    monkeypatch.setattr(wga_run, "fetch_task_agent_context", _REAL_FETCH)
    client = SimpleNamespace(get=AsyncMock(side_effect=ValueError("not json")))
    await wga_run.advance_wga_task_after_resume(
        SimpleNamespace(company_client=client),
        run_id=_RUN,
        workspace_id="ws1",
        sub="7",
        output_text="x",
    )
    stubs.finalize.assert_not_awaited()
    kw = stubs.advance.await_args.kwargs
    assert kw["to_status"] == "in_progress" and "context_unavailable" in kw["note"]


async def test_empty_owner_profile_falls_back_to_operations(stubs):
    stubs.ctx.return_value = {**_CTX, "ownerAgentProfile": ""}
    stubs.verify.return_value = VerificationOutcome(Verdict.PASS, "vr_1", "ok", [])
    await _go()
    stubs.verify.assert_awaited_once()
    stubs.finalize.assert_awaited_once()


async def test_missing_owner_profile_falls_back_to_operations(stubs):
    ctx = {k: v for k, v in _CTX.items() if k != "ownerAgentProfile"}
    stubs.ctx.return_value = ctx
    stubs.verify.return_value = VerificationOutcome(Verdict.PASS, "vr_1", "ok", [])
    await _go()
    stubs.verify.assert_awaited_once()


async def test_unknown_owner_profile_is_inconclusive_and_never_finalizes(stubs):
    stubs.ctx.return_value = {**_CTX, "ownerAgentProfile": "no_such_profile"}
    await _go()
    stubs.verify.assert_not_awaited()
    stubs.finalize.assert_not_awaited()
    note = stubs.advance.await_args.kwargs["note"]
    assert stubs.advance.await_args.kwargs["to_status"] == "in_progress"
    assert "unsupported_owner_agent_profile" in note


async def test_resume_sub_reaches_fetch_kr_values(stubs, monkeypatch):
    """Ca KR trên đường resume: `sub` (actor_id của người duyệt) phải tới fetch_kr_values."""
    from agent.verification.repository import InMemoryVerificationReportRepository

    from apps.cosa.worker import wga_verify

    monkeypatch.setattr(wga_run, "verify_task_result", wga_verify.verify_task_result)
    fetch = AsyncMock(return_value={"7": 5.0})
    monkeypatch.setattr(wga_verify, "fetch_kr_values", fetch)
    stubs.ctx.return_value = {
        **_CTX,
        "doneCriteria": {
            "version": 1,
            "criteria": [
                {
                    "id": "m1",
                    "description": "d",
                    "required": True,
                    "check": "deterministic",
                    "predicate": {
                        "kind": "metric_gte",
                        "args": {"key_result_id": "7", "threshold": 3},
                    },
                }
            ],
        },
    }
    plane = SimpleNamespace(
        verification_report_repository=InMemoryVerificationReportRepository(),
        artifact_repository=SimpleNamespace(list_for_conversation=AsyncMock(return_value=[])),
        run_repository=SimpleNamespace(append_event=AsyncMock()),
    )
    await wga_run.advance_wga_task_after_resume(
        plane, run_id=_RUN, workspace_id="ws1", sub="42", output_text="x"
    )
    assert fetch.await_args.kwargs["sub"] == "42"
