from __future__ import annotations

from agent.workflows import (
    LoopDoctor,
    LoopTerminalState,
    StepType,
    WorkflowSpec,
    WorkflowStepSpec,
)


def test_loop_terminal_state_enum_values():
    assert LoopTerminalState.SUCCESS == "SUCCESS"
    assert LoopTerminalState.NOOP == "NOOP"
    assert LoopTerminalState.BLOCKED == "BLOCKED"
    assert LoopTerminalState.NEED_APPROVAL == "NEED_APPROVAL"
    assert LoopTerminalState.EXHAUSTED == "EXHAUSTED"
    assert LoopTerminalState.STAGNATED == "STAGNATED"


def test_loop_doctor_audits_clean_workflow():
    spec = WorkflowSpec(
        id="clean-loop-wf",
        name="Clean Loop Workflow",
        steps=[
            WorkflowStepSpec(
                id="observe_step",
                name="Observe State",
                type=StepType.DETERMINISTIC,
            ),
            WorkflowStepSpec(
                id="act_step",
                name="Perform Bounded Action",
                type=StepType.DETERMINISTIC,
                depends_on=["observe_step"],
                verifier_step_id="verify_step",
            ),
            WorkflowStepSpec(
                id="verify_step",
                name="Independent Verification",
                type=StepType.DETERMINISTIC,
                depends_on=["act_step"],
                terminal_state=LoopTerminalState.SUCCESS,
            ),
        ],
    )

    report = LoopDoctor.audit_workflow_spec(spec)
    assert report.workflow_id == "clean-loop-wf"
    assert report.has_bounded_feedback is True
    assert report.has_independent_verifier is True
    assert "SUCCESS" in report.terminal_states_declared
    assert report.verdict == "CLEAN"


def test_loop_doctor_detects_self_grading_anti_pattern():
    spec = WorkflowSpec(
        id="bad-self-grading-wf",
        name="Self Grading Workflow",
        steps=[
            WorkflowStepSpec(
                id="step1",
                name="Do and Self Grade",
                type=StepType.DETERMINISTIC,
                verifier_step_id="step1",  # Anti-pattern: Self-grading!
            )
        ],
    )

    report = LoopDoctor.audit_workflow_spec(spec)
    assert report.verdict == "CRITICAL_RISK"
    assert any("Self-Grading" in ap for ap in report.anti_patterns_found)


def test_loop_doctor_audits_prompt_anti_patterns():
    # Bad prompt with self-wakeup and no stopping condition
    bad_prompt = "Hãy quét dữ liệu, sau khi xong tự gọi lại chính mình sau 5 phút để chạy tiếp mãi mãi."
    audit_bad = LoopDoctor.audit_prompt_text(bad_prompt)
    assert audit_bad["is_safe"] is False
    assert len(audit_bad["issues"]) >= 2

    # Good bounded prompt
    good_prompt = "Kiểm tra danh sách tác vụ quá hạn. Cập nhật trạng thái và dừng khi không còn tác vụ nào. Dừng lại xin phép trước khi xóa dữ liệu."
    audit_good = LoopDoctor.audit_prompt_text(good_prompt)
    assert audit_good["is_safe"] is True
