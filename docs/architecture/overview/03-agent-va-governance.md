# Agent Platform & Governance — chi tiết kỹ thuật

> Dành cho engineer làm việc với agent runtime. Bối cảnh nghiệp vụ (vì sao
> cần governance) xem mục 6 trong
> [02-workflow-nghiep-vu.md](02-workflow-nghiep-vu.md). Bản đồ tổng của
> `packages/agent`/`apps/cosa` xem mục 4 trong
> [01-bon-vung-kien-truc.md](01-bon-vung-kien-truc.md).

## AgentSpec: authoring hardcode, resolution qua registry

`AgentSpec` được định nghĩa một lần tại `packages/agent/contracts/spec.py`
(Pydantic model, bắt buộc có `definition_hash`).

**Authoring** (viết đặc tả agent) vẫn là hardcode: `apps/cosa/agents/specs.py`
khai báo các AgentSpec của COSA bằng hằng số Python
(`COSA_OPERATIONS_AGENT_SPEC`, `COSA_FINANCE_AGENT_SPEC`...), gom vào
`COSA_DEPLOYED_AGENT_SPECS`.

**Resolution** (lấy đặc tả agent lúc chạy) đã qua registry:
`apps/cosa/agents/seed.py::seed_cosa_agent_specs()` publish các spec hardcode
này vào `SpecRegistryRepository` (`packages/agent/registry/`). Khi chạy
thật, code KHÔNG import trực tiếp hằng số Python nữa — `worker/handlers.py`
dùng `SpecResolver(repository=plane.spec_registry)`, còn
`worker/autopilot_run.py`/`copilot_run.py` dùng
`agents/registry_loader.py::load_registered_agent_spec()` để lấy theo
`(agent, spec_id, version)`.

**Vì sao cần biết điều này:** đây là trạng thái **hybrid** — không phải
"chưa làm gì" và cũng chưa phải "hoàn toàn theo registry, sửa qua UI/DB
không cần deploy code". Muốn thêm/sửa một AgentSpec hiện tại vẫn cần sửa
code + chạy lại seed, không có UI quản trị runtime cho việc này (đúng như
`ADR-AGENT-REG-001` mô tả: 3 agent hardcode cho launch, đăng ký runtime là
việc hậu-launch).

## Capability Layer & Governance/Approval

Nguyên tắc bắt buộc #5 trong `CLAUDE.md`: "Governance là code xác định,
không phải LLM tự quyết." Đây là code thật, không chỉ là thiết kế:

- `packages/agent/capabilities/approval_service.py` — class `ApprovalService`
  thay thế cách tra cứu cũ theo `(run_id, action)` bằng ràng buộc bắt buộc
  `(run_id, tool_call_id, checkpoint_ref)`:
  - `create_approval_request(run_id, tool_call_id, checkpoint_ref, ...)` —
    sinh `approval_id = f"appr_{run_id}_{tool_call_id}"`.
  - `get_by_invocation(run_id, tool_call_id, checkpoint_ref)` và
    `verify_and_prepare_resume(run_id, tool_call_id, checkpoint_ref)` — xác
    minh đúng khớp cả 3 trường trước khi cho resume.
- 3 trường này là field kiểu tường minh trên `RunApprovalRecord`
  (`packages/agent/runs/models.py`), có migration SQL thật đứng sau
  (`004_harden_exact_invocation_and_approval.sql`,
  `005_idempotency_claims.sql`).
- Risk gating khác: `packages/agent/governance/budget_gate.py`,
  `governance/floor.py` — được `apps/cosa/agents/specs.py` và
  `apps/cosa/composition/context_assembler.py` tiêu thụ.

**Vì sao đáng tin:** một constraint lịch sử (một action đã từng bị đánh dấu
`REQUIRE_APPROVAL`) không tự động biến mất khi policy sau nới lỏng, vì
approval bind theo `checkpoint_ref` cụ thể chứ không lookup theo tên hành
động — đúng nguyên tắc bắt buộc #5.

## Kernel & model runtime

- **OpenAI Agents SDK** là kernel chính:
  `packages/agent/kernel/openai_agents_kernel.py`
  (`ManualToolLoopKernel`/`KernelRunState`).
- **DeepSeek** là model provider chính, qua **LiteLLM**:
  - Adapter thấp tầng: `packages/agent_integrations/litellm/gateway.py`
    (`LiteLLMModelClient`).
  - Wiring thật dùng trong production: `apps/cosa/composition/model_provider.py`
    (`build_deepseek_model()`).
- **LangChain** là adapter tuỳ chọn (`packages/agent_integrations/langchain/`),
  không phải runtime chính.
- Các integration khác (LangGraph, Google ADK, Pydantic AI, giao thức
  A2A/AG-UI/MCP) tồn tại như package riêng dưới `packages/agent_integrations/`,
  mỗi cái có `pyproject.toml` riêng — dùng khi cần tương thích hệ sinh thái
  ngoài, không phải đường chạy mặc định.
- `packages/agent_testkit/` cung cấp bộ "conformance test" chạy cùng một bộ
  test hợp đồng cho mọi kernel/integration, kể cả một test sống thật với
  DeepSeek (`test_openai_agents_sdk_kernel_deepseek_live.py`).

## Trạng thái nhà nước (state) — cấu trúc, không suy diễn từ text

Nguyên tắc bắt buộc #7: không dùng kiểu `if "blocked" in model_text`. Phần
lớn codebase tuân thủ — enum tường minh xuất hiện rộng rãi:
`AutonomyLevel`, `RunStatus` (`packages/agent/contracts/run.py`), cùng các
enum trong `workflows/models.py`, `memory/models.py`, `skills/contracts.py`,
`vault/lifecycle.py`, và một file enum sinh tự động
(`contracts/enums_generated.py`).

**Một ngoại lệ đã phát hiện** (xem thêm
[05-khuyen-nghi.md](05-khuyen-nghi.md#nhom-b)):
`apps/cosa/events/trigger_promotion.py:41-42`:

```python
stale = any("stale" in issue.lower() for issue in gate.blocking_issues)
return GateResult(False, "stale_evidence" if stale else "checks_failed")
```

Đây là string-match trên nội dung `blocking_issues` thay vì dùng reason code
có kiểu — vi phạm nhỏ nguyên tắc #7, nên sửa thành enum/typed reason.

## `skillpacks/` — quan hệ với `packages/agent`

`skillpacks/` (114 skill, 20 domain) là **nội dung** (prompt + manifest),
không phải code runtime — được `packages/agent/skills/registry.py` và
`resolver.py` nạp vào để agent biết mình có những skill nào và dùng ra sao.
Vẫn viết bằng tiếng Anh theo quy ước riêng (không áp dụng rule ngôn ngữ
tiếng Việt của `CLAUDE.md`, vì đây là "canonical prompt của agent runtime").
