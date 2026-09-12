# Executive Board: Wire Real Model Execution + Thêm Role CCO — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay `ExecutiveBoardRunner.run()` từ mock/stub cứng thành gọi kernel/LLM thật (DeepSeek qua `RealOpenAIAgentsSDKKernel`), rồi trên nền đó bật role thứ 3 của Executive Advisory Board — `cco` (Chief Customer Officer) — từ `PENDING_CUSTOMER_SUPPORT_PROFILE` lên `READY`.

**Architecture:** `ExecutiveBoardRunner` nhận `kernel: ExecutionKernel` + `spec_registry: SpecRegistryRepository` qua constructor injection (thay vì tự tạo instance rỗng). Khi `req.mock_model_output` là `None`, runner tự resolve `role_pin.skill_pins` (chuỗi dạng `"skillpack:executive/<role>-advisor@<version>"`) thành `PinnedSkillRef` có hash thật qua registry, dựng 1 `AgentSpec` tạm thời (không publish) gắn `output_schema` mới, rồi gọi `kernel.run()` — kernel tự inject nội dung `SKILL.md` vào prompt và validate output theo JSON schema (cơ chế này đã có sẵn trong `RealOpenAIAgentsSDKKernel`, không cần sửa kernel). `mock_model_output` vẫn được giữ lại làm test override cho các test hiện có (không phá vỡ 4 test file đang dùng field này).

**Tech Stack:** Python 3.11+, Pydantic v2, `agents` SDK (OpenAI Agents SDK) qua LiteLLM/DeepSeek, pytest + pytest-asyncio.

## Global Constraints

- Không tự tạo Agent mới khi chưa cần (CLAUDE.md rule 3) — Executive Board dùng `AgentSpec` tạm thời trong bộ nhớ cho mỗi lần phân tích, KHÔNG đăng ký thêm agent mới vào `COSA_DEPLOYED_AGENT_SPECS`.
- Governance là code xác định, không phải LLM tự quyết (CLAUDE.md rule 5) — `autonomy_level=AutonomyLevel.L1` (Propose/Draft) bắt buộc trên mọi `AgentSpec` executive board dựng ra; không có capability_refs nào được cấp cho các spec này (rỗng).
- `definition_hash` bắt buộc khớp tuyệt đối khi resolve skill — không tự dùng "bản mới nhất" theo id (đã có sẵn trong `SkillResolver`, giữ nguyên).
- Coverage gate `packages/agent`: 80% (`make agent-test`).
- Chạy `make skillpacks-validate` sau khi thêm/sửa bất kỳ `manifest.yaml`/`SKILL.md` nào.
- Chạy `make contracts-check` sau khi sửa `shared/contracts/*.json` và regenerate.
- Comment mới viết bằng tiếng Việt cho phần giải thích lý do (why), định danh/log giữ tiếng Anh.

---

## Task 1: Thêm JSON schema cho output phân tích Executive Board

**Files:**
- Modify: `packages/agent/executive_board/models.py`
- Test: `tests/agent/executive_board/test_output_schema.py` (mới)

**Interfaces:**
- Produces: `EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA: dict[str, Any]` — dùng lại ở Task 4 (`AgentSpec.output_schema`) và validation nội bộ trong `runner.py`.

- [x] **Step 1: Viết test thất bại**

```python
# tests/agent/executive_board/test_output_schema.py
from __future__ import annotations

from agent.contracts.output import validate_output_payload
from agent.executive_board.models import EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA


def test_valid_payload_passes_schema():
    payload = {
        "conclusion": "Runway hiện tại đủ 14 tháng nếu giữ nguyên burn rate.",
        "options": [
            {"title": "Giữ nguyên chi tiêu", "trade_off": "An toàn nhưng chậm tăng trưởng"},
        ],
        "evidence_claims": [
            {"claim": "Burn rate tháng 8 là 45,000 USD", "source_ref": "object://finance/burn-aug"},
        ],
        "assumptions": ["Doanh thu không đổi"],
        "risks_and_unknowns": ["Chưa tính đến vòng gọi vốn mới"],
        "confidence": 0.8,
        "human_review_required": True,
    }
    is_valid, parsed, errors = validate_output_payload(payload, EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA)
    assert is_valid is True
    assert errors == []
    assert parsed["conclusion"] == payload["conclusion"]


def test_payload_missing_evidence_claims_fails_schema():
    payload = {
        "conclusion": "Thiếu evidence.",
        "options": [{"title": "A", "trade_off": "B"}],
    }
    is_valid, _parsed, errors = validate_output_payload(payload, EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA)
    assert is_valid is False
    assert errors
```

- [x] **Step 2: Chạy test, xác nhận fail**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/test_output_schema.py -v`
Expected: FAIL với `ImportError: cannot import name 'EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA'`

- [x] **Step 3: Thêm schema vào `models.py`**

Thêm vào cuối `packages/agent/executive_board/models.py` (giữ nguyên toàn bộ nội dung hiện có phía trên):

```python
from typing import Any

EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["conclusion", "options", "evidence_claims"],
    "properties": {
        "conclusion": {"type": "string", "minLength": 1},
        "options": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["title", "trade_off"],
                "properties": {
                    "title": {"type": "string"},
                    "trade_off": {"type": "string"},
                },
            },
        },
        "evidence_claims": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["claim", "source_ref"],
                "properties": {
                    "claim": {"type": "string"},
                    "source_ref": {"type": "string"},
                },
            },
        },
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "risks_and_unknowns": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "human_review_required": {"type": "boolean"},
    },
}
```

Lưu ý: `models.py` đã có `from typing import Any, Literal` ở dòng 3 — chỉ cần thêm hằng số này, không thêm lại import trùng.

- [x] **Step 4: Chạy test, xác nhận pass**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/test_output_schema.py -v`
Expected: PASS (2 test)

