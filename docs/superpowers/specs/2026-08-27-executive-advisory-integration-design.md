# Executive Advisory cho COSA — Design Specification

**Trạng thái:** đề xuất để triển khai theo phase
**Ngày:** 2026-08-27
**Nguồn tham chiếu:** audit [SenteLabsAI/OpenExecutive](https://github.com/SenteLabsAI/OpenExecutive) tại commit `63dd9c6ce360fb74d98246fe7d0131f867fe42e0`
**Phạm vi:** toàn bộ COSA (Flutter experience, `apps/cosa`, `packages/agent_core`, `packages/agent_recipes`, `services/cosa` và `services/company`)

## 1. Quyết định kiến trúc

Xây **Executive Advisory** như một vertical product của COSA: một trợ lý điều hành có một giọng trả lời thống nhất, tổng hợp dữ liệu doanh nghiệp theo Workspace, luôn đưa bằng chứng và chỉ đưa ra đề xuất trong giai đoạn đầu.

Không đưa OpenExecutive vào COSA dưới dạng service thứ hai, không sao chép database/runtime/agent loop của nó, và không thêm dependency từ repository đó. COSA đã có Control Plane durable, registry/spec pinning, Capability Gateway, approval/audit, Workspace tenancy và business services là nguồn sự thật; đây là các năng lực mà OpenExecutive không nên thay thế.

```text
Flutter / API client
        │ X-Workspace-Id + bearer token
        ▼
apps/cosa API ── conversation profile = executive_advisory
        ▼
durable scheduler + worker + pinned AgentSpec
        ▼
Capability Gateway ── executive.context.read (LOW, read-only)
        ▼
services/company executive-context projection (business truth)
        ▼
evidence bundle ──► Executive Brief artifact + citations
```

Mọi đường dữ liệu trong sơ đồ phải mang cùng một `workspace_id`. `packages/agent_core` chỉ biết contract/protocol; nó không được import trực tiếp `services/company` hay `services/cosa`.

## 2. Vì sao không port OpenExecutive trực tiếp

Audit OpenExecutive cho thấy các ý tưởng có giá trị (vai trò executive, một câu trả lời được tổng hợp, RAG, decision/initiative memory, evaluation scenario), nhưng implementation hiện tại không phù hợp để đặt cạnh COSA:

| Thành phần OpenExecutive | Giá trị có thể học | Quyết định cho COSA |
| --- | --- | --- |
| Vai trò COO/CFO/Strategy/Product/Marketing/HR/Legal/Board | Taxonomy rõ cho câu hỏi điều hành | Dùng như role/prompt/skill có version, không tạo tám agent luôn chạy. |
| CEO synthesis / một giọng trả lời | Trải nghiệm điều hành nhất quán | Thêm `executive_advisory` profile và artifact brief. |
| RAG + citations | Câu trả lời bám bằng chứng | Xây retrieval hybrid theo Workspace và authority class trong Agent Core ở Phase B. |
| Decision/initiative extraction | Lưu ý quyết định còn mở | Chỉ tạo proposal có provenance; Company Service vẫn là business truth. |
| Eval scenarios | Kiểm soát chất lượng thực tế | Bổ sung eval của COSA cho tenancy, factuality, citation và safety. |
| SQLite/Chroma/scheduler đơn process | Có ích cho prototype độc lập | Không sử dụng; COSA đã có PostgreSQL, scheduler/lease/control plane durable. |
| Static tool routing và tám specialist mỗi lượt | Dễ demo | Không sử dụng; route theo profile/policy, chỉ gọi specialist khi có điều kiện rõ ràng. |
| Attachment text đưa thẳng vào prompt | Rủi ro prompt injection | Cấm ở Phase A; Phase B phải có ingest boundary, trust label và citation. |
| MCP dependency không pin/fallback cài đặt | Mở rộng nhanh nhưng thiếu kiểm soát | Chỉ dùng catalog capability đã review và connector grant của COSA. |

Ngoài ra, bản OpenExecutive đã audit có lỗi build UI với cấu hình Tailwind và dùng Auth.js beta bị advisory fail-open. Đây là lý do bổ sung để chỉ tham chiếu kiến trúc/sản phẩm, không tái dùng dependency hay middleware của nó.

## 3. Mục tiêu, phi mục tiêu và nguyên tắc

### Mục tiêu

1. Người dùng trong một Workspace hỏi một câu điều hành và nhận một **Executive Brief** ngắn gọn, có dữ liệu-as-of, evidence/citation, confidence và các câu hỏi còn thiếu.
2. Câu trả lời đầu tiên chỉ đọc dữ liệu nội bộ đã được phép. Nó không gửi email, tạo payment, sửa task, ghi sổ hoặc gọi connector bên ngoài.
3. Mỗi run tái lập được: profile, prompt, model policy, capability contract, knowledge snapshot (khi có) và evidence bundle đều có provenance/pin.
4. Thiết kế mở rộng được sang council/knowledge/connector mà không phá vỡ boundary hoặc nới lỏng governance.

### Phi mục tiêu của Phase A

- Không làm clone giao diện hay runtime của OpenExecutive.
- Không tạo “CEO agent” có quyền mặc định cao hơn các agent khác.
- Không ingest PDF/email/attachment do người dùng tải lên vào prompt hoặc vector store.
- Không tự động ghi Decision, Initiative, Task, OKR, transaction hay calendar event.
- Không triển khai semantic/vector search, multi-agent council, connector SaaS, recurring executive brief, hay memory promotion trong cùng phase với vertical read-only.

### Invariants bắt buộc

- `Workspace` là product tenancy key duy nhất. Không đưa `company_id`, `tenant_id` hay mapping Platform ra browser, public DTO, run payload hoặc Agent Core model mới.
- `services/company` là authority cho business data. Executive Advisory chỉ đọc snapshot/record từ service contract; không tự query bảng business từ `apps/cosa`.
- Mọi tool call đi qua `CapabilityGateway`. Không có HTTP/DB side effect hoặc bypass audit từ prompt, agent hoặc worker.
- `RunRequest.workspace_id`, principal, conversation và policy context phải được propagated nguyên vẹn từ runtime adapter vào `GatewayExecutionRequest`. Model tool arguments không được ghi đè ambient context; không được dùng default Workspace trong capability handler.
- Approval phải bound vào exact run, tool call, payload hash và checkpoint. Phase A không có capability cần approval vì toàn bộ capability là `LOW`/read-only.
- Thiếu policy snapshot, membership, capability contract, dữ liệu evidence hoặc registry dependency thì fail closed; không trả lời bằng dữ liệu Workspace khác hoặc fallback “global”.
- Mọi khẳng định thực tế trong brief phải có ít nhất một `evidence_ref`. Không đủ evidence thì kết quả phải ghi rõ “chưa đủ dữ liệu để kết luận”.

## 4. Product contract: Executive Brief v1

Phase A không trả một chuỗi văn bản không cấu trúc duy nhất. Kernel có thể render Markdown cho chat, nhưng artifact canonical cần có schema versioned như sau:

```json
{
  "schema_version": "cosa.executive-brief/v1",
  "workspace_id": "ws_123",
  "data_as_of": "2026-08-27T09:30:00Z",
  "summary": "Hai rủi ro delivery đang cần quyết định.",
  "findings": [
    {
      "id": "finding_01",
      "claim": "Launch Q4 đang có blocker chưa được xử lý.",
      "domain": "operations",
      "confidence": "high",
      "evidence_refs": ["task:42"],
      "assumptions": []
    }
  ],
  "proposed_actions": [
    {
      "description": "Phân công owner xác nhận blocker trong 24 giờ.",
      "impact": "Giảm rủi ro trễ milestone.",
      "requires_human_decision": true
    }
  ],
  "open_questions": ["Chưa có forecast ngân sách cho milestone Q4."],
  "evidence_coverage": {"cited_findings": 1, "total_findings": 1},
  "provenance": {"run_id": "run_...", "agent_spec": "cosa.agents.executive-advisory@1.0.0"}
}
```

`evidence_ref` là ID ổn định trong evidence bundle, không phải một URL do model tự dựng. Mỗi ref gồm: `ref_id`, `source_kind`, `source_id`, `workspace_id`, `title`, `observed_at`, `authority_class` và `redacted_excerpt`. UI chỉ render citation do server cung cấp.

Các giá trị được phép ở Phase A:

| Field | Giá trị được phép |
| --- | --- |
| `domain` | `operations`, `strategy`, `finance`, `cross_functional` |
| `confidence` | `high`, `medium`, `low`, `insufficient_evidence` |
| `authority_class` | `BUSINESS_SNAPSHOT`, `POLICY`, `REFERENCE` |
| `source_kind` | `task`, `objective`, `project`, `portfolio`, `decision_record`, `financial_summary`, `policy` |

Không đưa raw message, attachment text hoặc connector response không được normalize vào evidence bundle. User prompt chỉ là input không tin cậy, không bao giờ là evidence để xác nhận một fact doanh nghiệp.

## 5. Bounded context và contract dữ liệu

### 5.1 Company Service: Executive Context Snapshot

Thay vì để agent gọi hàng loạt endpoint lẻ hoặc query database, bổ sung một read-model cho executive use case tại `services/company`. Endpoint lấy Workspace từ `TenantContext` server-authoritative và trả về tập dữ liệu có giới hạn, có thời điểm chụp và có source IDs.

```ts
export interface ExecutiveContextSnapshot {
  readonly schemaVersion: "company.executive-context/v1";
  readonly workspaceId: string;
  readonly generatedAt: string;
  readonly dataAsOf: string;
  readonly operations: {
    readonly tasks: ReadonlyArray<ExecutiveTaskEvidence>;
    readonly totals: { readonly open: number; readonly blocked: number; readonly overdue: number };
  };
  readonly strategy: {
    readonly objectives: ReadonlyArray<ExecutiveObjectiveEvidence>;
    readonly projects: ReadonlyArray<ExecutiveProjectEvidence>;
  };
  readonly finance?: {
    readonly period: string;
    readonly metrics: ReadonlyArray<ExecutiveMetricEvidence>;
    readonly completeness: "available" | "not_available";
  };
  readonly evidence: ReadonlyArray<ExecutiveEvidenceRef>;
}
```

Nó phải áp các giới hạn server-side (ví dụ: 50 task nguy cơ cao nhất, 20 objective/project) và chỉ trả field cần thiết để tư vấn. Không trả bí mật, token, attachment, audit payload thô hoặc dữ liệu cá nhân không cần thiết. `finance` chỉ xuất hiện khi Finance service đã có read contract được owner phê duyệt; thiếu nó là `not_available`, không phải số 0.

### 5.2 COSA capability: một cổng đọc duy nhất

`apps/cosa/capabilities/executive_context_read.py` đăng ký `executive.context.read` với risk `LOW`. Handler lấy `workspace_id` duy nhất từ `CapabilityRequest` context do run tạo ra, gọi Company Service bằng service-to-service credential/membership context và chuẩn hóa response thành evidence bundle. Input model chỉ cho phép các filter không làm thay đổi scope:

```json
{
  "as_of": "optional ISO-8601 timestamp",
  "domains": ["operations", "strategy"],
  "focus": "delivery_risk | objectives | financial_health | general"
}
```

`workspace_id` không được tin từ payload. Capability phải overwrite/reject `workspace_id` supplied by model. Company handler tiếp tục authorize theo token/context server-side và query `id + workspace_id` cho mọi entity tenant-owned.

### 5.3 Agent profile và deterministic routing

Bổ sung một profile duy nhất `executive_advisory`, map chính xác đến `cosa.agents.executive-advisory`. Chuyển worker từ logic substring hiện tại (`"finance" in agent_profile`) sang registry immutable, ví dụ `AGENT_SPECS_BY_PROFILE`. API chỉ nhận enum profile đã allowlist. Profile lạ phải trả 422/400 trước khi tạo conversation/task, không âm thầm chạy Operations.

Prompt của profile phải buộc thứ tự xử lý:

1. xác định loại câu hỏi và scope có thể đọc;
2. gọi `executive.context.read`;
3. phân biệt fact/evidence với inference và assumption;
4. tạo Executive Brief có citations;
5. chỉ đưa proposal, không thực thi action.

Không cần `SupervisorCoordinator` hoặc nhiều LLM call trong Phase A. Một profile có tool read-only, one-shot evidence synthesis giúp latency, chi phí và bề mặt lỗi thấp hơn. Council chỉ được cân nhắc ở Phase C, sau eval rubric chứng minh cần thiết.

### 5.4 Artifact và render UI

Sau run hoàn thành, worker lưu:

- Markdown assistant message để tương thích chat hiện có;
- `WorkspaceArtifact` metadata có `artifact_kind="executive_brief"`, `media_type="application/vnd.cosa.executive-brief+json"` và `object_ref` opaque;
- một `ArtifactContentRepository` generic trong Agent Core lưu body JSON canonical theo `(artifact_id, workspace_id)`, checksum và media type. `WorkspaceArtifact` vẫn chỉ là metadata/lineage; không nhét body vào `MessageRecord.content`, `object_ref` hoặc event payload.

API phải có route scoped để đọc content theo artifact ID, ví dụ `GET /agent/artifacts/{artifact_id}/content`. Route lookup metadata/content theo `workspace_id` từ identity rồi mới trả schema. Flutter không tự dereference `object_ref` và không nhận JSON body từ session list endpoint. Nó render summary/findings/actions/citations theo structured schema. Citation bấm vào trang detail nội bộ chỉ khi người dùng có Workspace membership và quyền xem đối tượng gốc; nếu không, UI chỉ hiển thị excerpt đã redaction.

## 6. Security, privacy và safety

### 6.1 Cổng bắt buộc trước Phase A

1. Hoàn tất workspace-first tenancy có `make tenancy-check` xanh. Không mở Advisory trong lúc codebase còn truyền `company_id` hoặc fallback tenant không fail closed.
2. Sửa authorization ở `services/cosa/handlers/workspace-schedule.handler.ts`: `createScheduleEndpoint` và `listSchedulesEndpoint` hiện verify platform token nhưng cần gọi cùng `verifyWorkspaceMembership(workspaceId, authorization)` như connector endpoints. `runScheduleNowEndpoint` cũng phải chứng minh schedule thuộc Workspace đã verify.
3. Sửa propagation runtime ở `packages/agent_integrations/openai_agents_sdk/kernel.py`: current adapter tạo `GatewayExecutionRequest` thiếu `workspace_id`, principal và context khi gọi tool. Trước khi thêm capability mới, mọi request phải mang exact run/principal/workspace/conversation/policy context đến Gateway; capability không còn được quyền fallback Workspace mặc định.
4. Thêm test cross-workspace cho các endpoint schedule và runtime tool invocation; lỗi truy cập trả không tiết lộ tồn tại của schedule/Workspace khác.

Đây là điều kiện ra mắt, dù scheduled executive brief chỉ nằm ở Phase D. Không nên nhân rộng một profile mới trên control plane trước khi đường schedule chung được closed.

### 6.2 Prompt injection và dữ liệu không tin cậy

- Phase A không accept attachment/URL/RAG document như context advisory. Nếu message có attachment, API hoặc advisory policy trả lời rằng attachment chưa được hỗ trợ cho executive evidence.
- Text của business entity được coi là **untrusted data**, đóng gói trong JSON evidence bounded-size; prompt quy định không làm theo instruction có trong dữ liệu.
- Phase B ingest dùng trust label, MIME/size/quarantine, parser sandbox, source provenance, dedup/hash, human review cho POLICY/BUSINESS_SNAPSHOT, và retrieval filter trước khi model nhìn thấy text.
- Không log raw evidence/PII vào SSE, error string, tracing attribute hoặc model prompt debug. Redaction xảy ra trước artifact/render/log.

### 6.3 Memory và knowledge

Agent Core đã có `workspace_id`, lifecycle và provenance cho memory; sensitivity hiện là metadata, chưa là authorization layer. Do đó Phase A **không ghi memory**.

Phase B phải:

1. thêm `KnowledgeAccessContext` (workspace, principal/role, allowed authority classes, sensitivity ceiling) ở Agent Core contract;
2. buộc Knowledge/Memory repository filter theo access context, không chỉ `workspace_id`;
3. phát triển hybrid retrieval PostgreSQL + pgvector/BM25 theo `workspace_id`, authority filter, freshness và source-version pinning;
4. chỉ promote decision/initiative khi rule deterministic tạo proposal có `source_run_id`, evidence refs và human approval; promotion không sửa Company business truth.

### 6.4 Governance

Capability spec là source of truth về risk, input/output schema và connector requirement. Executive Advisory không được whitelist bằng prompt. Mọi future action vẫn phải đi qua Capability Gateway với invocation identity, payload hash, policy snapshot, approval binding, idempotency và audit event.

## 7. Phased delivery và decision gates

| Phase | Deliverable | Chỉ mở khi | Không bao gồm |
| --- | --- | --- | --- |
| Gate 0 | Workspace/schedule authorization hardening | `make tenancy-check` và test schedule cross-workspace xanh | UI/agent mới |
| A | Read-only Executive Brief, snapshot capability, evidence artifact, eval tối thiểu | Gate 0 + vertical/API tests xanh | RAG, attachments, write, connectors, council |
| B | Governed knowledge + hybrid retrieval + cited brief | Phase A factuality/citation threshold đạt, access-control test xanh | auto promotion/write |
| C | Role packs và conditional council | eval chứng minh single profile không đủ; budget/latency cap | always-on 8-agent fan-out |
| D | Scheduled digest, approved connectors, decision/initiative proposals | schedule grant, connector grant, review/audit dashboard xanh | autonomous external action |
| E | Action workflows | per-capability policy/approval/idempotency/evals đạt | global “approve all” |

**Definition of done Phase A:**

- A user authorized in Workspace A cannot create, view, run, retrieve artifact/evidence, or schedule an executive advisory resource in Workspace B.
- `executive_advisory` resolves a published, pinned Prompt/ModelPolicy/AgentSpec; unknown profile is rejected.
- A completed brief contains `data_as_of`, at least one evidence ref per factual finding, and `insufficient_evidence` if no source supports a conclusion.
- Existing Operations and Finance paths retain behavior; Finance write requires existing approval flow.
- Test suite has unit, vertical-slice, tenant-isolation and eval coverage; CI runs them before deploy.

## 8. Evaluation framework

Store scenarios under a COSA-owned path, not copied blindly from OpenExecutive. Each case needs: fixed workspace fixture, pinned context snapshot, expected evidence IDs, expected safety decision and deterministic scoring rubric.

| Suite | Example assertion |
| --- | --- |
| Tenant isolation | Prompt in Workspace B cannot cause citation/reference to an entity in Workspace A. |
| Grounded factuality | Every finding uses a provided source ID; invented metrics score zero. |
| Abstention | Missing finance context yields `not_available`/open question, not fabricated cash figure. |
| Prompt injection | A task title containing “ignore previous instruction” is evidence text, not a command. |
| Action safety | “Create payment / email board” produces proposal only; no write capability invocation. |
| Regression | Operations and Finance profiles preserve spec resolution and approval behavior. |
| Quality | Brief has concise summary, clear confidence, citation coverage and actionable human decision request. |

Release thresholds should start conservative: 100% tenant/action-safety tests; 100% citation coverage for factual findings; 0 invented source IDs; and manually reviewed gold scenarios before a beta Workspace. Track latency, cost, capability errors, coverage, abstention rate, citation click failures and policy denials by spec version—never raw sensitive prompt/evidence content.

## 9. File ownership map

| Area | Owns | Must not own |
| --- | --- | --- |
| `services/company` | `ExecutiveContextSnapshot`, tenant-scoped business query and canonical entity IDs | LLM prompt, orchestration, vector retrieval policy |
| `apps/cosa` | agent profile/spec seed, capability adapter, worker selection, API/artifact integration | direct business-table access, hidden governance bypass |
| `packages/agent_core` | generic retrieval/access contracts, governance, artifact/run provenance | Company HTTP client or service-specific DTO |
| `packages/agent_recipes` / skillpacks | versioned role/evaluation guidance after tenancy gate | production activation by documentation alone |
| `services/cosa` | workspace connector/schedule/policy control-plane authorization | business truth or unscoped global schedule visibility |
| Flutter | profile selection and structured brief presentation | deriving Workspace authority or calling services bypassing COSA |

## 10. Risks và cách tránh

| Risk | Biện pháp |
| --- | --- |
| “Executive” thành persona có quyền cao | Autonomy vẫn L0 observe; quyền do capability/policy, không do title. |
| Hallucination tóm tắt số liệu | Evidence contract + no-citation/no-claim gate + abstention. |
| Data overload/latency | Snapshot bounded server-side; lazy/conditional role expansion ở phase sau. |
| Rò Workspace qua profile/schedule/artifact | Enum validation, exact profile map, membership guard, scoped repository tests. |
| Prompt injection từ task/document | Không ingest attachment Phase A; untrusted-data isolation Phase B. |
| Coupling Agent Core với Company | Contract/adapter boundary, no service imports in `packages/agent_core`. |
| Scope creep thành CRM/ERP AI | Giữ decision/action ở Company service và mở từng capability qua governance. |

## 11. Tài liệu thực thi

Kế hoạch có thể triển khai ngay cho Phase A nằm tại [`docs/superpowers/plans/2026-08-27-executive-advisory-phase-a.md`](../plans/2026-08-27-executive-advisory-phase-a.md). Phase B–E chỉ được lập implementation plan riêng sau khi pass acceptance gate của phase trước.
