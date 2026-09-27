# COSA: phân tích toàn diện và đề xuất hoàn thiện

Ngày: 2026-09-27. Cơ sở: `main` tại `f55e960`, sau PR vutasoftvn/javis-saas#12.

Phương pháp: đọc code và đo trực tiếp trên repo (đếm file, liệt kê catalog agent và capability,
chạy test, tái hiện lỗi trên Postgres thật). Mỗi nhận định có đường dẫn để kiểm lại. Những gì
chưa xác minh được ghi rõ là "cần xác minh". Trục trạng thái dùng đúng quy ước của repo:
ACCEPTED / IMPLEMENTED / WIRED / VERIFIED / PRODUCTION.

## 1. Tóm tắt

COSA đã có **bộ khung kiến trúc đúng và chặt**:
- tách 4 vùng (Experience, Control Plane, Company Business, Agent Platform);
- governance xác định bằng code;
- delegation token một chiều;
- AgentSpec pin exact-hash;
- fail-closed ở hầu hết biên.

Điểm yếu nằm ở phần **"thịt" trên khung**:
- agent đông nhưng phần lớn không có công cụ hành động;
- chat không nhớ lượt trước;
- chưa có kết nối ra hệ thống bên ngoài;
- chưa có kiểm soát chi phí theo workspace;
- repository Postgres có lỗi mà test InMemory không bắt được.

Ưu tiên đề xuất:
1. **Làm chat thành co-founder thật:** nhớ hội thoại, điều phối nhiều agent.
2. **Cho agent công cụ làm việc thật**, có governance.
3. **Chặn rủi ro vận hành SaaS:** chi phí, rate-limit, parity Postgres.
4. **Kết nối ra ngoài** qua MCP.
5. **Đo chất lượng agent** bằng eval chạy định kỳ.

## 2. Hiện trạng đo được

| Vùng | Quy mô (dòng code, không tính test) | Ghi chú |
|---|---|---|
| Experience: `frontend/lib` | ~105k dòng Dart, 25 module, 209 file test | Coverage gate chỉ 46% và loại trừ views/widgets (`.github/workflows/quality.yml:44`). |
| Control Plane: `services/cosa` | ~11k dòng TS, 82 endpoint, 55 file test | Identity/organization do `backend/core` quản lý (cutover đã làm). |
| Company Business: `services/company` | ~76k dòng TS, 453 endpoint, 272 file test | Business truth, WGA, founder assets. |
| Agent Platform: `packages/agent` + `apps/cosa` | ~38k + ~43k dòng Python, 94 route | 553 file test Python; coverage gate 80% / 78%. |
| Contract MVP: `shared/contracts/mvp-surface.json` | 145 capability (3 disabled) | Chỉ ~23% trong số ~630 endpoint nằm trong contract. |
| Skill | 129 skillpack, 40 skill được pin vào agent | 153 eval suite là eval *policy* (accept/reject), không phải eval chất lượng câu trả lời. |

**Catalog agent** (`apps/cosa/agents/catalog.py`, đếm qua `seeded_entries()`):

| Nhóm | Số lượng | Capability |
|---|---|---|
| operating: operations, founder_assistant, finance, marketing, customer_support | 5 | 4–20 capability, có ghi/draft |
| operating: research_intelligence, strategy, sales, coding, product, people, security, legal, data, ai_governance | 10 | 3–4 capability, **chỉ đọc** (và chủ yếu đọc ngữ cảnh chung) |
| executive: CEO/CFO/CTO/CMO/COO/… | 15 | **0 capability**, chạy như cố vấn trong Executive Board |
| system: customer_support_autopilot, kickoff_suggestion | 2 | — |
| `crm` (có trong startup team) | 1 | **không có spec**: chat bị `unknown_agent_profile`, worker WGA bị fail-closed |

## 3. Điểm mạnh cần giữ

- **Governance xác định:** `CosaPolicyEngine` chỉ siết, không nới. Approval bind
  `run_id + tool_call_id + checkpoint_ref`. Có statutory floor.
