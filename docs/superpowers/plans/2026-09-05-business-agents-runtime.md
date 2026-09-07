# Kế hoạch sửa runtime và khả năng thực thi của agents

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng F04–F06; bảo đảm agent dùng đúng context/quyền, chỉ báo hoàn tất có bằng chứng và thực sự có tool/knowledge mà skill cần.

**Architecture:** Tái sử dụng run_core/registry/gateway/lease; chuẩn hóa input/output và dispatch thay vì tạo runtime mới. Contract event lưu reference và pin; business outcome do Company xác nhận.

**Tech Stack:** Python/Pydantic/OpenAI Agents SDK adapter, Encore scheduler, pytest, PostgreSQL, Flutter views hiện có.

**Spec:** [07](/docs/architecture/overview/07-code-audit-business-agents-2026-09-05.md), [08](/docs/architecture/overview/08-phan-tich-cycle-cas-permissions-2026-09-05.md), [plan tổng](/docs/superpowers/plans/2026-09-05-business-agents-master.md).

## Global Constraints

- Kế thừa Global Constraints và H0 test conventions; A3 là điều kiện bật side effect mới.
- “Run hoàn tất chưa mặc nhiên là task hoặc KR hoàn tất.”
- Không thêm agent profile Strategy/Legal/CFO chỉ để đủ tên; compose skill/tool/workflow trước.
- Không suy trạng thái từ lời model; không tự gửi tin nhắn thật trong test. Test send dùng transport giả nhưng authorization/gateway/handler thật.
- Không nói đã kiểm durability nếu chỉ khởi tạo instance thứ hai trong cùng process.

## R1 — Contract producer→scheduler→worker và run identity ổn định

**Files sửa:** [execution_plane_client.py](/apps/cosa/events/execution_plane_client.py), [main.py](/apps/cosa/worker/main.py), [handlers.py](/apps/cosa/worker/handlers.py), [control-plane-scheduler.service.ts](/services/cosa/services/control-plane-scheduler.service.ts), [test_execution_plane_client.py](/tests/apps/cosa/events/test_execution_plane_client.py), [test_main.py](/tests/apps/cosa/worker/test_main.py).

**Files tạo:** [event_run_contract.py](/apps/cosa/events/event_run_contract.py), [test_event_worker_contract.py](/tests/apps/cosa/events/test_event_worker_contract.py), [event-run-contract.test.ts](/services/cosa/tests/event-run-contract.test.ts). Chỉ thêm bảng binding UUIDv7 ở local event storage nếu schedule/task record hiện có không lưu bền mapping event-rule→run; không tự dùng UUIDv5 trái quy tắc leaf ID.

**Thiết kế dispatch:** giữ task_type="run" đã hỗ trợ, bổ sung trigger metadata schema_version=1. Producer gọi builder contract chung; event adapter ở worker resolve aggregate dưới authority rồi đưa vào execute_run_task hiện có. Profile tra bảng tường minh theo pinned spec ID; unsupported profile từ chối có lý do.

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal
class EventRunEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    task_type: Literal["run"] = "run"
    run_id: str
    workspace_id: str
    event_id: str
    trigger_rule_id: str
    agent_profile: str
    agent_spec_id: str
    agent_spec_version: str
    agent_spec_hash: str
    aggregate_type: str
    aggregate_id: str
    correlation_id: str
