# COSA Feature Implementation Decision Tree (§18.1-18.2)

Quy trình bắt buộc cho mọi tính năng mới được thêm vào hệ thống JAVIS / COSA.

---

## 1. Sơ Đồ Cây Quyết Định (Feature Implementation Decision Tree)

Áp dụng cây quyết định này từ trên xuống dưới cho mọi yêu cầu tính năng:

```
Yêu cầu tính năng mới X
      │
      ▼
X chỉ thay đổi cách trình bày (UI/response format), không tạo/đổi business record?
      │YES → Sửa ở Flutter (frontend/) hoặc Agent API event contract (agentos/api/) — KHÔNG chạm services/
      │NO
      ▼
X cần business record tồn tại lâu dài (đọc lại được, có lifecycle, cross-reference)?
      │YES → Owner là 1 bounded context trong services/ đã có (control-plane/identity/operations/commercial/finance-legal)
      │        → schema + migration → service logic tất định → handler/API → domain event
      │        → Chỉ tạo services/<new> mới nếu ĐỦ CẢ 3 điều kiện §18.2:
      │          1. Bounded context độc lập rõ ràng;
      │          2. Lifecycle/data ownership khác biệt hẳn;
      │          3. Mở rộng service hiện tại gây coupling xấu đáng kể.
      │NO
      ▼
X cần agent gọi 1 khả năng đã có ở services/ (đọc hoặc ghi)?
      │YES → Tạo/tái dùng Tool (ToolSpecV2, Phase 3a) → KHÔNG viết business logic trong tool handler
      │NO
      ▼
X cần agent biết "làm sao để" thực hiện 1 loại việc (quy trình, khi nào dùng tool nào)?
      │YES → Skill (skillpacks/, Phase 5a) — chỉ tạo Skill mới nếu KHÔNG phải chỉ là:
      │        - 1 API CRUD (đó là Tool),
      │        - 1 business rule (đó là Service logic),
      │        - 1 chuỗi retry/approval (đó là Workflow),
      │        - 1 persona (đó là Agent Profile).
      │NO
      ▼
X cần nhiều bước tất định có thể fail/compensate/pause (không cần suy luận multi-agent)?
      │YES → Deterministic Workflow (agentos/workflows/, Phase 8b)
      │NO
      ▼
X cần nhiều specialist agent phối hợp/suy luận song song?
      │YES → ADK Orchestration (agentos/orchestration/adk/, Phase 9)
      │NO
      ▼
X đã có sẵn qua Agent API (chat/tool/skill đã tồn tại)?
      │YES → Chỉ cần Text Chat/Voice expose nó — KHÔNG viết business logic mới trong voice_tools.py/chat handler
```

---

## 2. Checklist Khi Mở Pull Request (PR Template Checklist)

> **Quy định bắt buộc trước khi merge PR:**
> Trong mô tả PR, tác giả phải chỉ rõ nhánh trong cây quyết định đã đi:
> 
> ```markdown
> ### Feature Tree Decision Branch
> - [x] Nhánh đã chọn: [UI/API Contract | Services Bounded Context | Tool | Skill | Workflow | ADK Orchestration | Voice/Chat Expose]
> - [x] Đã xác nhận không vi phạm ranh giới kiến trúc (không viết business logic vào tool/skill/chat handler).
> - [x] Bổ sung test tương ứng với nhánh quyết định đã chọn.
> ```

---

## 3. Rà Soát Đối Chiếu Ngược Các Tính Năng Đã Xây (Phases 2 - 10)