- [x] **Step 5: Commit**

```bash
git add packages/agent/executive_board/models.py tests/agent/executive_board/test_output_schema.py
git commit -m "feat(executive-board): add structured output JSON schema for advisor analysis"
```

---

## Task 2: Parser cho định dạng `skill_pins` (`"skillpack:executive/cfo-advisor@1.0.0"`)

**Files:**
- Create: `packages/agent/executive_board/skill_pins.py`
- Test: `tests/agent/executive_board/test_skill_pins.py`

**Interfaces:**
- Consumes: `agent.executive_board.models.ExecutiveBoardInputError`, `agent.registry.repository.SpecRegistryRepository`, `agent.registry.models.PublishedSpecRecord`, `agent.contracts.identity.PinnedSkillRef`.
- Produces: `parse_skill_pin_ref(ref: str) -> tuple[str, str]`, `async def resolve_role_pin_skills(skill_pins: tuple[str, ...], spec_registry: SpecRegistryRepository) -> list[PinnedSkillRef]` — dùng ở Task 4.

Xác nhận nền tảng (đã kiểm chứng trực tiếp trong code, không suy đoán): `apps/cosa/api/skillpack_mapper.py:58` lấy `skill_id = metadata.get("id") or pack_dir.name` — với `skillpacks/executive/cfo-advisor/manifest.yaml` có `metadata.id: executive.cfo-advisor`, nên skill_id thật trong registry là `"executive.cfo-advisor"` (dấu chấm), trong khi catalog `executive-advisor-roles.json` ghi `required_skill_pins: ["skillpack:executive/cfo-advisor@1.0.0"]` (dấu gạch chéo, có tiền tố `skillpack:`) — 2 định dạng khác nhau, cần hàm chuyển đổi tường minh.

- [x] **Step 1: Viết test thất bại**

```python
# tests/agent/executive_board/test_skill_pins.py
from __future__ import annotations

import pytest

from agent.executive_board.models import ExecutiveBoardInputError
from agent.executive_board.skill_pins import parse_skill_pin_ref, resolve_role_pin_skills
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import InMemorySpecRegistryRepository


def test_parse_skill_pin_ref_converts_slash_to_dot():
    skill_id, version = parse_skill_pin_ref("skillpack:executive/cfo-advisor@1.0.0")
    assert skill_id == "executive.cfo-advisor"
    assert version == "1.0.0"


def test_parse_skill_pin_ref_rejects_unknown_prefix():
    with pytest.raises(ExecutiveBoardInputError, match="UNSUPPORTED_SKILL_PIN_FORMAT"):
        parse_skill_pin_ref("executive/cfo-advisor@1.0.0")


@pytest.mark.asyncio
async def test_resolve_role_pin_skills_returns_pinned_ref_with_real_hash():
    registry = InMemorySpecRegistryRepository()
    await registry.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id="executive.cfo-advisor",
            version="1.0.0",
            definition_hash="abc123hash",
            content={"id": "executive.cfo-advisor", "version": "1.0.0", "instructions": "..."},
            publisher="cosa_built_in",
        )
    )

    refs = await resolve_role_pin_skills(("skillpack:executive/cfo-advisor@1.0.0",), registry)

    assert len(refs) == 1
    assert refs[0].skill_id == "executive.cfo-advisor"
    assert refs[0].version == "1.0.0"
    assert refs[0].definition_hash == "abc123hash"


@pytest.mark.asyncio
async def test_resolve_role_pin_skills_raises_when_not_published():
    registry = InMemorySpecRegistryRepository()
    with pytest.raises(ExecutiveBoardInputError, match="SKILL_PIN_NOT_PUBLISHED"):
        await resolve_role_pin_skills(("skillpack:executive/cco-advisor@1.0.0",), registry)
```

- [x] **Step 2: Chạy test, xác nhận fail**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/test_skill_pins.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'agent.executive_board.skill_pins'`

- [x] **Step 3: Viết implementation**

```python
# packages/agent/executive_board/skill_pins.py
from __future__ import annotations

from agent.contracts.identity import PinnedSkillRef
from agent.executive_board.models import ExecutiveBoardInputError
from agent.registry.repository import SpecRegistryRepository

__all__ = ["parse_skill_pin_ref", "resolve_role_pin_skills"]

_PREFIX = "skillpack:"


def parse_skill_pin_ref(ref: str) -> tuple[str, str]:
    """Chuyển 'skillpack:executive/cfo-advisor@1.0.0' -> ('executive.cfo-advisor', '1.0.0').

    Catalog role dùng dấu '/' cho path skillpack trên đĩa, nhưng registry publish
    skill dùng skill_id dạng dấu chấm lấy từ manifest.yaml metadata.id
    (apps/cosa/api/skillpack_mapper.py:58) — 2 quy ước khác nhau, cần convert.
    """
    if not ref.startswith(_PREFIX):
        raise ExecutiveBoardInputError(f"UNSUPPORTED_SKILL_PIN_FORMAT: {ref}")
    body = ref[len(_PREFIX):]
    path, sep, version = body.partition("@")
    if not sep or not path or not version:
        raise ExecutiveBoardInputError(f"UNSUPPORTED_SKILL_PIN_FORMAT: {ref}")
    return path.replace("/", "."), version


