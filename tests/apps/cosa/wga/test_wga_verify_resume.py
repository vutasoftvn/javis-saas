from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agent.verification import Verdict
from apps.cosa.worker import wga_run
from apps.cosa.worker.wga_verify import VerificationOutcome

pytestmark = pytest.mark.asyncio

_CTX = {
    "taskId": "123", "workspaceId": "ws1", "title": "T", "projectId": "p1",
    "autonomyClass": "NEEDS_APPROVAL", "ownerAgentProfile": "operations",
    "decisionReason": "R",
    "doneCriteria": {"version": 1, "criteria": [
        {"id": "c1", "description": "d", "required": True, "check": "rubric", "rubric": "r"}]},
}
_RUN = "wga_task_123_ab12cd34"


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
