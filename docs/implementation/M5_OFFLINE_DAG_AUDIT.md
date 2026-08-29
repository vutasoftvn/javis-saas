# M5 — Audit: tái dùng WorkflowEngine cho offline DAG

**Ngày:** 2026-08-26
**Nguồn:** Wave M5 (`docs/superpowers/plans/2026-08-26-marin-patterns-m5-offline-dag-caching.md`), theo
`COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md` §10.1/§19 Wave M5 "Điều kiện trước khi
tạo runner mới: Phải chứng minh workflow/recipe engine hiện có không đáp ứng được."

## Kết luận

**`packages/agent/workflows/engine.py::WorkflowEngine` ĐÃ ĐỦ năng lực cho offline eval/build DAG.
KHÔNG tạo `StepRunner`/scheduler mới.**

## Bằng chứng (đọc trực tiếp code, không suy đoán)

| Năng lực cần | Có trong WorkflowEngine? | Bằng chứng |
|---|---|---|
| Dependency-aware execution (DAG, không phải linear) | ✅ Có | `engine.py::_execute_dag()` — tính `ready_step_ids` dựa trên `s.depends_on` đã hoàn thành (dòng 213-219) |
| Parallel branch execution | ✅ Có | `engine.py:229` — `asyncio.gather(*(run_single_step(sid) for sid in ready_step_ids))`, chạy song song toàn bộ step "ready" trong 1 wave |
| Checkpoint | ✅ Có | `Workflow.checkpoints: dict[str, Any]` (models.py:66), ghi sau mỗi step hoàn thành (engine.py:270) |
| Compensation khi fail | ✅ Có | `WorkflowStepSpec.on_failure` + `engine.py:251-262` chạy compensating step tương ứng |
| Custom step injection theo step id | ✅ Có | `execute_spec(..., custom_step_builders: dict[str, Callable[[WorkflowStepSpec], WorkflowStep]])` (engine.py:172-176), `build_steps_from_spec()` ưu tiên `custom_step_builders[step_spec.id]` nếu có (engine.py:122-124) |
| Artifact-aware caching (cache theo fingerprint) | ❌ Không có | Không có logic skip step nào trong `_execute_dag()` — mọi step luôn chạy |
| Dry-run graph inspection | ❌ Không có (không cần cho phạm vi Wave M5 — không có use case cụ thể yêu cầu) | — |

## Quyết định

Chỉ cần bổ sung **1 lớp adapter** implement `WorkflowStep` Protocol
(`packages/agent/workflows/steps.py::WorkflowStep` — chỉ yêu cầu `name: str` +
`async def run(state) -> StepOutcome`, không phải ABC/base class bắt buộc kế thừa):
`CachingStep` bọc quanh 1 `WorkflowStep` bất kỳ, tính cache key từ artifact fingerprint,
skip `run()` thật nếu cache hit. Không cần sửa `engine.py`, không cần `custom_step_builders`
đổi chữ ký — dùng đúng cơ chế inject step theo id đã có sẵn.

## Phạm vi KHÔNG làm ở Wave M5

- Dry-run graph inspection (không có yêu cầu cụ thể — YAGNI).
- Cache persistence qua Postgres (cache là tối ưu tốc độ offline, không phải nguồn sự thật —
  mất cache khi restart process chỉ làm pipeline chạy lại, không mất dữ liệu thật).
- Wiring `CachingStep` vào 1 pipeline eval/build cụ thể nào (vd Skill Optimization Lab, Wave
  M3) — đó là quyết định sử dụng, để khi có pipeline thật cần dùng, không phải phần "xây hạ
  tầng cache" của Wave M5.
