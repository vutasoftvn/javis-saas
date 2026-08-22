# Phase 10 — RBAC hoàn thiện, Connector Pattern, Observability

> Chi tiết thực thi cho Phase 10 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. Mở rộng `evaluate_access()` (Phase 1c) lên đủ 6 chiều theo §8.5 guide gốc, chuẩn hoá pattern connector cho external integration, và hoàn thiện eval/observability taxonomy.

## 10a. RBAC decision function — đủ 6 chiều (§8.5)

**Bối cảnh:** Phase 1c đã có `evaluate_access(role, agent_permission_level, tool_risk_level, tool_permission) -> ALLOW/REQUIRE_APPROVAL/DENY`. Phase 10a mở rộng thêm `TenantPolicy`, `ExecutionMode`, `DataScope` vào công thức, đúng target:
```
Decision = RBAC/Entitlement ∩ TenantPolicy ∩ AgentPermissionLevel ∩ ToolRisk ∩ ExecutionMode ∩ DataScope
```

**Task:**
1. Định nghĩa `ExecutionMode` (nếu chưa có sẵn — kiểm tra `agentos/core/` trước khi tạo mới):
```python
class ExecutionMode(str, Enum):
    INTERACTIVE = "interactive"           # có người đang chat trực tiếp, chờ phản hồi
    APPROVED_WORKFLOW = "approved_workflow"  # chạy trong workflow đã được duyệt trước (Phase 8b)
    AUTONOMOUS_SAFE = "autonomous_safe"      # agent tự chạy không giám sát, chỉ cho phép risk thấp
```
2. Định nghĩa `DataScope`:
```python
class DataScope(str, Enum):
    WORKSPACE = "workspace"
    COMPANY = "company"
    READ_ONLY = "read_only"
```
3. Định nghĩa `TenantPolicy` — cấu hình theo từng company (ví dụ company X không cho phép bất kỳ agent nào tự động gửi email ra ngoài, bất kể role/risk gì) — lưu ở `services/control-plane` (đây là business policy, thuộc business truth), AgentOS đọc qua API/Tool đọc read-only, không tự lưu bản sao policy trong Agent Plane.
4. Mở rộng `evaluate_access()`:
```python
def evaluate_access(
    *, role: str, agent_permission_level: PermissionLevel,
    tool_risk_level: ToolRiskLevel, tool_permission: ToolPermission,
    tenant_policy: TenantPolicyDecision, execution_mode: ExecutionMode,
    data_scope: DataScope,
) -> PolicyDecision: ...
```
Nguyên tắc: kết quả cuối = giao (intersection) của mọi chiều — bất kỳ chiều nào trả `DENY` thì kết quả `DENY`; nếu không chiều nào `DENY` nhưng có ít nhất 1 chiều `REQUIRE_APPROVAL` thì kết quả `REQUIRE_APPROVAL`; chỉ `ALLOW` khi tất cả 6 chiều đều `ALLOW`.
5. `ExecutionMode.INTERACTIVE` luôn yêu cầu approval cho risk ≥ HIGH bất kể role/level (an toàn hơn khi có người đang trực tiếp tương tác, tránh agent tự ý hành động ngoài ý muốn). `ExecutionMode.AUTONOMOUS_SAFE` chỉ cho phép risk LOW/MEDIUM, risk HIGH/CRITICAL luôn `DENY` (không có approval vì không có người giám sát để duyệt kịp thời) trừ khi đã qua `APPROVED_WORKFLOW` trước đó.
6. `DataScope.READ_ONLY` override mọi write tool về `DENY` bất kể risk/role.

**Task cập nhật caller:**
7. Rà lại mọi nơi gọi `evaluate_access()` cũ (Executor Phase 1c/3a, ADK node Phase 9b, Workflow engine Phase 8b) — cập nhật truyền đủ 6 tham số. Xác định `execution_mode` tại từng call site: request từ Text Chat/Voice trực tiếp = `INTERACTIVE`; request từ trong 1 workflow đã duyệt = `APPROVED_WORKFLOW`; request từ background job không giám sát = `AUTONOMOUS_SAFE`.

