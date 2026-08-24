"""Wave 5-6 — Skill Optimization Lab (Blueprint V2 §69.3), kích hoạt cùng
ADR-SKILL-IDENTITY §4 (2026-08-24). Test chạy qua ExecutionKernel THẬT
(OpenAIAgentsKernel + InMemoryRunRepository), không mock riêng cho lab — verify
đúng đường thực thi canonical, mutator/scorer tiêm từ ngoài (không hardcode LLM
call cụ thể trong hạ tầng lõi)."""
from __future__ import annotations

import pytest

from agent_core.contracts.spec import AgentSpec
from agent_core.kernel.openai_agents_kernel import OpenAIAgentsKernel
from agent_core.runs.repository import InMemoryRunRepository
from agent_core.skills.contracts import SkillSpec
from agent_core.skills.lab import EvalCase, SkillCandidateExecutor, SkillOptimizationLab


class _KeywordAwareModelClient:
    """Mock model client trả output khác nhau tuỳ system prompt có chứa
    'ALWAYS_CITE_SOURCES' hay không — mô phỏng việc skill instructions thực sự
    thay đổi hành vi model, để test vòng lặp optimize() có ý nghĩa."""

    class _Completions:
        async def create(self, model="deepseek-chat", messages=None, temperature=0.0, **kwargs):
            system_content = messages[0]["content"] if messages else ""

            class _Msg:
                tool_calls: list = []

                def __init__(self, content: str) -> None:
                    self.content = content

            class _Choice:
                def __init__(self, content: str) -> None:
                    self.message = _Msg(content)

            class _Resp:
                usage = None

                def __init__(self, content: str) -> None:
                    self.choices = [_Choice(content)]

            if "ALWAYS_CITE_SOURCES" in system_content:
                return _Resp("Phân tích đối thủ kèm Nguồn: [Báo cáo ngành 2026]")
            return _Resp("Phân tích đối thủ, không có trích dẫn.")

    @property
    def chat(self):
        class _Chat:
            completions = _KeywordAwareModelClient._Completions()

        return _Chat()


def _make_executor() -> SkillCandidateExecutor:
    repo = InMemoryRunRepository()
    kernel = OpenAIAgentsKernel(repository=repo, model_client=_KeywordAwareModelClient())
    base_agent_spec = AgentSpec(
        id="test.agent.lab_base", version="1.0.0", instructions="Bạn là chuyên viên phân tích thị trường."
    )
    return SkillCandidateExecutor(kernel=kernel, base_agent_spec=base_agent_spec)


def _cases() -> list[EvalCase]:
    return [
        EvalCase(input_payload={"prompt": "Phân tích đối thủ Acme"}, expected_outcome={"contains": "Nguồn"}),
        EvalCase(
            input_payload={"prompt": "Phân tích đối thủ Beta"},
            expected_outcome={"contains": "Nguồn"},
            is_holdout=True,
        ),
    ]


@pytest.mark.asyncio
async def test_lab_accepts_mutation_that_improves_score():
    executor = _make_executor()

    def add_citation_mutator(skill: SkillSpec):
        mutated = skill.model_copy(update={"instructions": "ALWAYS_CITE_SOURCES: luôn trích nguồn công khai."})
        return mutated, "Thêm yêu cầu trích nguồn vào skill instructions"

    lab = SkillOptimizationLab(executor=executor, mutation_fn=add_citation_mutator, max_rounds=2)
    base_skill = SkillSpec(id="test.skill.lab_citation", version="1.0.0", instructions="")

    record = await lab.optimize(base_skill, _cases())

    assert record.baseline_score == 0.0  # chưa có citation -> case fail (holdout không tính vào baseline)
    assert record.latest_score == 1.0  # full regression bao gồm holdout -> vẫn pass vì mutation thật sự cải thiện
    assert record.status == "evaluated"
    assert "ALWAYS_CITE_SOURCES" in record.proposed_content["instructions"]

    mutations = lab.list_mutations(record.candidate_id)
    assert len(mutations) == 2
    assert mutations[0].accepted is True
    assert mutations[0].pre_score == 0.0
    assert mutations[0].post_score == 1.0
    # Round 2 áp lại cùng mutator lên skill đã có citation -> không tăng thêm điểm -> reject
    assert mutations[1].accepted is False


@pytest.mark.asyncio
async def test_lab_reverts_mutation_that_does_not_improve_and_keeps_baseline():
    executor = _make_executor()

    def useless_mutator(skill: SkillSpec):
        mutated = skill.model_copy(update={"instructions": "Một chỉ dẫn không liên quan gì tới trích nguồn."})
        return mutated, "Mutation không liên quan tới tiêu chí chấm điểm"

    lab = SkillOptimizationLab(executor=executor, mutation_fn=useless_mutator, max_rounds=1)
    base_skill = SkillSpec(id="test.skill.lab_useless", version="1.0.0", instructions="")

    record = await lab.optimize(base_skill, _cases())

    assert record.baseline_score == 0.0
    assert record.latest_score == 0.0  # mutation không cải thiện -> revert, giữ baseline
    mutations = lab.list_mutations(record.candidate_id)
    assert mutations[0].accepted is False
    # proposed_content phải giữ nguyên skill GỐC (rỗng), không phải bản mutate bị reject
    assert record.proposed_content["instructions"] == ""


@pytest.mark.asyncio
async def test_lab_rejects_invalid_max_rounds():
    executor = _make_executor()
    with pytest.raises(ValueError, match="max_rounds"):
        SkillOptimizationLab(executor=executor, max_rounds=0)