async def resolve_role_pin_skills(
    skill_pins: tuple[str, ...],
    spec_registry: SpecRegistryRepository,
) -> list[PinnedSkillRef]:
    """Resolve từng skill_pins string thành PinnedSkillRef có definition_hash thật
    (đọc từ registry, không tự đoán/không dùng 'bản mới nhất')."""
    refs: list[PinnedSkillRef] = []
    for raw in skill_pins:
        skill_id, version = parse_skill_pin_ref(raw)
        record = await spec_registry.get(spec_kind="skill", spec_id=skill_id, version=version)
        if record is None:
            raise ExecutiveBoardInputError(
                f"SKILL_PIN_NOT_PUBLISHED: '{skill_id}@{version}' not found in spec registry"
            )
        refs.append(
            PinnedSkillRef(skill_id=skill_id, version=version, definition_hash=record.definition_hash)
        )
    return refs
```

- [x] **Step 4: Chạy test, xác nhận pass**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/test_skill_pins.py -v`
Expected: PASS (4 test)

- [x] **Step 5: Commit**

```bash
git add packages/agent/executive_board/skill_pins.py tests/agent/executive_board/test_skill_pins.py
git commit -m "feat(executive-board): resolve skill_pins catalog refs to hash-pinned SkillRef"
```

---

## Task 3: Refactor `ExecutiveBoardRunner` — gọi kernel thật khi không có `mock_model_output`

**Files:**
- Modify: `packages/agent/executive_board/runner.py`
- Test: `tests/agent/executive_board/test_runner.py` (đã tồn tại — thêm test case mới, KHÔNG xoá test case cũ dùng `mock_model_output`)

**Interfaces:**
- Consumes: `agent.contracts.kernel.ExecutionKernel.run(request: RunRequest, spec: AgentSpec) -> RunResult`, `agent.contracts.run.RunRequest`, `agent.contracts.run.RunStatus`, `agent.contracts.spec.AgentSpec`, `agent.governance.contracts.AutonomyLevel`, `resolve_role_pin_skills` (Task 2), `EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA` (Task 1).
- Produces: `ExecutiveBoardRunner(kernel: ExecutionKernel, spec_registry: SpecRegistryRepository)` — constructor thay đổi, dùng ở Task 5.

- [x] **Step 1: Viết test thất bại cho đường gọi kernel thật**

Thêm vào cuối `tests/agent/executive_board/test_runner.py` (giữ nguyên mọi test hiện có phía trên):

```python
import json

import pytest

from agent.contracts.run import RunResult, RunStatus
from agent.executive_board.models import RolePin
from agent.executive_board.runner import ExecutiveBoardRunner
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import InMemorySpecRegistryRepository


class _StubKernel:
    def __init__(self, result: RunResult) -> None:
        self._result = result
        self.last_spec = None
        self.last_request = None

    async def run(self, request, spec):
        self.last_request = request
        self.last_spec = spec
        return self._result


@pytest.mark.asyncio
async def test_run_calls_kernel_when_no_mock_output_provided():
    registry = InMemorySpecRegistryRepository()
    await registry.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id="executive.cfo-advisor",
            version="1.0.0",
            definition_hash="hash-cfo-1",
            content={"id": "executive.cfo-advisor", "version": "1.0.0", "instructions": "..."},
            publisher="cosa_built_in",
        )
    )
    kernel_output = {
        "conclusion": "Runway đủ 12 tháng.",
        "options": [{"title": "Giữ nguyên", "trade_off": "An toàn"}],
        "evidence_claims": [{"claim": "Burn rate ổn định", "source_ref": "object://x"}],
        "confidence": 0.7,
    }
    stub = _StubKernel(
        RunResult(run_id="run-1", status=RunStatus.COMPLETED, final_output=kernel_output)
    )
    runner = ExecutiveBoardRunner(kernel=stub, spec_registry=registry)

    outcome = await make_outcome_request(
        runner,
        role_pin=RolePin(
            role_key="cfo",
            assignment_id="assign-cfo",
            spec_id="cosa.agents.finance",
            spec_version="1.1.0",
            spec_hash="fin-hash",
            skill_pins=("skillpack:executive/cfo-advisor@1.0.0",),
        ),
    )

    assert outcome.kind == "executive.analysis.completed.v1"
    assert outcome.descriptor["conclusion"] == "Runway đủ 12 tháng."
    assert stub.last_spec.pinned_skills[0].skill_id == "executive.cfo-advisor"
    assert stub.last_spec.autonomy_level.value == "L1"
    assert stub.last_request.workspace_id == "ws-1"


@pytest.mark.asyncio
async def test_run_fails_when_kernel_status_not_completed():
    registry = InMemorySpecRegistryRepository()
    await registry.publish(
        PublishedSpecRecord(
            spec_kind="skill", spec_id="executive.cfo-advisor", version="1.0.0",
            definition_hash="hash-cfo-1", content={}, publisher="cosa_built_in",
        )
    )
    stub = _StubKernel(RunResult(run_id="run-2", status=RunStatus.FAILED, errors=["boom"]))
    runner = ExecutiveBoardRunner(kernel=stub, spec_registry=registry)

    outcome = await make_outcome_request(
        runner,
        role_pin=RolePin(
            role_key="cfo", assignment_id="assign-cfo", spec_id="cosa.agents.finance",
            spec_version="1.1.0", spec_hash="fin-hash",
            skill_pins=("skillpack:executive/cfo-advisor@1.0.0",),
        ),
    )

    assert outcome.kind == "executive.analysis.failed.v1"
    assert "KERNEL_RUN_FAILED" in outcome.error_detail
```

Nếu file test hiện có chưa có helper `make_outcome_request`, thêm helper này ngay phía trên 2 test mới (giữ nguyên helper `make_request` cũ nếu có, không đổi tên nó):