**Acceptance:**
- [ ] Test: Founder + L3_EXECUTE + risk LOW + `DataScope.READ_ONLY` → vẫn `DENY` nếu tool là write (data scope override).
- [ ] Test: `ExecutionMode.AUTONOMOUS_SAFE` + risk HIGH → `DENY`, không có đường `REQUIRE_APPROVAL` (vì không có người duyệt kịp trong autonomous mode).
- [ ] Test: `ExecutionMode.INTERACTIVE` + risk HIGH + role founder + level L3 → vẫn `REQUIRE_APPROVAL` (an toàn ưu tiên trong tương tác trực tiếp) — **quyết định nghiệp vụ cụ thể này cần xác nhận với người vận hành trước khi code**, vì có thể mâu thuẫn với kỳ vọng "Founder L3 = full autonomy" đã thiết lập ở Phase 1c; nếu mâu thuẫn, ghi rõ decision cuối cùng vào code comment.
- [ ] Toàn bộ call site cũ (Executor, ADK node, Workflow engine) đã cập nhật, không còn gọi API cũ 4 tham số.
- [ ] `TenantPolicy` đọc từ `services/control-plane` qua API, không có bản sao policy lưu cứng trong `agentos/`.

## 10b. Connector Pattern & OAuth (§16.1-16.3)

**Task:**
1. Viết pattern chuẩn (tài liệu ngắn `agentos/connectors/README.md` + code mẫu), 2 tầng theo đúng guide:
```
External service
     ↓ OAuth
Secret store (vault — kiểm tra infra/ đã có vault nào chưa, ví dụ HashiCorp Vault/cloud KMS, không tự dựng vault mới nếu đã có)
     ↓
Connector transport client   (agentos/connectors/<name>/client.py — chỉ lo auth/HTTP)
     ↓
COSA Tool adapter             (agentos/tools/clusters/<name>_tools.py — map operation → ToolSpecV2, Phase 3a)
     ↓
Governance (evaluate_access, Phase 10a)
     ↓ HTTP
services/ API (nếu connector data cần persist thành business record)
```
2. Implement 1 connector tham chiếu (ví dụ Slack API — gửi message) để chứng minh pattern:
   - `agentos/connectors/slack/client.py`: OAuth token exchange, HTTP client gọi Slack API, không chứa business logic.
   - Token lưu ở vault/secret store, không lưu trong memory provider (Phase 7) hay trace (dù đã redact — nguyên tắc là không đưa secret vào bất kỳ hệ thống nào ngoài vault, không chỉ dựa vào redaction làm lưới an toàn cuối).
   - Tool `commercial.notification.slack_send` (ví dụ) với `risk_level=high` (external write), `approval_policy` theo Phase 3a.
3. OAuth ownership: token linking flow (user kết nối tài khoản Slack cá nhân/company) thuộc `services/identity` (integration/connector linking là identity capability theo §16.3 guide gốc) — `agentos/connectors/` chỉ dùng token đã có, không tự làm OAuth flow đầu-cuối trong Agent Plane.
4. Audit: mọi request/response qua connector ghi vào audit sink (Phase 3d) có redaction, kèm metadata external (endpoint gọi, status code, thời gian) nhưng không log token/credential.
5. Rate limit/retry/circuit breaker: thêm ở tầng `client.py` (ví dụ dùng `httpx` với retry backoff), không đặt logic này trong Tool adapter (tách biệt transport concern khỏi business/governance concern).

**Acceptance:**
- [ ] Connector Slack tham chiếu hoạt động end-to-end (test có thể dùng mock server thay vì Slack thật, nhưng phải test đủ luồng: token lookup từ vault → gọi API → xử lý response → ghi audit).
- [ ] Test: external write (risk HIGH) không có approval trước → bị chặn theo `evaluate_access()` (Phase 10a), không gọi được API bên ngoài.
- [ ] Test: audit record của 1 lần gọi connector không chứa token/credential thô.
- [ ] Test: connector client tự retry khi gặp lỗi tạm thời (5xx/timeout), có giới hạn số lần retry (không retry vô hạn).
- [ ] README pattern đủ rõ để người khác thêm connector thứ 2 (ví dụ Notion) mà không cần hỏi lại kiến trúc.

## 10c. Eval taxonomy (§20.4-20.5)