- **Delegation một chiều theo phạm vi** `{workspace_id, run_id, capability_ids}`. Secret mặc định
  bị chặn ở production (`apps/cosa/auth/jwt.py`).
- **Spec pin exact-hash** + bảng ánh xạ tường minh profile→spec, chống drift khi rolling deploy.
- **Fail-closed nhất quán:** thiếu project scope, profile lạ, capability ngoài profile.
- **Gate chất lượng phong phú:**
  - boundary, route-auth allowlist, contract-freeze, migration Expand-only, schema fingerprint;
  - secret scan, dependency audit;
  - durability, migration rollback.
- **Vận hành:** OTEL collector, Prometheus, 5 alert rule, backup có kiểm tra độ tươi và
  restore-test (`scripts/backup/`), Caddy, ADR rollback N-1.

## 4. Lỗ hổng và rủi ro (xếp theo mức ảnh hưởng)

### P0: ảnh hưởng trực tiếp giá trị cốt lõi hoặc rủi ro vận hành

**G-1. Chat không nhớ lượt trước.**
- `ADR-CONV-001` quyết định launch single-turn. Code hiện tại vẫn vậy: worker và kernel không
  gọi `list_messages`, prompt chỉ có lượt hiện tại.
- Với sản phẩm định vị "Co-Founder", đây là khoảng cách UX lớn nhất: founder phải nhắc lại ngữ
  cảnh mỗi câu.
- Abstraction `apps/cosa/conversations/ports.py` và `stub.py` là code chết (chính ADR ghi vậy).

**G-2. Repository Postgres lệch với InMemory, CI không bắt được.**
- Bằng chứng: `PostgresRunRepository.list_runs` truy vấn cột không tồn tại, làm 500 cả dashboard.
  `ProjectActivityEventDTO` bắt buộc field mà Postgres lưu NULL, làm hỏng list và SSE. Cả hai
  sửa ở `997606b`.
- Test route dùng InMemory nên luôn xanh. Chắc chắn còn lỗi cùng loại ở các repository khác.

**G-3. Không có kiểm soát chi phí LLM theo workspace.**
- Token chỉ được ghi vào metric Prometheus (`record_model_tokens`), không có sổ cái usage theo
  workspace/run.
- `budget_usd_limit` trên profile **chưa được enforce**; code tự ghi chú rõ
  (`apps/cosa/models/providers.py:192-197`).
- Metric còn gắn nhãn model theo `spec.model_policy` thay vì route thật, nên sai khi workspace
  dùng profile riêng hoặc fallback.
- Với SaaS trả phí, một workspace có thể đốt ngân sách provider không giới hạn.

**G-4. Không có rate-limit ở biên.**
- Không thấy rate-limit ở Caddy (`deploy/central_vps/Caddyfile`), FastAPI (`apps/cosa/api/app.py`
  chỉ có CORS và MaxBodySize) hay Encore.
- Chỉ có giới hạn riêng cho sweep WGA (`WGA_MAX_TASK_RUNS_PER_WORKSPACE_PER_DAY`).
- Endpoint tạo run (`POST /agent/conversations/:id/messages`) là điểm tốn tiền nhất nhưng chưa
  có quota.

### P1: giới hạn năng lực sản phẩm

**G-5. Agent đông nhưng "mỏng".**
- 10/15 agent vận hành chỉ có 3–4 capability đọc; 15 agent executive không có tool nào.
- Khi WGA giao task cho `strategy`/`sales`/`coding`… agent chỉ viết được văn bản.
- Giờ đã có guard `capability_not_in_profile`, nên task yêu cầu hành động sẽ bị chặn. Đúng về
  an toàn, nhưng vòng tự động hoá chỉ thật sự chạy với 5 domain.
- `crm` có trong startup team nhưng không có spec.

**G-6. Không có kết nối ra hệ thống thật.**
- Framework connector có (`connector_routes.py`: install/authorize/grant/revoke, vault), nhưng
  connector duy nhất là `sandbox-read` MCP.