```python
from agent.executive_board.models import ExecutiveAnalysisRequest


async def make_outcome_request(runner: ExecutiveBoardRunner, *, role_pin: RolePin):
    request = ExecutiveAnalysisRequest(
        workspace_id="ws-1",
        project_id="proj-1",
        deliberation_id="delib-1",
        frame_version=1,
        role_key=role_pin.role_key,
        question="Founder muốn biết tình hình runway.",
        role_pin=role_pin,
    )
    return await runner.run(request)
```

- [x] **Step 2: Chạy test, xác nhận fail**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/test_runner.py -v`
Expected: FAIL — `TypeError: ExecutiveBoardRunner() takes no arguments` (constructor cũ không nhận `kernel`/`spec_registry`)

- [x] **Step 3: Viết implementation — thay toàn bộ nội dung `runner.py`**

```python
# packages/agent/executive_board/runner.py
from __future__ import annotations

from typing import Any

from agent.contracts.kernel import ExecutionKernel
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.executive_board.models import (
    EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    ExecutiveAnalysisOutcome,
    ExecutiveAnalysisRequest,
    ExecutiveBoardInputError,
)
from agent.executive_board.skill_pins import resolve_role_pin_skills
from agent.governance.contracts import AutonomyLevel
from agent.registry.repository import SpecRegistryRepository


class ExecutiveBoardRunner:
    """Isolated runner for Executive Advisory Board analyses.
    Enforces no-peer-drafts, cross-project data fencing, and strict claim-evidence mapping.
    """

    def __init__(self, kernel: ExecutionKernel, spec_registry: SpecRegistryRepository) -> None:
        self._kernel = kernel
        self._spec_registry = spec_registry

    async def run(self, req: ExecutiveAnalysisRequest) -> ExecutiveAnalysisOutcome:
        # 1. Isolation check: Peer drafts strictly forbidden
        if req.peer_drafts is not None and len(req.peer_drafts) > 0:
            raise ExecutiveBoardInputError(
                "PEER_DRAFT_FORBIDDEN: Advisory analysis must be isolated without peer drafts"
            )

        # 2. Evidence fence: Cross-project evidence strictly forbidden
        for ref in req.evidence_refs:
            if ref.project_id is not None and ref.project_id != req.project_id:
                raise ExecutiveBoardInputError(
                    f"CROSS_PROJECT_EVIDENCE_FORBIDDEN: Evidence {ref.source_ref} belongs to project {ref.project_id}, not {req.project_id}"
                )

        # 3. Model execution: mock_model_output là test override; mặc định gọi kernel thật
        if req.mock_model_output is not None:
            output: dict[str, Any] | None = req.mock_model_output
        else:
            output = await self._run_kernel(req)
            if output is None:
                return ExecutiveAnalysisOutcome(
                    kind="executive.analysis.failed.v1",
                    deliberation_id=req.deliberation_id,
                    frame_version=req.frame_version,
                    role_key=req.role_key,
                    error_detail="KERNEL_RUN_FAILED: model execution did not produce a valid analysis",
                )

        # 4. Validate output schema & claim-to-evidence mapping
        conclusion = output.get("conclusion")
        if not conclusion or not isinstance(conclusion, str):
            return ExecutiveAnalysisOutcome(
                kind="executive.analysis.failed.v1",
                deliberation_id=req.deliberation_id,
                frame_version=req.frame_version,
                role_key=req.role_key,
                error_detail="CONCLUSION_REQUIRED: Valid conclusion string is required",
            )

        options = output.get("options")
        if not options or not isinstance(options, list) or len(options) == 0:
            return ExecutiveAnalysisOutcome(
                kind="executive.analysis.failed.v1",
                deliberation_id=req.deliberation_id,
                frame_version=req.frame_version,
                role_key=req.role_key,
                error_detail="OPTIONS_REQUIRED: Options list must contain at least one option",
            )

        claims = output.get("evidence_claims")
        if not claims or not isinstance(claims, list) or len(claims) == 0:
            return ExecutiveAnalysisOutcome(
                kind="executive.analysis.failed.v1",
                deliberation_id=req.deliberation_id,
                frame_version=req.frame_version,
                role_key=req.role_key,
                error_detail="EVIDENCE_MAPPING_REQUIRED: Every analysis must map claims to evidence",
            )

        descriptor: dict[str, Any] = {
            "role_key": req.role_key,
            "conclusion": conclusion,
            "options": options,
            "evidence_claims": claims,
            "assumptions": output.get("assumptions", []),
            "risks_and_unknowns": output.get("risks_and_unknowns", []),
            "confidence": float(output.get("confidence", 0.8)),
            "human_review_required": bool(output.get("human_review_required", True)),
            "role_pin": req.role_pin.model_dump(),
        }

        return ExecutiveAnalysisOutcome(
            kind="executive.analysis.completed.v1",
            deliberation_id=req.deliberation_id,
            frame_version=req.frame_version,
            role_key=req.role_key,
            descriptor=descriptor,
        )

    async def _run_kernel(self, req: ExecutiveAnalysisRequest) -> dict[str, Any] | None:
        pinned_skills = await resolve_role_pin_skills(req.role_pin.skill_pins, self._spec_registry)

        spec = AgentSpec(
            id=f"executive.board.{req.role_key}",
            version="1.0.0",
            instructions=(
                f"Bạn là thành viên Hội đồng Cố vấn Điều hành (Executive Advisory Board) "
                f"giữ vai trò '{req.role_key}'. Chỉ đọc và đề xuất (advisory L1_PROPOSE) — "
                f"không tự quyết định hay thực thi bất kỳ hành động nào. Trả lời bằng đúng "
                f"cấu trúc JSON được yêu cầu, không thêm văn bản ngoài JSON."
            ),
            autonomy_level=AutonomyLevel.L1,
            pinned_skills=pinned_skills,
            output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
        ).with_hash()

        evidence_text = "\n".join(
            f"- {ref.source_ref} (hash={ref.source_hash}, classification={ref.classification})"
            for ref in req.evidence_refs
        ) or "(không có evidence nào được đính kèm)"

        run_req = RunRequest(
            principal=f"executive_board:{req.role_key}",
            workspace_id=req.workspace_id,
            root_executable_ref=spec.id,
            input={"prompt": f"Câu hỏi deliberation: {req.question}\n\nEvidence:\n{evidence_text}"},
        )

        result = await self._kernel.run(run_req, spec)
        if result.status != RunStatus.COMPLETED:
            return None
        if not isinstance(result.final_output, dict):
            return None
        return result.final_output