**Task:**
1. Kiểm tra `agentos/evals/` hiện có gì trước (tương tự nguyên tắc verify-trước-khi-viết đã áp dụng ở Phase 8.0) — không giả định trống.
2. Tổ chức theo 7 loại eval của guide gốc, mỗi loại 1 subfolder trong `agentos/evals/`:
   - `agent/` — success rate, tool correctness, forbidden action rate.
   - `tool/` — độ chính xác tool call so với intent.
   - `skill/` — routing correctness (dùng lại eval case đã viết ở Phase 5b cho strategy skills làm ví dụ đầu tiên).
   - `model/` — latency, cost, quality regression giữa các model provider.
   - `business_outcome/` — proxy metric (ví dụ: gate evaluation có dẫn tới decision thật trong vòng N ngày không).
   - `safety_governance/` — approval coverage (bao nhiêu % tool call risk cao có qua approval đúng quy trình), policy violation bị chặn đúng bao nhiêu.
   - `retrieval/` — precision/recall cho Knowledge retrieval (Phase 7C/7D), dùng dataset câu hỏi đã biết đáp án.
3. Mỗi loại eval có: dataset định nghĩa (file JSON/YAML câu input + expected), hàm chấm điểm, cách query kết quả (đơn giản nhất: ghi kết quả vào bảng/file có thể query lại theo thời gian, không cần dashboard phức tạp ở Phase 10).
4. Nối vào `agentos/improvement/` (Phase 0c) — `GapDetector` giờ có nguồn `CapabilityOutcome` thật từ eval results thay vì phải nhận thủ công từ caller (đây chính là "production wiring gap" đã ghi nhận từ Phase 0c).

**Acceptance:**
- [ ] Mỗi loại eval trong 7 loại có ít nhất 1 dataset case + eval chạy được qua eval runner hiện có.
- [ ] Eval regression: chạy lại toàn bộ eval suite, so sánh với baseline lưu trước, có test/script phát hiện khi có regression rõ ràng (không cần alerting tự động ở Phase 10, chỉ cần script so sánh chạy thủ công/CI).
- [ ] `GapDetector` (Phase 0c) nhận `CapabilityOutcome` từ eval results thật, có test xác nhận 1 eval fail tạo ra đúng gap signal.

## 10d. OpenTelemetry distributed tracing (§20.2)

**Task:**
1. Kiểm tra `agentos/observability/` hiện có gì trước khi thêm OTEL — có thể đã có phần khởi tạo sẵn, không giả định trống.
2. Tích hợp OpenTelemetry SDK vào `agentos/core/` — mọi lời gọi lớn (Agent API request → ContextBuilder → tool call → services/ API) tạo span tương ứng.
3. `correlation_id` (đã có từ Phase 1a/3d) map vào OTEL trace context — không tạo ID thứ hai song song, dùng `correlation_id` làm trace ID hoặc gắn làm attribute nếu OTEL yêu cầu format ID riêng.
4. Cấu hình exporter (Jaeger/Zipkin/OTLP collector — kiểm tra `infra/` xem đã có sẵn hạ tầng nào, ưu tiên dùng lại thay vì dựng mới).
5. SQLite trace sink (Phase 0a) **không bị thay thế hoàn toàn** — vẫn giữ cho local trace/audit chi tiết đã redact (§7.3 SQLite rule: được phép cho local trace); OTEL bổ sung cho distributed tracing cross-service, không phải thay thế 1:1.

**Acceptance:**
- [ ] Test: 1 request Text Chat đầy đủ (từ Agent API tới tool call tới services/) tạo ra 1 trace liên tục trên OTEL backend, đúng thứ tự span cha-con.
- [ ] `correlation_id` xuất hiện trong OTEL trace, có thể tra cứu qua ID đó và khớp với `correlation_id` trong SQLite trace sink cho cùng request.
- [ ] SQLite trace sink vẫn hoạt động song song, không bị Phase 10d vô hiệu hoá.

## Dependency

10a phụ thuộc Phase 1c (đã có 4 chiều đầu) và cần cập nhật mọi call site đã tồn tại (Phase 3a, 8b, 9b) — nên làm sau khi các phase đó ổn định, tránh sửa liên tục theo API đang thay đổi. 10b độc lập, có thể làm song song 10a/10c/10d, chỉ cần Phase 3a (ToolSpecV2) và Phase 1a (TenantContext) đã có. 10c phụ thuộc Phase 5b (ví dụ eval case đầu tiên) và Phase 0c (GapDetector). 10d độc lập về kỹ thuật, chỉ cần correlation_id (Phase 1a) đã có, nên làm sau cùng trong phase này vì ít rủi ro nhất.