| Phase & Tính năng | Bounded Layer | Nhánh Cây Quyết Định Đã Áp Dụng | Đánh Giá Tuân Thủ |
|---|---|---|---|
| **Phase 2: Strategy Domain** | `services/operations/strategy` | **Services Bounded Context**: Schema migrations + deterministic calculation (NBA, Stage Policy) + Domain Events. | ✅ Đúng 100% — logic nghiệp vụ nằm hoàn toàn ở TypeScript backend. |
| **Phase 3: ToolSpecV2** | `agentos/tools/` | **Tool Layer**: Wrap endpoints qua `EncoreClient` + metadata (Risk, Idempotency, Governance). | ✅ Đúng 100% — tool handlers chỉ là pass-through transport. |
| **Phase 4: Agent Profiles** | `agentos/profiles/` | **Agent Profile**: Định nghĩa persona, mission scope, default tools. | ✅ Đúng 100% — không chứa procedural workflows. |
| **Phase 5: Strategy Skillpacks** | `skillpacks/strategy/` | **Skill Layer**: Hướng dẫn 10 mục về cách phân rã bài toán, gọi tool và điều kiện tiên quyết. | ✅ Đúng 100% — cấm LLM tự do bịa kết quả NBA/Gate. |
| **Phase 6: Self-Improvement** | `agentos/improvement/` | **Governance / Improvement Loop**: Gap detection, proposal evaluation, distillation. | ✅ Đúng 100% — hoạt động dựa trên eval metrics thật. |
| **Phase 7: Memory & Knowledge** | `agentos/memory/`, `agentos/knowledge/` | **Memory / Retrieval Layer**: Lưu trữ operational history, short-term/long-term memory & RAG. | ✅ Đúng 100% — tách biệt hoàn toàn khỏi Postgres business records. |
| **Phase 8: Workflow Engine** | `agentos/workflows/` | **Deterministic Workflow**: DAG engine, pause/resume approval, compensation. | ✅ Đúng 100% — quy trình tất định, không cần multi-agent. |
| **Phase 9: ADK Orchestration** | `agentos/orchestration/adk/` | **ADK Orchestration**: Phối hợp specialists song song, governance gate, synthesis. | ✅ Đúng 100% — multi-agent reasoning có kiểm soát. |
| **Phase 10: 6D RBAC & Connectors** | `agentos/core/policy.py`, `agentos/connectors/` | **Governance & Connector Layer**: Quyết định 6 chiều, 2-tier transport separation, Otel tracing. | ⚠️ Phần lớn đúng — xem "Known Deviations" bên dưới cho các điểm lệch cụ thể. |

---

## 4. Known Deviations (phát hiện khi rà soát lại 2026-08-23, không im lặng bỏ qua theo đúng §11a.3)