```

- [x] **Step 4: Chạy toàn bộ test file, xác nhận pass (kể cả test cũ dùng `mock_model_output`)**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/test_runner.py -v`
Expected: PASS toàn bộ — test cũ vẫn pass vì nhánh `mock_model_output is not None` không đổi hành vi; 2 test mới pass qua `_StubKernel`.

Nếu test cũ trong file gọi `ExecutiveBoardRunner()` không tham số, sửa các dòng khởi tạo đó thành `ExecutiveBoardRunner(kernel=_StubKernel(...), spec_registry=InMemorySpecRegistryRepository())` (test cũ dùng `mock_model_output` nên `_StubKernel`/`spec_registry` không bao giờ thực sự được gọi tới, chỉ cần thoả constructor).

- [x] **Step 5: Commit**

```bash
git add packages/agent/executive_board/runner.py tests/agent/executive_board/test_runner.py
git commit -m "feat(executive-board): call real ExecutionKernel instead of hardcoded stub output"
```

---

## Task 4: Cập nhật call site trong worker handler

**Files:**
- Modify: `apps/cosa/worker/executive_board_handler.py:57`
- Test: `tests/agent/executive_board/test_handler.py` (đã tồn tại)

**Interfaces:**
- Consumes: `plane.kernel` (`ExecutionKernel`), `plane.spec_registry` (`SpecRegistryRepository`) — cả 2 đã tồn tại trên `CosaAgentPlane` (`apps/cosa/composition/agent_plane.py:107,113`).

- [x] **Step 1: Đọc test hiện có để biết nó mock gì**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/test_handler.py -v`
Expected: PASS (baseline trước khi sửa — xác nhận test hiện tại xanh trước khi đổi code).

- [x] **Step 2: Sửa dòng khởi tạo runner**

Trong `apps/cosa/worker/executive_board_handler.py`, thay dòng 57:

```python
runner = getattr(plane, "executive_board_runner", None) or ExecutiveBoardRunner()
```

thành:

```python
runner = getattr(plane, "executive_board_runner", None) or ExecutiveBoardRunner(
    kernel=plane.kernel,
    spec_registry=plane.spec_registry,
)
```

- [x] **Step 3: Chạy lại test handler, xác nhận vẫn pass**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/test_handler.py -v`
Expected: PASS. Nếu FAIL vì test mock `plane` không có thuộc tính `kernel`/`spec_registry`, thêm 2 thuộc tính đó vào fixture `plane` giả trong test (dùng `_StubKernel`/`InMemorySpecRegistryRepository` từ Task 3, hoặc `MagicMock()` nếu test này set `plane.executive_board_runner` sẵn nên nhánh `getattr(...) or ...` không rơi vào `ExecutiveBoardRunner(...)`).

- [x] **Step 4: Chạy toàn bộ test suite executive_board**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/ -v`
Expected: PASS toàn bộ.

- [x] **Step 5: Commit**

```bash
git add apps/cosa/worker/executive_board_handler.py tests/agent/executive_board/test_handler.py
git commit -m "feat(executive-board): wire real kernel/spec_registry into worker handler"
```

---

## Task 5: Test tích hợp với `FakeSDKModel` (chứng minh chạy qua kernel thật, không chỉ stub tự viết)

**Files:**
- Test: `tests/agent/executive_board/test_runner_real_kernel_integration.py` (mới)

**Interfaces:**
- Consumes: `packages/agent_testkit/fake_sdk_model.py::FakeSDKModel`, `text_response`, `apps/cosa/composition/kernel_factory.py::build_execution_kernel`.

Mục đích: Task 3 dùng `_StubKernel` tự viết (test đơn vị của riêng `runner.py`, không đụng kernel thật). Task này chứng minh code Task 3 hoạt động đúng khi chạy qua `RealOpenAIAgentsSDKKernel` thật (chỉ thay model client bằng `FakeSDKModel`, đúng pattern `tests/apps/cosa/compliance/test_run_delegation.py` đã dùng cho các luồng khác).

- [x] **Step 1: Viết test thất bại**

```python
# tests/agent/executive_board/test_runner_real_kernel_integration.py
from __future__ import annotations

import json

import pytest

from agent.executive_board.models import ExecutiveAnalysisRequest, RolePin
from agent.executive_board.runner import ExecutiveBoardRunner
from agent.registry.models import PublishedSpecRecord
from agent.registry.repository import InMemorySpecRegistryRepository
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response
from apps.cosa.composition.kernel_factory import build_execution_kernel