```

- [ ] Test gọi producer thật với rule/env fixture có sẵn, đưa payload đã được scheduler lưu vào worker dispatch thật. Không tạo payload consumer riêng. RED hiện tại phải thể hiện thiếu task_type/run_id hoặc profile mapping.
- [ ] Chạy `PYTEST tests/apps/cosa/events/test_event_worker_contract.py` và `DBTEST cosa tests/event-run-contract.test.ts`.
- [ ] Persist run_id một lần trên unique(workspace,event,trigger_rule,spec_hash); retry đọc lại ID. Coalescing key có rule ID để hai rule cùng event không nuốt nhau. Run record và scheduling dùng outbox/idempotency, không random run_id mới mỗi lần retry; không copy raw business message lên scheduler.
- [ ] Consumer hỗ trợ envelope cũ bằng adapter chỉ khi có đủ reference để resolve quyền/run; thiếu thông tin quarantine với reason và retry tooling nội bộ. Không đoán workspace/profile. Pin dependencies bằng registry exact hash trước execution; lease/task claim fencing hiện hữu vẫn được dùng.
- [ ] Test duplicate event+same rule một run, hai rule hai run, unsupported profile không side effect, replay sau restart giữ run ID. Commit `fix: align event scheduling with durable worker run contracts`.

## R2 — Một pipeline context/auth/output cho Copilot và WGA

**Files sửa:** [copilot_run.py](/apps/cosa/worker/copilot_run.py), [run_core.py](/apps/cosa/worker/run_core.py), [wga_run.py](/apps/cosa/worker/wga_run.py), [handlers.py](/apps/cosa/worker/handlers.py), [engagement_read.py](/apps/cosa/capabilities/engagement_read.py), [kernel.py](/packages/agent_integrations/openai_agents_sdk/kernel.py), [Company copilot service](/services/company/commercial/services/customer-engagement/copilot.service.ts).

**Files tạo:** [run_outcome.py](/apps/cosa/worker/run_outcome.py), [test_run_outcome.py](/tests/apps/cosa/worker/test_run_outcome.py); sửa [test_copilot_run.py](/tests/apps/cosa/test_copilot_run.py), [test_copilot_p1_matrix.py](/tests/apps/cosa/test_copilot_p1_matrix.py).

**Interfaces:** run_core chuẩn hóa `prepare → gateway context reads → build model input → kernel → validate output → persist artifact → business callback`. `resolve_run_outcome(status,output_valid,artifact_persisted)` trả một trong completed/failed/waiting_approval/cancelled; status của RunStatus enum normalize tại adapter. DTO callback thêm reasonCode/artifactRef/evidenceRefs; không dùng final_output rỗng làm success.

- [ ] Thêm test failed/no-output/artifact write error/waiting/cancelled và context capture. Mẫu unit mới:

```python
from apps.cosa.worker.run_outcome import resolve_run_outcome
def test_failed_kernel_cannot_complete():
    assert resolve_run_outcome("FAILED", True, True) == "failed"
def test_completed_requires_artifact():
    assert resolve_run_outcome("COMPLETED", True, False) == "failed"
```

- [ ] Chạy PYTEST các file trên để ghi RED. Auth test dùng CompanyServiceClient thật + mock HTTP transport, capture Authorization đúng delegation, workspace/run/capability scopes đúng; không thay handler bằng mock trả dict để bỏ qua auth.
- [ ] Di chuyển prefetch sau resolve principal/delegation/compliance. Read qua gateway với InvocationContext chuẩn; token đúng secret/direction, không ambient tự đặt thủ công trước toàn run. Model input gồm prompt hệ thống tách context có provenance/trust; truncate có metadata, không silently drop input.context.
- [ ] Hàm trạng thái xử lý WAITING_APPROVAL/CANCELLED/FAILED trước success. Output schema theo skill/intent, artifact thực sự lưu/readable mới callback completed. Persist callback idempotent theo run + completion version, retry artifact không tạo bản thứ hai. Một final response mẫu không thay được artifact bị mất.
- [ ] WGA/resume COMPLETED gọi S3 validateTaskCompletion; trong giai đoạn S3 chưa deploy, giữ task in_progress kèm completion_pending, không advance(done) trực tiếp. Cả initial run lẫn resumed run dùng cùng finalizer. WAITING_APPROVAL giữ checkpoint và không báo failed.
- [ ] Test business callback conflict/stale version và UI consumer phản ánh đúng structured state; expose lý do lỗi qua DTO hiện có, không parse text. Gates Python/Company, commit `fix: preserve authorization context and truthful agent completion`.

## R3 — Knowledge thật, capability readiness và vai trò agent

**Files sửa:** [knowledge_read.py](/apps/cosa/capabilities/knowledge_read.py), [capability_registration.py](/apps/cosa/composition/capability_registration.py), [AgentSpecs](/apps/cosa/agents/specs.py), [finance_read.py](/apps/cosa/capabilities/finance_read.py), [marketing_read.py](/apps/cosa/capabilities/marketing_read.py), [snapshot_repository.py](/packages/agent/knowledge/snapshot_repository.py). Reuse repository hiện có thay vì một store knowledge mới.

**Files tạo:** [capability_readiness.py](/apps/cosa/agents/capability_readiness.py), [test_business_agent_readiness.py](/tests/apps/cosa/agents/test_business_agent_readiness.py), [test_knowledge_profile_evidence.py](/tests/apps/cosa/test_knowledge_profile_evidence.py). Sửa manifests/SKILL.md thực sự pin bởi AgentSpecs sau khi resolve danh sách ở code, không đổi toàn bộ skillpacks.

**Interfaces:** `check_capability_readiness(required:set[str], available:set[str])->list[str]` trả sorted missing. Knowledge handler factory nhận repository đã inject từ plane composition; trả sections với sourceId/version/publishedAt/freshUntil/trust, không đổi untrusted=false vì include_untrusted=true. Read profile phải kiểm workspace và published state trên nguồn bên dưới, không chỉ wrapper.

- [ ] Test Operations pin lifecycle skill thiếu `strategy.project.get`/`strategy.next_best_action.get` báo missing; test knowledge DB/query spy xác nhận đọc nguồn thật và provenance. Unit core:

```python
def check_capability_readiness(required: set[str], available: set[str]) -> list[str]:
    return sorted(required - available)
