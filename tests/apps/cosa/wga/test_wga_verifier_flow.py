"""Luồng đầu-cuối của Verifier: sweep -> claim -> chạy -> xác minh doneCriteria -> advance.

Dùng orchestrator thật `verify_task_result`, kho báo cáo InMemory và plane giả (không cần DB);
chỉ stub `run_judge` (phần gọi LLM)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.contracts.run import RunStatus
from agent.verification.models import CriterionVerdict
from agent.verification.repository import InMemoryVerificationReportRepository

from apps.cosa.worker import wga_run, wga_verify
from apps.cosa.worker.wga_verify import JudgeResult

pytestmark = pytest.mark.asyncio

_SECRET_RUBRIC = "RUBRIC_TEXT_SECRET"
_SECRET_OUTPUT = "OUTPUT_TEXT_SECRET"
_SECRET_REASON = "JUDGE_FREE_TEXT_SECRET"


def _run_result(status, final_output="", errors=None):
    return SimpleNamespace(
        status=status, final_output=final_output, errors=errors or [], interruptions_waits=[]
    )


def _rubric(cid):
    return {
        "id": cid,
        "description": "Nội dung đạt yêu cầu",
        "check": "rubric",
        "required": True,
        "rubric": _SECRET_RUBRIC,
    }


def _artifact_crit(cid):
    return {
        "id": cid,
        "description": "Có file xuất",
        "check": "deterministic",
        "required": True,
        "predicate": {"kind": "artifact_exists", "args": {"kind": "file_export"}},
    }


def _task(task_id, criteria=None):
    t = {
        "taskId": task_id,
        "autonomyClass": "AUTO",
        "ownerAgentProfile": "operations",
        "expectedCapability": "operations.task.list",
        "title": f"Task {task_id}",
        "decisionReason": "cleanup",
        "planItemId": f"i_{task_id}",
        "projectId": "proj1",
    }
    if criteria is not None:
        t["doneCriteria"] = {"version": 1, "criteria": criteria}
    return t


def _plane(company, tasks_output=_SECRET_OUTPUT):
    kernel = AsyncMock()
    kernel.run.return_value = _run_result(RunStatus.COMPLETED, {"response": tasks_output})
    resolver = AsyncMock()
    resolver.resolve_for_run.return_value = {"_company_delegation_token": "jwt-x"}

    async def _list_for_conversation(workspace_id, conversation_id):
        # conversation = "wga_task_<run_id>"; chỉ task A có artifact do công cụ tạo ra.
        run_id = conversation_id.removeprefix("wga_task_")
        if run_id.startswith("wga_task_tA_"):
            return [
                SimpleNamespace(
                    artifact_kind="file_export",
                    display_name="export.csv",
                    run_id=run_id,
                    status="available",
                    archived_at=None,
                    object_ref="artifact://tool/created/1",
                )
            ]
        return []

    return SimpleNamespace(
        company_client=company,
        kernel=kernel,
        compliance_resolver=resolver,
        spec_registry=SimpleNamespace(),
        conversation_repository=AsyncMock(),
        artifact_repository=SimpleNamespace(
            create=AsyncMock(), list_for_conversation=_list_for_conversation
        ),
        scheduler=AsyncMock(),
        verification_report_repository=InMemoryVerificationReportRepository(),
        run_repository=SimpleNamespace(append_event=AsyncMock()),
    )


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    async def _fake_resolve_spec(plane, *, run_id, local_spec):
        return SimpleNamespace(
            to_pinned_identity=lambda: "cosa.agents.operations@1.2.0#h",
            spec_id="cosa.agents.operations",
        )

    monkeypatch.setattr("apps.cosa.worker.run_core.resolve_spec", _fake_resolve_spec)
    monkeypatch.setenv("COSA_COMPANY_DELEGATION_SECRET", "x" * 40)
    monkeypatch.delenv("WGA_VERIFY_ON_COMPLETE", raising=False)


def _install_judge(monkeypatch, behaviour):
    """behaviour: dict task_id -> 'pass' | 'fail' | 'raise'. Trả danh sách run_id đã gọi judge."""
    calls: list[str] = []

    async def _fake_judge(plane, **kw):
        run_id = kw["task_run_id"]
        calls.append(run_id)
        task_id = run_id.split("_")[2]
        mode = behaviour[task_id]
        if mode == "raise":
            raise RuntimeError("judge infra down")
        verdict = CriterionVerdict.PASS if mode == "pass" else CriterionVerdict.FAIL
        verdicts = {
            c["id"]: (verdict, _SECRET_REASON) for c in kw["rubric_criteria"] if c.get("id")
        }
        return JudgeResult(verdicts, f"{run_id}__verify", None)

    monkeypatch.setattr(wga_verify, "run_judge", _fake_judge)
    return calls


def _advances(company):
    """task_id -> list of (toStatus, body)."""
    out: dict[str, list[dict]] = {}
    for c in company.post.await_args_list:
        url = c.args[0]
        if url.startswith("/operations/tasks/") and url.endswith("/advance"):
            out.setdefault(url.split("/")[3], []).append(c.kwargs["json"])
    return out


def _events(plane):
    return [
        c.args[0]
        for c in plane.run_repository.append_event.await_args_list
        if c.args[0].event_type == "verification.completed"
    ]


async def _sweep(plane, run_id="wga_sweep_v"):
    await wga_run.execute_workspace_task_sweep_task(
        plane, None, {"run_id": run_id, "workspace_id": "ws1", "actor_id": "42"}
    )


async def test_flow_three_tasks_pass_fail_and_no_criteria(monkeypatch):
    monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "1")
    judge_calls = _install_judge(monkeypatch, {"tA": "pass", "tB": "fail"})
    company = AsyncMock()
    company.get.return_value = {
        "tasks": [
            _task("tA", [_artifact_crit("ca1"), _rubric("ca2")]),
            _task("tB", [_rubric("cb1")]),
            _task("tC"),
        ]
    }
    company.post.return_value = {"status": "ok"}
    plane = _plane(company)

    await _sweep(plane)  # không ném => sweep không bị ngắt

    adv = _advances(company)
    assert [b["toStatus"] for b in adv["tA"]] == ["in_progress", "done"]
    assert [b["toStatus"] for b in adv["tB"]] == ["in_progress", "in_progress"]
    assert [b["toStatus"] for b in adv["tC"]] == ["in_progress", "done"]
    assert len(judge_calls) == 2  # chỉ A và B có rubric; C không có doneCriteria

    reports = plane.verification_report_repository
    ra = await reports.list_for_task("ws1", "tA")
    rb = await reports.list_for_task("ws1", "tB")
    assert await reports.list_for_task("ws1", "tC") == []
    assert [r.verdict for r in ra] == ["PASS"] and [r.verdict for r in rb] == ["FAIL"]
    assert ra[0].mode == "deterministic+judge"

    # A: evidence có tham chiếu báo cáo.
    done_a = adv["tA"][1]
    assert f"verification:{ra[0].report_id}" in done_a["evidenceRefs"]
    assert any(ref.startswith("artifact:") for ref in done_a["evidenceRefs"])
    # C: như trước, không có evidence verification.
    assert not any(r.startswith("verification:") for r in adv["tC"][1]["evidenceRefs"])
    # B: không bao giờ 'done'; note chỉ mã, không lộ lời giải thích tự do của thẩm phán.
    assert all(b["toStatus"] != "done" for b in adv["tB"])
    note_b = adv["tB"][1]["note"]
    assert note_b.startswith("verification_fail:")
    assert _SECRET_REASON not in note_b and "cb1(fail)" in note_b

    events = _events(plane)
    assert len(events) == 2
    by_run = {e.run_id: e for e in events}
    assert by_run[ra[0].run_id].payload["verdict"] == "PASS"
    assert by_run[rb[0].run_id].payload["verdict"] == "FAIL"
    assert by_run[rb[0].run_id].payload["report_id"] == rb[0].report_id
    assert by_run[rb[0].run_id].payload["failed"] == ["cb1"]
    for e in events:
        assert set(e.payload) == {"verdict", "report_id", "mode", "failed", "unclear"}
        dumped = str(e.payload)
        for secret in (_SECRET_OUTPUT, _SECRET_RUBRIC, _SECRET_REASON):
            assert secret not in dumped


async def test_second_sweep_over_same_run_ids_does_not_duplicate_reports(monkeypatch):
    monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "1")
    _install_judge(monkeypatch, {"tA": "pass", "tB": "fail"})
    counter = {"n": 0}

    class _FakeUuid:
        @staticmethod
        def uuid4():
            counter["n"] += 1
            return SimpleNamespace(hex=f"{counter['n']:032x}")

    monkeypatch.setattr(wga_run, "uuid", _FakeUuid)
    company = AsyncMock()
    company.get.return_value = {
        "tasks": [_task("tA", [_artifact_crit("ca1"), _rubric("ca2")]), _task("tB", [_rubric("cb1")])]
    }
    company.post.return_value = {"status": "ok"}
    plane = _plane(company)

    await _sweep(plane)
    first = {
        t: [r.report_id for r in await plane.verification_report_repository.list_for_task("ws1", t)]
        for t in ("tA", "tB")
    }
    counter["n"] = 0  # cùng run id ở lượt sweep thứ hai
    await _sweep(plane)
    second = {
        t: [r.report_id for r in await plane.verification_report_repository.list_for_task("ws1", t)]
        for t in ("tA", "tB")
    }
    assert first == second and all(len(v) == 1 for v in second.values())


async def test_judge_infra_error_is_inconclusive_and_never_done(monkeypatch):
    monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "1")
    _install_judge(monkeypatch, {"tD": "raise"})
    company = AsyncMock()
    company.get.return_value = {"tasks": [_task("tD", [_rubric("cd1")])]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company)

    await _sweep(plane)

    adv = _advances(company)
    assert [b["toStatus"] for b in adv["tD"]] == ["in_progress", "in_progress"]
    assert adv["tD"][1]["note"].startswith("verification_inconclusive:")
    assert "evidenceRefs" not in adv["tD"][1]


async def test_flag_off_skips_verification_and_closes_as_before(monkeypatch):
    calls = _install_judge(monkeypatch, {"tA": "fail", "tB": "fail", "tD": "raise"})
    verify = AsyncMock()
    monkeypatch.setattr(wga_run, "verify_task_result", verify)
    company = AsyncMock()
    company.get.return_value = {
        "tasks": [
            _task("tA", [_artifact_crit("ca1"), _rubric("ca2")]),
            _task("tB", [_rubric("cb1")]),
            _task("tD", [_rubric("cd1")]),
        ]
    }
    company.post.return_value = {"status": "ok"}
    plane = _plane(company)

    await _sweep(plane)

    verify.assert_not_awaited()
    assert calls == []
    adv = _advances(company)
    for tid in ("tA", "tB", "tD"):
        assert [b["toStatus"] for b in adv[tid]] == ["in_progress", "done"]
        assert not any(r.startswith("verification:") for r in adv[tid][1]["evidenceRefs"])
    assert await plane.verification_report_repository.list_for_task("ws1", "tA") == []
    assert _events(plane) == []


async def test_report_store_failure_keeps_task_in_progress(monkeypatch):
    monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "1")
    _install_judge(monkeypatch, {"tA": "pass"})
    company = AsyncMock()
    company.get.return_value = {"tasks": [_task("tA", [_artifact_crit("ca1"), _rubric("ca2")])]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company)
    plane.verification_report_repository = SimpleNamespace(
        create_if_absent=AsyncMock(side_effect=RuntimeError("db"))
    )

    await _sweep(plane)

    adv = _advances(company)
    assert [b["toStatus"] for b in adv["tA"]] == ["in_progress", "in_progress"]
    assert adv["tA"][1]["note"] == "verification_inconclusive: report_store_failed"


async def test_delegation_token_is_reminted_after_verification(monkeypatch):
    monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "1")
    _install_judge(monkeypatch, {"tA": "pass"})
    minted: list[str] = []

    def _mint(**kw):
        minted.append(f"tok{len(minted)}")
        return minted[-1]

    monkeypatch.setattr(wga_run, "mint_company_delegation", _mint)
    company = AsyncMock()
    company.get.return_value = {"tasks": [_task("tA", [_rubric("ca1")])]}
    company.post.return_value = {"status": "ok"}
    plane = _plane(company)

    await _sweep(plane)

    # list token, claim token, token cấp lại sau xác minh
    assert minted == ["tok0", "tok1", "tok2"]
    auth = [
        c.kwargs["headers"]["Authorization"]
        for c in company.post.await_args_list
        if c.args[0].endswith("/advance")
    ]
    assert auth == ["Bearer tok1", "Bearer tok2"]