@pytest.mark.asyncio
async def test_runner_completes_analysis_through_real_kernel_with_fake_model():
    spec_registry = InMemorySpecRegistryRepository()
    await spec_registry.publish(
        PublishedSpecRecord(
            spec_kind="skill",
            spec_id="executive.cfo-advisor",
            version="1.0.0",
            definition_hash="hash-cfo-real",
            content={
                "id": "executive.cfo-advisor",
                "version": "1.0.0",
                "instructions": "Đóng vai CFO advisory, chỉ đề xuất, không thực thi.",
            },
            publisher="cosa_built_in",
        )
    )

    fake_output = {
        "conclusion": "Runway 10 tháng nếu không huy động thêm vốn.",
        "options": [{"title": "Cắt giảm chi phí marketing 20%", "trade_off": "Chậm tăng trưởng ngắn hạn"}],
        "evidence_claims": [{"claim": "Cash balance hiện tại", "source_ref": "object://finance/cash-2026-09"}],
        "confidence": 0.75,
    }
    model = FakeSDKModel(responses=[text_response(json.dumps(fake_output))])

    kernel, _ = build_execution_kernel(
        runtime="openai_agents",
        repository=None,
        spec_registry=spec_registry,
        capability_registry=None,
        gateway=None,
        policy_engine=None,
        company_client=None,
        model=model,
    )

    runner = ExecutiveBoardRunner(kernel=kernel, spec_registry=spec_registry)
    request = ExecutiveAnalysisRequest(
        workspace_id="ws-1",
        project_id="proj-1",
        deliberation_id="delib-1",
        frame_version=1,
        role_key="cfo",
        question="Runway hiện tại còn bao lâu?",
        role_pin=RolePin(
            role_key="cfo",
            assignment_id="assign-cfo",
            spec_id="cosa.agents.finance",
            spec_version="1.1.0",
            spec_hash="fin-hash",
            skill_pins=("skillpack:executive/cfo-advisor@1.0.0",),
        ),
    )

    outcome = await runner.run(request)

    assert outcome.kind == "executive.analysis.completed.v1"
    assert outcome.descriptor["conclusion"] == fake_output["conclusion"]
```

Ghi chú: chữ ký chính xác của `build_execution_kernel` (tham số nào bắt buộc `None` được, tham số nào cần object thật) cần đối chiếu lại với `apps/cosa/composition/kernel_factory.py` tại thời điểm code — nếu một số tham số không nhận `None` (vd. `repository`/`gateway`/`policy_engine` bắt buộc non-null), dùng `unittest.mock.MagicMock()` thay cho `None` ở đúng tham số đó và chạy lại test để xác nhận.

- [x] **Step 2: Chạy test, sửa tham số theo lỗi thực tế nếu cần**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/test_runner_real_kernel_integration.py -v`
Expected: Nếu FAIL vì thiếu tham số bắt buộc, đọc traceback, thay `None` bằng `MagicMock()` cho đúng tham số đó, chạy lại tới khi PASS.

- [x] **Step 3: Xác nhận PASS**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/test_runner_real_kernel_integration.py -v`
Expected: PASS.

- [x] **Step 4: Commit**

```bash
git add tests/agent/executive_board/test_runner_real_kernel_integration.py
git commit -m "test(executive-board): prove runner works through real kernel with FakeSDKModel"
```

---

## Task 6: Skillpack `cco-advisor`

**Files:**
- Create: `skillpacks/executive/cco-advisor/manifest.yaml`
- Create: `skillpacks/executive/cco-advisor/SKILL.md`

**Interfaces:**
- Produces: skill được `apps/cosa/agents/skillpack_seed.py::seed_builtin_skillpacks` tự động publish thành `spec_kind="skill", spec_id="executive.cco-advisor", version="1.0.0"` khi app khởi động — không cần đăng ký code thủ công nào khác (đã xác nhận cơ chế filesystem-driven qua `root.rglob("manifest.yaml")`).

- [x] **Step 1: Tạo `manifest.yaml` (theo đúng khuôn `cfo-advisor`)**

```yaml
apiVersion: agentos.ai/v1
kind: Skill
metadata:
  id: executive.cco-advisor
  name: CCO Customer Retention & Lifecycle Advisory
  version: 1.0.0
  description: Đánh giá tình trạng giữ chân khách hàng, sức khoẻ vòng đời và mẫu hình hỗ trợ khách hàng để phản biện quyết định chiến lược của Founder.
publisher:
  name: cosa
  type: official
source:
  type: local
  path: skillpacks/executive/cco-advisor
capability:
  domain: executive
  category: advisory
  intents:
  - cco advisory
  - customer retention
  - lifecycle health
  - support pattern learning
runtime:
  entrypoint: SKILL.md
  tools: []
permissions:
  required:
  - READ_LOCAL
risk:
  level: low
trust:
  tier: T0
applicability:
  project_stages:
  - P0_DISCOVERY
  - P1_PROBLEM_VALIDATION
  - P2_SOLUTION_VALIDATION
  - P3_BUILD_VALIDATE
  - P4_GO_TO_MARKET
  - P5_OPERATE_GROWTH
  - P6_SCALE_GOVERN
  gates:
  - G0
  - G1
  - G2
  - G3
  - G4
  - G5
  - G6
  required_context:
  - workspace
  - project
  outputs:
  - proposal
  - artifact
autonomy:
  ceiling: L1_PROPOSE
  side_effect_class: A
evidence:
  min_source_refs: 1
  self_validation_forbidden: true
quality:
  eval_suite: evals/executive/board_cases.yaml
  required_negative_cases:
  - missing-workspace
  - cross-workspace
  - peer-draft-forbidden