assert check_capability_readiness({"strategy.project.get"}, set()) == ["strategy.project.get"]
```

- [ ] Chạy PYTEST hai file mới và [test_knowledge_production_wiring.py](/tests/apps/cosa/test_knowledge_production_wiring.py), ghi RED cho stub/lỗi trust.
- [ ] Readiness chạy khi seed/publish và trước activation: skill required tool có trong registry + spec capability refs; quyền runtime vẫn kiểm riêng A3, không tự grant để readiness pass. Pin/hash cập nhật theo cơ chế hiện có, old run tiếp tục dùng old pin.
- [ ] Operations nhận read cycle/weekly/metric/evidence/context và draft planning; Finance nhận read transaction/snapshot/document/budget, draft request/reconciliation theo F6; Marketing context nối experiment/evidence/CRM outcome bằng ID thực. Strategy/Legal compose read/advisory vào role thích hợp, không tạo agent mới. Send/publish chỉ theo workflow đã có approval, không mở vì đổi spec.
- [ ] Knowledge không có dữ liệu trả EMPTY/UNAVAILABLE và nguồn thiếu; thử cross-workspace, unpublished, expired, include_untrusted. Frontend profile composition hiển thị missing capability/permission như hai vấn đề khác nhau tại [profile_composition_view.dart](/frontend/lib/modules/settings/workforce/views/profile_composition_view.dart); tạo widget test [agent_readiness_test.dart](/frontend/test/modules/settings/agent_readiness_test.dart).
- [ ] Chạy skillpacks-validate, contract-freeze-check, relevant pytest/Flutter và typecheck API nếu đổi; commit `feat: wire grounded knowledge and business agent capability readiness`.

## R4 — Evals nghiệp vụ và độ bền qua process thật

**Files sửa:** [customer_support_autopilot_cases.py](/apps/cosa/evals/customer_support_autopilot_cases.py), [test_autopilot_run.py](/tests/apps/cosa/test_autopilot_run.py), [test_crash_recovery_subprocess.py](/tests/apps/cosa/worker/test_crash_recovery_subprocess.py), [autopilot_run.py](/apps/cosa/worker/autopilot_run.py).

**Files tạo:** [test_business_agent_evals.py](/tests/apps/cosa/evals/test_business_agent_evals.py), [test_event_approval_restart.py](/tests/e2e/test_event_approval_restart.py), [business-agent-evals.md](/docs/testing/business-agent-evals.md).

**Consumes:** A3 revoke/version, R1 envelope, R2 finalizer, R3 knowledge/readiness, S3 completion. **Produces:** eval gọi wrapper/kernel/gateway thật với model/provider fake và báo business output/side effects chính xác.

- [ ] Viết table-driven cases: same input different project facts→different proposal; denied rule→zero tool calls; malformed model output→failed; takeover→no send; stale policy after approval→denied; artifact failure→not completed; no metric evidence→task completion pending/KR unchanged.
- [ ] Chạy `PYTEST tests/apps/cosa/evals/test_business_agent_evals.py`; bỏ các eval chỉ trả dict kỳ vọng mà không gọi production path. Test cần assert gateway/audit/business state, không chỉ model text.
- [ ] Dùng subprocess fixture sẵn có: process A claim và persist WAITING_APPROVAL → terminate A → process B resolve same checkpoint và decision, chạy một lần → process C đọc lại kết quả. Model/send transport fake; PostgreSQL, leases, scheduler, approval store thật. Lưu pid để chứng minh các process khác nhau.
- [ ] Assertion nghiệm thu:

```python
assert first_worker_pid != resumed_worker_pid
assert delivered_message_count == 1
assert completed_run_ids == [original_run_id]
assert approval_checkpoint_after_restart == approval_checkpoint_before_restart
```

Test riêng founder takeover trước resume phải delivered_message_count=0. Không re-enable autopilot nếu trạng thái đã disabled trong Company.
- [ ] Chạy test restart mới với marker cross_plane trên disposable cluster; ghi timeout/lease evidence. Chạy existing autopilot/capability approval tests. Commit `test: verify durable and policy-bound business agent outcomes`.

**Nghiệm thu:** F04–F06 đã tái hiện và sửa bằng test xuyên producer/consumer; không có stub knowledge hay completion giả; missing tools hiển thị rõ; mọi autonomy có negative eval và restart evidence. Điều chỉnh frontend liên quan nằm trong S5/A4/F6 và profile composition R3, không tạo một màn hình “agent dashboard” trùng lặp.