| Phase | Lệch gì | Vì sao lệch | Trạng thái |
|---|---|---|---|
| Phase 7D (Knowledge citation) | `KnowledgeIngestPipeline.ingest()` không ghi `source_title`/`source_uri` vào `chunk.metadata` dù `retrieve_citations()` đọc đúng 2 field đó — citation luôn thiếu provenance. | Thiếu sót khi implement, không phải quyết định có chủ đích. | ✅ Đã fix trong phiên rà soát 2026-08-23. |
| Phase 8b (Workflow governance) | `WorkflowStepSpec.permission_level` khai báo trong schema nhưng chưa từng truyền vào `ToolCallStep`; `ToolCallStep.evaluate_access()` thiếu `tenant_policy`/`data_scope` — 2/6 chiều governance không áp dụng được cho step trong workflow. | Thiếu sót khi implement — cấu hình "có nhưng không có tác dụng". | ✅ Đã fix trong phiên rà soát 2026-08-23. |
| Phase 9c (ADK Orchestrator) | `PermissionLevel` được dùng làm fallback nhưng thiếu import — `NameError` tiềm ẩn nếu nhánh đó thực sự chạy. | Bug sót, chưa bị test nào kích hoạt vì default luôn truthy. | ✅ Đã fix. |
| Phase 9a (dependency pin) | `deepseek-harness-sdk` không pin version dù roadmap yêu cầu khớp legacy (`0.1.0rc6`). | Thiếu sót khi implement. | ✅ Đã fix. |
| Phase 10a (TenantPolicy) | `evaluate_access()` nhận tham số `tenant_policy` nhưng chưa có adapter nào đọc thật từ `services/control-plane`. | Cần API control-plane trước khi wire. | ✅ Đã fix thật: bảng `cosa.company_agent_policy` + migration (`services/control-plane/migrations/4_add_agent_policy.up.sql`) + endpoint `GET/POST /platform/internal/agent-policy` (test qua `encore test`, Postgres thật) + Python `TenantPolicyClient` wire vào `Executor`/`AgentRuntime`/`build_cosa_agent_plane()`, có test end-to-end xác nhận tool bị DENY đúng theo policy từ control-plane. |
| Phase 10c (Eval taxonomy) | `EvalRunner` tự nhận "7-Category" nhưng chỉ có 6 method — thiếu `run_model_eval`; test tương ứng cũng chỉ test 6 category và tự assert `== 6`. | Thiếu sót khi implement. | ✅ Đã fix (thêm `run_model_eval`, sửa test đủ 7). |
| Phase 10c (Eval regression) | Chưa có script/test so sánh eval result với baseline để phát hiện regression (acceptance 10c-2). | — | ✅ Đã fix thật: `agentos/evals/regression.py` (save/compare baseline) + `agentos/evals/run_regression_check.py` (CLI chạy được: `python -m agentos.evals.run_regression_check --save/--check`, dùng lại `STRATEGY_EVAL_CASES` thật) + test. |
| Phase 10d (OTEL) | `OtelTracer` là class tự viết mô phỏng, không dùng package `opentelemetry` thật, không có exporter. | — | ✅ Đã fix thật: viết lại `OtelTracer` dùng `opentelemetry-sdk` thật (`TracerProvider`, `InMemorySpanExporter` + `ConsoleSpanExporter`, hook sẵn OTLP qua `OTEL_EXPORTER_OTLP_ENDPOINT` khi có quyết định hạ tầng), pin `opentelemetry-api`/`opentelemetry-sdk==1.43.0` vào `agentos/requirements.txt`. Exporter thật (Jaeger/OTLP) vẫn cần quyết định hạ tầng `infra/` trước khi bật. |
| Phase 11b/11c (Smoke test) | Roadmap yêu cầu smoke test chạy qua HTTP thật + `services/` thật + DB thật, không mock ở tầng service. | — | ✅ Đã fix thật: `test_strategy_smoke_e2e_real_services.py` chạy `encore run` (Encore + Postgres thật) + `EncoreClient` thật, không mock — cả 2 test pass thật. Việc này lộ ra và đã fix 2 bug thật: (1) tool `strategy.project.get` gọi endpoint chưa từng tồn tại → thêm `GET /operations/projects/:id` thật. (2) Toàn bộ `agentos/tools/clusters/strategy_tools.py` (10 tool) đã được rà lại và viết lại field mapping cho khớp đúng DTO thật của từng handler TS (`statement`/`importance`/`uncertainty` cho assumption; `hypothesis`/`method`/`successCriteria` cho experiment; `sourceType`/`claim` cho evidence — backend tự tính strength/confidence; `stagePolicyId` (không phải `currentStage`/`targetStage`/`passed`/`score`) cho gate evaluation — thêm tool mới `strategy.stage_policy.list` để agent tra được id hợp lệ; `decision` enum `proceed/pivot/kill/hold` cho decision record), thêm `companyId`+`workspaceId` bắt buộc đúng theo thực tế. Đồng bộ luôn 6 file `SKILL.md` (assumption-discovery, gate-evaluation, experiment-design, evidence-synthesis, decision-capture) và `test_strategy_tools.py`/`test_strategy_smoke_e2e.py`/`test_commercial_smoke_e2e.py` theo field mới. **Gap còn lại phát hiện thêm, ngoài phạm vi field-mapping**: bảng `experiments` thật không có cột tham chiếu `sourceExperimentId`/`leadRef` như roadmap §4.5 giả định — cần quyết định thiết kế riêng (thêm cột), đã ghi rõ comment trong `test_commercial_smoke_e2e.py`, không tự ý thêm cột khi chưa xác nhận. |
| Phase 12b (Performance baseline) | Báo cáo `PERFORMANCE_BASELINE_2026-08-23.md` trình bày như benchmark hạ tầng production đã đo (kèm khuyến nghị cụ thể như `pool_size >= 20`), nhưng test nền chạy hoàn toàn in-process với mock model, không chạm Postgres/HTTP server/model provider thật. | Nhầm lẫn giữa micro-benchmark nội bộ và load test hạ tầng thật. | ✅ Đã sửa báo cáo cho trung thực, gỡ khuyến nghị không có cơ sở đo lường. Load test 100 user thật qua HTTP+Postgres+model provider thật vẫn **chưa làm** — cần thêm 1 lượt riêng (đã xác nhận `encore run` khả thi trong phiên này, có thể tái dùng cho việc này). |
| Phase 12a (Security review) | Chưa có báo cáo security review chính thức ghi lại kết quả PASS cho 7 mục checklist như acceptance yêu cầu (dù rà nhanh 5/7 mục grep-based đều sạch). Thiếu test "brute-force approval_id không hợp lệ" riêng biệt. | Chưa làm đầy đủ — nằm ngoài phạm vi 1 lượt rà soát nhanh. | ❌ Chưa làm. |