```

- [x] **Step 2: Tạo `SKILL.md`**

```markdown
---
name: executive-cco-advisor
description: Hướng dẫn phân tích tình trạng giữ chân khách hàng và sức khoẻ vòng đời cho CCO Advisor trong Hội đồng Cố vấn Điều hành.
---

# Vai Trò CCO Advisor trong Hội Đồng Cố Vấn Điều Hành

## 1. Mục Tiêu (Objective)
Cung cấp góc nhìn phản biện về mức độ giữ chân khách hàng (retention), sức khoẻ vòng đời khách hàng, và mẫu hình lặp lại trong yêu cầu hỗ trợ, đối với các đề xuất chiến lược của Founder.

## 2. Quy Tắc Phân Tích
1. **Dựa trên dữ liệu hỗ trợ/retention thực**: Đối chiếu với ticket hỗ trợ, tỷ lệ churn, và phản hồi khách hàng đã ghi nhận — không suy diễn từ cảm tính.
2. **Phân biệt vấn đề gốc vs triệu chứng**: Một mẫu hình ticket lặp lại thường là triệu chứng của vấn đề sản phẩm/vận hành sâu hơn — chỉ ra vấn đề gốc khi có đủ bằng chứng.
3. **Cấm side-effects**: Chỉ khuyến nghị và đánh giá, không tự ý phản hồi khách hàng hoặc thay đổi chính sách hỗ trợ.
```

- [x] **Step 3: Chạy validate skillpack**

Run: `make skillpacks-validate`
Expected: PASS — không có violation nào cho `skillpacks/executive/cco-advisor`.

- [x] **Step 4: Commit**

```bash
git add skillpacks/executive/cco-advisor/
git commit -m "feat(executive-board): add cco-advisor skillpack content"
```

---

## Task 7: Bật readiness cho `customer_support` profile và role `cco`

**Files:**
- Modify: `shared/contracts/startup-team-profiles.json`
- Modify: `shared/contracts/executive-advisor-roles.json`
- Regenerate: các file `.generated.ts`/`.generated.py` tương ứng (qua script generator có sẵn — KHÔNG sửa tay)

**Interfaces:**
- Không có interface Python/TS mới — đây là thay đổi dữ liệu cấu hình + chạy lại generator.

- [x] **Step 1: Tìm script generator**

Run: `grep -rn "startup-team-profiles.json\|executive-advisor-roles.json" package.json Makefile scripts/ 2>/dev/null`
Expected: tìm ra đúng lệnh generate (nghi vấn `scripts/gen-executive-advisor-roles.mjs` theo phát hiện khảo sát trước, và 1 script tương tự cho `startup-team-profiles.json` — xác nhận tên chính xác trước khi chạy).

- [x] **Step 2: Sửa `shared/contracts/startup-team-profiles.json`**

Đổi entry `customer_support`:
```json
{"key": "customer_support", "label": "Customer Support", "defaultMode": "TEMPLATE", "runtimeReadiness": "READY"}
```
(từ `"runtimeReadiness": "PENDING_PROJECT_KNOWLEDGE"`)

- [x] **Step 3: Sửa `shared/contracts/executive-advisor-roles.json`**

Đổi entry `cco`, field `runtimeReadiness` (hoặc `runtime_readiness` tuỳ key thật trong JSON — xác nhận đúng tên field khi mở file) từ `"PENDING_CUSTOMER_SUPPORT_PROFILE"` thành `"READY"`.

- [x] **Step 4: Chạy generator tìm được ở Step 1, rồi chạy contracts-check**

Run: lệnh generate tìm được ở Step 1, sau đó `make contracts-check`
Expected: PASS — `.generated.ts`/`.generated.py` khớp với JSON nguồn, không có drift.

- [x] **Step 5: Chạy test service liên quan**

Run: `cd services/company && npx vitest run operations/tests/executive-role-activation.service.test.ts operations/tests/project-startup-team.service.test.ts operations/tests/executive-deliberation.service.test.ts`
Expected: PASS toàn bộ (test hiện có không giả định `customer_support`/`cco` ở trạng thái PENDING nên không nên bị ảnh hưởng; nếu có test khẳng định `cco` đang `PENDING_CUSTOMER_SUPPORT_PROFILE`, cập nhật assertion đó thành `READY` — đây là hệ quả trực tiếp, mong đợi của thay đổi).

- [x] **Step 6: Commit**

```bash
git add shared/contracts/startup-team-profiles.json shared/contracts/executive-advisor-roles.json \
  services/company/shared/contracts/startup-team-profiles.generated.ts \
  services/company/shared/contracts/executive-advisor-roles.generated.ts \
  apps/cosa/agents/startup_team_profiles_generated.py \
  apps/cosa/agents/executive_advisor_roles_generated.py