- Chưa có email, lịch, kế toán/ngân hàng, CRM ngoài, kênh chat khách hàng.
- `packages/agent_integrations` có adapter MCP, A2A, AG-UI, LangGraph… nhưng runtime chính chỉ
  dùng OpenAI Agents SDK và LiteLLM.

**G-7. Chưa có điều phối nhiều agent trong chat.**
- Mỗi conversation gắn một `active_agent_profile`. Founder phải tự chọn agent.
- Kernel contract có "handoff agent-as-tool" (`packages/agent/contracts/kernel.py`) nhưng chat
  không dùng.
- WGA đã giải quyết phần bất đồng bộ (lập kế hoạch rồi giao việc). Phần đồng bộ ("hỏi CFO về
  runway ngay trong cuộc chat này") thì chưa có.

**G-8. Memory dài hạn chưa tham gia run.**
- `packages/agent/memory` có service/store/retention, nhưng trong `apps/cosa` chỉ dùng để xoá
  theo retention (`compliance/retention_coordinator.py`). Không có recall khi chạy.
- Knowledge (pgvector) đã nối qua `workspace.context.read`.

**G-9. Đo chất lượng agent còn thiếu.**
- 153 eval suite trong `evals/` là eval policy (accept/reject scope).
- Eval chất lượng câu trả lời chỉ có cho customer support (`apps/cosa/evals/`).
- CI có job `quality-live-provider`, nhưng không có bộ eval hồi quy cho prompt và skill của 30
  agent. Đổi prompt hay skill hiện không có tín hiệu tốt/xấu hơn.

**G-10. Founder-configurable assets mới triển khai một phần.**
- Đã có handler authoring/deployment/query (`services/company/operations/handlers/founder-asset-*`)
  và event `founder.asset.commanded.v1`.
- Cần xác minh các bước lifecycle clone → validate → eval → review → publish theo spec đã duyệt
  đã khép kín chưa. Theo CLAUDE.md, đây vẫn là "design đã duyệt, chưa là runtime capability".

### P2: nợ kỹ thuật và chất lượng

**G-11. File "thần thánh" ở Flutter và worker.** Ví dụ:
`founder_command_center_controller.dart` 1283 dòng, `hologram_hub_view.dart` 1442 dòng,
`apps/cosa/worker/handlers.py` 1430 dòng. Coverage frontend 46% và loại trừ views/widgets.

**G-12. Contract MVP chỉ phủ ~23% endpoint.** Route ngoài contract dựa vào allowlist, nên drift
giữa frontend và backend chỉ được bắt một phần.

**G-13. Tài liệu lệch code.**
- CLAUDE.md tham chiếu nhiều spec/plan "không còn trong cây".
- Danh sách ADR trong CLAUDE.md thiếu `ADR-EXECUTIVE-BOARD-001` và `ADR-WORKSPACE-INVITATION-001`.
- `ADR-COSA-DELEGATION-002` vẫn PROPOSED dù cơ chế đã chạy.
- CLAUDE.md yêu cầu "code trực tiếp trên `main`", mâu thuẫn với quy trình nhánh + PR thực tế.

**G-14. Abstraction chết hoặc dở dang.**
- `conversations/ports.py` và `stub.py`.
- `IWorkflowOrchestration` có method `NotImplementedError`.
- `CliBridgeModel` không hỗ trợ streaming.
- Stream Project Activity trước đây không có live fanout (đã sửa ở `f055075`).

**G-15. Môi trường dev và agent không chạy được gate Encore.**
- Session cloud không cài được `encore` CLI/runtime, nên `services-test-*` và `e2e-test` chỉ
  chạy được trên CI.
- Mọi thay đổi company được merge khi chưa chạy test DB tại chỗ.

## 5. Đề xuất: lộ trình 4 đợt

Nguyên tắc chung:
- Mỗi hạng mục viết plan riêng trong `docs/superpowers/plans/` trước khi làm.
- TDD. Migration chỉ Expand.
- Không tạo agent mới khi Skill/Tool/Workflow giải quyết được (quy tắc 3).

### Đợt 1: an toàn vận hành và độ tin cậy (G-2, G-3, G-4, G-15)

1. **Parity test Postgres ↔ InMemory.**
   - Một bộ contract test dùng chung, chạy cho cả hai implementation của mỗi repository: run,
     conversation, artifact, project activity, workforce, approval.
   - Chạy trong job `durability`/`quality-integration` có Postgres.
   - Xong khi: mỗi method public của repository Postgres có ít nhất một test trên Postgres thật.
2. **Sổ cái usage + ngân sách.**
   - Bảng `agent.run_usage` (Expand) ghi token/cost theo `workspace_id, project_id, run_id,
     profile_id`, lấy từ route thật, kể cả fallback.
   - Enforce `budget_usd_limit` của profile và quota tháng của workspace **trước khi** dựng
     client. Vượt ngưỡng thì fail-closed với `user_message` rõ.
   - Sửa nhãn metric.
3. **Rate-limit.**
   - Tại Caddy theo IP/route cho endpoint public.
   - Theo workspace cho `POST .../messages` và endpoint tạo run (quota phút/ngày, trả 429 +
     `Retry-After`).
4. **Encore trong môi trường dev/agent.**
   - Viết SessionStart hook hoặc devcontainer cài `encore` từ nguồn được phép (mirror nội bộ nếu
     proxy chặn GitHub), để `make verify` chạy đủ trước khi merge.

### Đợt 2: chat thành Co-Founder thật (G-1, G-7, G-8)

1. **Lịch sử hội thoại có ngân sách token.**
   - Nạp N lượt gần nhất từ `PostgresConversationRepository` vào prompt; lượt cũ hơn được tóm
     tắt cuốn chiếu và lưu làm artifact có hash.
   - Thay `ADR-CONV-001` bằng ADR mới. Xoá `ports.py`/`stub.py`.
   - Test: hội thoại nhiều lượt qua process thật.
2. **Điều phối trong chat.**
   - `founder_assistant` làm router: gọi agent chuyên môn như tool (agent-as-tool) với scope và
     capability của agent đích, không nới quyền.
   - Mỗi lượt gọi là một child run có `run_id` riêng, hiện trong timeline.
   - Câu hỏi đa lĩnh vực cần quyết định thì chuyển sang Executive Board (đã có).
3. **Memory dự án có governance.**
   - Chỉ ghi "fact" founder xác nhận (quyết định, ràng buộc, ưu tiên), không ghi suy diễn LLM.
   - Recall theo `project_id` vào `session_context`. Retention/xoá đã có sẵn.

### Đợt 3: agent có công cụ làm việc thật (G-5, G-6)

1. **Ma trận coverage capability theo domain.** Với 10 agent chỉ-đọc, xác định 2–3 capability
   *draft* an toàn mỗi domain. Ví dụ:
   - sales: `project.crm.lead.draft`, `engagement.message.draft`;
   - product: `product.decision.draft`;
   - legal: `legal.issue.draft`;
   - people: `people.plan.draft`.

   Draft là artifact chờ founder duyệt, không có side-effect ngoài. Cập nhật prompt phân rã WGA
   để chỉ route task tới agent có capability.
2. **`crm`:** hoặc gộp vào `sales` (khuyến nghị, theo quy tắc 3) và bỏ khỏi startup team, hoặc
   tạo spec riêng.
3. **Connector MCP ưu tiên**, qua vault và grant hiện có, chỉ đọc trước:
   - email và lịch (tóm tắt, soạn nháp);
   - kế toán/ngân hàng (đọc giao dịch cho finance);
   - kênh khách hàng cho customer_support.

   Hành động gửi hoặc ghi ra ngoài luôn REQUIRE_APPROVAL (quy tắc 8).
4. **Executive agents:** giữ vai trò cố vấn không tool, nhưng cho đọc đúng dữ liệu domain (CFO
   đọc finance snapshot, CTO đọc engineering evidence) qua capability chỉ đọc, để lời khuyên dựa
   trên số liệu thật.

### Đợt 4: chất lượng, tuỳ biến và dọn nợ (G-9, G-10, G-11..14)

1. **Eval chất lượng agent.**
   - Bộ case golden theo domain chạy với model giả (deterministic) trong CI và model thật hằng
     đêm (`quality-live-provider`).
   - Chấm bằng rubric và LLM-judge có seed. Đổi prompt/skill phải kèm diff điểm eval.
2. **Hoàn tất lifecycle founder asset** (clone → eval → publish) theo spec đã duyệt, rồi mới mở
   canvas Hướng 3.
3. **Tách file lớn.**
   - `founder_command_center_controller` → controller chat, WGA, dashboard.
   - `handlers.py` → chat run, resume, schedule.
   - Nâng coverage frontend dần (46 → 60), tính cả controller.
4. **Mở rộng contract MVP** cho mọi route frontend gọi. Allowlist có hạn.
5. **Đồng bộ tài liệu:**
   - cập nhật CLAUDE.md: danh sách ADR, quy trình nhánh/PR, xoá tham chiếu tới file đã xoá;
   - đổi `ADR-COSA-DELEGATION-002` sang ACCEPTED/IMPLEMENTED nếu đúng thực tế.

## 6. Quyết định cần founder chốt

1. **Thứ tự đợt 1 và đợt 2.** Khuyến nghị làm đợt 1 trước nếu sắp thu phí (chi phí, rate-limit),
   làm đợt 2 trước nếu đang thử nghiệm với ít founder.
2. **Chính sách ngân sách:** quota theo gói (plan) ở `services/cosa`, hay chỉ ngân sách do
   workspace tự đặt?
3. **Ưu tiên connector** cho thị trường mục tiêu: email/lịch, kế toán hay kênh khách hàng.
4. **`crm`:** gộp vào `sales` hay giữ agent riêng?
5. **Memory:** chỉ fact founder xác nhận (khuyến nghị), hay cho agent tự đề xuất fact chờ duyệt?

## 7. Việc có thể làm ngay, rủi ro thấp

- Sửa nhãn metric token theo route thật (G-3, một phần).
- Xoá `apps/cosa/conversations/ports.py` và `stub.py` (G-14; cần xác nhận xoá theo quy tắc 10).
- Cập nhật danh sách ADR và quy trình nhánh trong CLAUDE.md (G-13).
- Test parity đầu tiên cho `PostgresProjectActivityRepository` và phần còn lại của
  `PostgresRunRepository` (G-2): đây là hai nơi vừa lộ lỗi schema/DTO. `list_runs` đã có test.

## 8. Nhật ký triển khai (2026-09-27, nhánh `claude/festive-fermi-ami9pa`)

Các quyết định ở mục 6 áp dụng theo mặc định khuyến nghị:

- đợt 1 làm trước;
- quota token theo workspace (env), kèm ngân sách USD theo model profile;
- `crm` gộp vào `sales`;
- memory chỉ lưu fact founder đã xác nhận;
- connector MCP chỉ đọc trước.

| Việc | Trạng thái | Commit |
|---|---|---|
| G-2 parity InMemory/Postgres (run, conversation, artifact, activity, memory) | IMPLEMENTED | `246a1f8`, `09cdd31` |
| G-3 sổ cái `models.run_usage`, chặn quota/ngân sách trước run | IMPLEMENTED | `8f8d651` |
| G-4 rate limit theo IP và tạo run (429 `RATE_LIMITED`) | IMPLEMENTED | `3fd98d1` |
| G-15 hook SessionStart (venv, npm, Flutter, Postgres + pgvector) | IMPLEMENTED; Encore CLI cài theo kiểu best-effort | `14a9fbb` |
| G-1 lịch sử chat trong prompt (ADR-CONV-002) | IMPLEMENTED | `88841ac` |
| G-7 `agent.consult` (child run chỉ đọc, sâu 1 cấp) | IMPLEMENTED | `627b5c2` |
| G-8 fact dự án: thẻ `memory_confirm`, API `/agent/projects/{id}/memory/facts`, đưa vào prompt | IMPLEMENTED | `09cdd31` |
| Regression PR #12: pin company operations 1.3.0 → `spec_hash_mismatch` | FIXED: worker chạy đúng version đã pin, lấy từ registry | `09cdd31` |
| G-5 9 capability `.draft` và route WGA cho product/people/security/legal/data | IMPLEMENTED | `7efdd00` |
| G-5 `crm` | Giữ key vì DB đã có dòng dữ liệu (migration chỉ Expand); nhãn đổi thành "merged into Sales"; task CRM route về `sales` | `7efdd00` |
| G-6 connector MCP theo manifest (`COSA_MCP_CONNECTORS_FILE`) | IMPLEMENTED (khung). Chưa có server email/lịch/kế toán thật | `7efdd00` |
| G-9 eval: case định tuyến WGA (CI) và rubric theo domain (`live_provider`, nightly) | IMPLEMENTED | đợt 4 |
| G-11 tách `worker/scheduled_tasks.py` và `founder_command_center_wga.dart` | IMPLEMENTED (bước đầu) | đợt 4 |
| G-13 CLAUDE.md: danh sách ADR, danh sách agent, nhánh phiên cloud, quy trình đổi spec | IMPLEMENTED | đợt 4 |

Có chủ đích chưa làm, hoặc thay đổi so với đề xuất:

- **Executive đọc dữ liệu domain (đợt 3, mục 4):**
  - Không thêm capability cho spec executive. Spec executive "capability-empty" là
    contract có test khoá và có overlay pin hash (`executive-advisor-overlays`).
  - Trong chat, lời khuyên dựa trên số liệu đi qua `agent.consult`: agent chuyên môn
    (finance, product…) đọc bằng capability chỉ đọc của chính nó.
  - Trong Executive Board, dữ liệu đi qua evidence founder chọn khi frame.
- **Secret connector theo workspace:**
  - Hiện dùng credential server qua `auth_env`.
  - Bước sau: lấy `secret_ref` của grant từ vault.
  - Tool `write` đã bị chặn hai lớp: approval ALWAYS, và control plane không có
    scope ghi.
- **G-10 lifecycle founder asset (clone → eval → publish):**
  - Chưa làm. Spec 2026-09-13 không còn trong cây.
  - Cần design và plan được duyệt trước khi code (quy tắc 13).
- **G-12 mở rộng contract MVP:**
  - Mới thêm 3 route memory.
  - Việc đưa các route còn lại ra khỏi allowlist nên tách thành một đợt riêng.
- **ADR-COSA-DELEGATION-002:** đã ở trạng thái ACCEPTED & IMPLEMENTED từ 2026-09-04,
  không cần đổi.

Lỗi test có sẵn trước đợt này:

- `tests/contracts/test_automation_contract.py` và `test_founder_trial_mvp_surface.py`
  fail từ commit khởi tạo:
  - tham chiếu migration `003_cosa_automation_mvp.up.sql` không tồn tại;
  - danh sách `PENDING_EVIDENCE` đã lỗi thời.

  CI không chạy thư mục này.
- `tests/apps/cosa/control_plane/test_connector_lifecycle_e2e.py` cần DB `cosa` thật
  (lỗi ở bước setup khi chạy local).
- `make agent-test` có 7 lỗi RLS/skill-improvement khi chạy trên DB tạm bằng superuser
  (RLS không áp dụng cho superuser).
- Gate Encore (`services-test-*`) và e2e cross-plane chỉ chạy được trên CI (container
  không có Encore CLI). Test thuần của `autonomy-classifier` đã chạy bằng `vitest`.