git commit -m "feat(executive-board): flip customer_support profile and cco role to READY"
```

---

## Task 8: Test end-to-end cho role `cco` (mirror đúng test pattern của `cfo`)

**Files:**
- Modify: `services/company/operations/tests/executive-role-activation.service.test.ts`
- Modify: `services/company/operations/tests/executive-deliberation.service.test.ts`

**Interfaces:**
- Consumes: `activateProjectStartupTeamMember`, `activateExecutiveRole`, `getProjectExecutiveRoleStates`, `frameDeliberation` — đã tồn tại, không đổi signature.

- [x] **Step 1: Thêm test activation cho `cco` (mirror test `cfo` đã có)**

Thêm vào `executive-role-activation.service.test.ts`, ngay sau test `"activates CFO when Finance is ACTIVE, and enforces CAS versioning"`:

```ts
it("activates CCO when Customer Support is ACTIVE, and enforces CAS versioning", async () => {
  await activateProjectStartupTeamMember(founderCtx, projectId, "customer_support", { expectedVersion: 1 });
  const statesBefore = await getProjectExecutiveRoleStates(founderCtx, projectId);
  const ccoBefore = statesBefore.roles.find((r) => r.roleKey === "cco");
  expect(ccoBefore?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");
  const activated = await activateExecutiveRole(founderCtx, projectId, "cco", {
    expectedVersion: ccoBefore!.version,
    idempotencyKey: "act-cco-1",
  });
  expect(activated.state).toBe("ACTIVE");
});

it("refuses CCO when Customer Support assignment is not ACTIVE", async () => {
  const statesBefore = await getProjectExecutiveRoleStates(founderCtx, projectId);
  const ccoBefore = statesBefore.roles.find((r) => r.roleKey === "cco");
  await expect(
    activateExecutiveRole(founderCtx, projectId, "cco", {
      expectedVersion: ccoBefore!.version,
      idempotencyKey: "act-cco-2",
    })
  ).rejects.toThrow(/EXECUTIVE_ROLE_NOT_AVAILABLE/);
});
```

- [x] **Step 2: Chạy test, xác nhận pass**

Run: `cd services/company && npx vitest run operations/tests/executive-role-activation.service.test.ts`
Expected: PASS.

- [x] **Step 3: Thêm test deliberation framing cho `cco` (mirror test `cfo`/`cmo`)**

Thêm vào `executive-deliberation.service.test.ts`, mở rộng `beforeEach` để activate thêm `customer_support`/`cco` (giữ nguyên activation `finance`/`cfo`, `marketing`/`cmo` đã có), rồi thêm test:

```ts
it("frames cco alongside cfo and atomically writes the outbox", async () => {
  const frame = await frameDeliberation(founderCtx, projectId, {
    roleKeys: ["cfo", "cco"],
    question: "Có nên tăng giá gói Pro không?",
  });
  expect(frame.selectedRoles.map((r: { roleKey: string }) => r.roleKey).sort()).toEqual(["cco", "cfo"]);
});
```

- [x] **Step 4: Chạy test, xác nhận pass**

Run: `cd services/company && npx vitest run operations/tests/executive-deliberation.service.test.ts`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add services/company/operations/tests/executive-role-activation.service.test.ts \
  services/company/operations/tests/executive-deliberation.service.test.ts
git commit -m "test(executive-board): cover cco role activation and deliberation framing"
```

---

## Task 9: Điều tra gap "operations" cho `coo`/`chief_of_staff` (investigation task)

**Files:** không sửa code ở task này — chỉ điều tra và ghi lại kết luận trong 1 file ghi chú tạm để dùng cho plan kế tiếp.

- [x] **Step 1: Kiểm tra `founder_assistant` có alias sang `"operations"` profile key hay không**

Run: `grep -n "\"operations\"\|'operations'" shared/contracts/startup-team-profiles.json services/company/operations/services/ai-member.service.ts`
Expected output cần đọc kỹ: xác nhận `AGENT_PROFILE_SPEC_ID` có entry `operations: "cosa.agents.operations"` (đã biết từ khảo sát trước) NHƯNG `startup-team-profiles.json` không có key `"operations"` nào — nghĩa là `OwnerAgentProfile` (TS type dùng cho `ai-member.service.ts`) rộng hơn `StartupTeamProfileKey` (TS type dùng cho `startup-team-profiles.json`).

- [x] **Step 2: Tìm định nghĩa `OwnerAgentProfile` để xác nhận `"operations"` có phải giá trị hợp lệ độc lập, không qua `STARTUP_TEAM_PROFILES`**

Run: `grep -rn "type OwnerAgentProfile\|OwnerAgentProfile =" services/company/`
Expected: xác định `OwnerAgentProfile` có liệt kê `"operations"` như 1 giá trị riêng, độc lập với danh sách 9 profile trong `startup-team-profiles.json` — nếu đúng vậy, kết luận: **không phải lệch tên/bug, mà `"operations"` là 1 owner-profile khác kênh**, được activate qua đường khác (không qua `activateProjectStartupTeamMember`/`STARTUP_TEAM_PROFILES`).

- [x] **Step 3: Nếu Step 2 xác nhận có kênh activate riêng cho `"operations"`, tìm kênh đó**

Run: `grep -rn "\"operations\"" services/company/operations/services/*.ts | grep -v test`
Expected: tìm ra hàm/đường dẫn nào set `project_agent_assignments` với `profileKey: "operations"` — nếu KHÔNG tìm thấy hàm nào, kết luận: đây là gap thật (role `coo`/`chief_of_staff` phụ thuộc 1 profile chưa từng được activate bằng bất kỳ đường nào) — cần 1 plan riêng để bổ sung con đường activate cho `"operations"` profile trước khi `coo`/`chief_of_staff` có thể `READY`.

- [x] **Step 4: Ghi kết luận**

Viết kết luận (2-3 câu, dựa trên bằng chứng Step 1-3) vào đầu Task tiếp theo trong plan kế tiếp (Giai đoạn 2 hoặc phần mở rộng Executive Board) — không cần file riêng, chỉ cần câu kết luận rõ ràng để plan sau không phải điều tra lại.

---

## Kiểm chứng tổng thể sau khi hoàn thành cả 9 task

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/ -v
make agent-test
make skillpacks-validate
make contracts-check
cd services/company && npx vitest run operations/tests/executive-role-activation.service.test.ts operations/tests/executive-deliberation.service.test.ts operations/tests/project-startup-team.service.test.ts
```

Tất cả phải PASS trước khi báo "xong" giai đoạn này.
