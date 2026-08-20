# COSA G1 × G2 Reconciliation Roadmap
## Phân tích G1 (Capability, Learning & Execution Enhancement Spec) đối chiếu codebase thật & đề xuất hoàn thiện app

**Trạng thái:** Đang triển khai — Phase 0A, 0B, 1A đã xong hoàn toàn (xem §12), gồm cả ContextAssembler + Mission DRAFT/confirm state machine. Tiếp theo là Phase 1B (Capability Registry).
**Ngày:** 2026-08-19
**Quan hệ tài liệu:** Đối chiếu `G1-COSA_Capability_Learning_Execution_Enhancement_Spec_2026-08-19.md` với codebase thật, dựa trên `G2-COSA_Codebase_Consolidation_Refactor_Spec_2026-08-19.md` làm khung phase
**Đối tượng:** Founder / Claude Code / Dev team
**Phạm vi tài liệu này:** Phân tích + đề xuất + triển khai thật (§9-§12 là nhật ký triển khai, không chỉ đề xuất).

---

# 0. Bối cảnh

G1 tự nói rõ nó **phụ thuộc** vào G2 hoàn tất trước ("Implementation Order chốt: 1. Hoàn thành P0 consolidation/security hiện tại... Không xây self-learning trước khi runtime truth ổn định"). G2 tự chẩn đoán codebase có "nhiều thế hệ kiến trúc song song" và "một số model/entity bị trùng vai trò".

Sau khi audit trực tiếp codebase (3 nhánh explore song song + đọc trực tiếp các file quyết định + verify các claim quan trọng nhất bằng grep/read trực tiếp), sự thật là: **mức độ trùng lặp nghiêm trọng hơn cả G2 tự chẩn đoán** — không phải 2x mà là 3-4x trên hầu hết mọi khái niệm mà G1 muốn thêm mới. Nếu triển khai G1 đúng như văn bản (tìm entity tương đương rồi "mở rộng") mà không có quyết định canonical rõ ràng trước, rủi ro cao là sẽ mở rộng nhầm bản sao sẽ bị xóa, hoặc tạo thêm bản sao thứ 4/5.

Mục tiêu tài liệu này: chốt sự thật hiện trạng, đưa ra **quyết định canonical dứt khoát** cho từng khái niệm trùng lặp, và một **roadmap theo phase** để hoàn thiện app — kết hợp đúng phần G2 (chưa xong) với 6 primitive của G1 (đúng thứ tự phụ thuộc mà G1 tự đặt ra).

---

# 1. Sự thật hiện trạng (ground truth đã verify trực tiếp trong codebase)

## 1.1. Capability bị định nghĩa 3 lần, 3 shape khác nhau
- `backend/app/workforce/agents/capabilities/registry.py` — frozen dataclass, `CAPABILITY_CATALOG` dict ~40 entry hard-code, `RiskLevel` enum L0-L5.
- `backend/app/business/packs/schemas.py` — Pydantic, load từ YAML `business/packs/factory/*/capabilities/*.yaml` (11 pack theo **business function**, không theo 5 Domain Agent).
- `backend/app/founder_os/strategy/models.py` — SQLAlchemy thật, table `capability_definitions`, workspace/brain-scoped, đi cùng `WorkspaceAgent.capability_keys_jsonb`. **Đây là ứng viên canonical tốt nhất** — nhưng nằm ngoài mọi path mà G1 §4.2 bảo tìm trước (`workforce/capabilities/*`, `workforce/models.py`...).

## 1.2. Skill có ít nhất 4 shape Python, 3 cây thư mục SKILL.md riêng biệt
`workforce/skills/*`, `workforce/agents/skills_library/*`, `business/packs/factory/*/skills/*` — không cây nào liên kết với model DB thật `SkillRegistryItem` (table `global_skill_registry`, đã có lifecycle candidate→evaluation→pending_approval→active→deprecated).

Đặc biệt: `SkillTrajectoryCandidate` (table `skill_trajectory_candidates`) — docstring ghi rõ đây là **"Learning candidate extracted from completed mission trajectory (Spec §62)"**, tức ai đó đã bắt đầu code nửa Skill-candidate của Learning Review Worker mà G1 đang đề xuất lại — nhưng `create_candidate_from_trajectory()` **chỉ được gọi từ test**, chưa bao giờ chạy production.

## 1.3. `AgentRun` bị định nghĩa 2 lần, 2 table khác nhau
`workforce.models.AgentRun` (table `platform_agent_runs`, dùng bởi `cosa_cofounder_service.py`) vs `workforce.agents.governance.models.AgentRun` (table `agent_runs`, dùng bởi orchestrator thật `ChiefOfStaffOrchestrator`). Đây là bẫy đặt tên nguy hiểm khi migrate.

## 1.4. Có 3 engine Mission/Plan/Execution chạy song song, không liên kết
- `backend/app/workforce/orchestrator/cosa_cofounder_service.py::handle_founder_message` — mặt tiền chat, nhưng với `FOUNDER_COMMAND` chỉ **trả về template string viết tay** ("1. Marketing Agent... 2. Build/Tech Agent..."), không tạo Mission/Plan thật, không gọi runtime nào.
- `backend/app/workforce/agents/orchestration/chief_of_staff.py::ChiefOfStaffOrchestrator.orchestrate` — **engine thật duy nhất có side-effect thật** (ghi `Outcome`/`OutcomeRun`/`AgentRun` thật, chạy governance/budget check) — nhưng hard-code đúng 2 delegation (`sales_specialist`, `finance_specialist`) bằng gọi hàm Python trực tiếp, không sinh `agent_runs` con dù đã tính `parent_run_id`.
- `backend/app/workforce/agents/control_plane/planner.py::GoalDecomposer` + `control_plane/execution.py::ControlPlaneExecutionManager` — engine thứ 3, keyword-match riêng, `CapabilityGateway`/`DomainCapabilityRouter` riêng, hoàn toàn tách biệt 2 cái trên.

**Đây là fork kiến trúc khẩn cấp nhất** — mọi primitive của G1 (Capability/Toolset Resolver, Learning Review, Subruns) cần **một** execution chain duy nhất để gắn vào, không phải ba.

## 1.5. Risk-level có 4 cách implement không tương thích
LOW/HIGH/CRITICAL (`workforce/governance/risk_evaluator.py`), R0-R4 IntEnum (`workforce/gateway/policy.py` — đúng cái G1/G2 muốn nhưng đặt sai module, tên class trùng với cái LOW/HIGH/CRITICAL ở trên), L0-L5 (`workforce/agents/capabilities/registry.py`), L0-L3A×r0-r4 (`workforce/agents/governance/policy_engine.py`). Không có "hardline blocklist" / "Dangerous Operation Scanner" nào tồn tại (grep "hardline", "blocklist", "YOLO" đều 0 kết quả).

## 1.6. Tool registry tồn tại 2 lần
DB-backed `ToolDefinition`/`AgentToolPermission` (`workforce/models.py`, chỉ dùng cho admin/scaffold) vs in-process `ToolSpec`/`_registry` decorator-based (`core/tool_registry.py`, **cái thật sự chạy runtime**, nhưng chỉ 7/15+ agent key có `tool_flat_names`). Từ "toolset" xuất hiện 0 lần trong backend — khái niệm Toolset Resolver của G1 hoàn toàn mới, chưa có gì trùng để gây nhầm.

## 1.7. Một API gateway đã build gần xong nhưng **chết, chưa mount vào app** — đã verify trực tiếp
`backend/app/workforce/agents/gateway/router.py` gộp 8 sub-router, trong đó có router `capabilities` (`/check`, `/grants`, `/catalog`, `/execute`) gần đúng thứ G1 §37 muốn. Đã verify bằng `grep "gateway" backend/app/main.py` → **0 kết quả**. Router này chỉ được test file import trực tiếp, chưa bao giờ chạy trong app thật. Rủi ro: ai grep route decorator để làm inventory sẽ tưởng nó live.

## 1.8. Mission Outcome hoàn tất không kích hoạt gì cả — đã verify trực tiếp
`chief_of_staff.py:475` gọi `record_event("mission_completed", ...)`, phát lên `mission_control_bus`. Đã đọc trực tiếp `mission_control_bus.py::subscribe()` — hàm này **chỉ là forward SSE cho client đang xem 1 run cụ thể** (yield event rồi break loop khi thấy mission_completed/failed/cancelled), không phải nơi kích hoạt job nền nào. Grep toàn repo xác nhận **0 subscriber nào xử lý business logic** khi mission hoàn tất — đây chính xác là hook point mà Learning Review Worker của G1 cần, hiện đang là ngõ cụt.

## 1.9. Memory có 2 đường ghi phân kỳ, không liên kết
`workforce/memory/*` (5 layer L0-L4, không có Evidence layer riêng như G1 muốn L0-L7; có sẵn `MemoryCandidate`/`MemoryPromotion` staging thật; nhưng retrieval chỉ là `ORDER BY last_accessed_at DESC LIMIT N`, không ranking; provider thật là proxy HTTP tới sidecar TencentDB **ngoài repo**) vs `workforce/agents/control_plane/models.py::AgentMemoryItem` (vocabulary category gần G1 hơn, provenance_jsonb thật, nhưng ghi thẳng không qua staging, chỉ chạy trong test qua `LearningWriter`/`Verifier`/`ReflectionEngine` chưa bao giờ gọi từ production).

## 1.10. Founder feedback/correction đã có sẵn khá đầy đủ
`ApprovalRequest.request_revision()`/`reject()` lưu feedback dạng text; `WorkProduct.status` có DRAFT/REVIEWED/ACCEPTED/REVISION_REQUESTED/REJECTED kèm `metadata_jsonb["revision_feedback"]`. Chưa có gì đọc lại các dữ liệu này để tạo learning candidate — input cho Learning Review Worker coi như có sẵn, chỉ thiếu người tiêu thụ.

## 1.11. `AgentProposal` (table `agent_proposals`) — ứng viên tốt nhất cho `LearningCandidate`
Có sẵn workspace_id/run_id/proposal_type/payload_jsonb/status pending→approved/rejected→applied/reviewed_by/reviewed_at. Đúng tinh thần G1 §9 ("ưu tiên reuse generic proposal/governance entity"). Thiếu: `domain`, `target_key`, `diff_jsonb`, `confidence`, `evidence_ids_jsonb`, `source_outcome_id`, status STAGED/SUPERSEDED.

## 1.12. Automation: không trùng thư mục thật, nhưng có bẫy đặt tên
`workforce/automation/` (số ít) là thư mục duy nhất tồn tại; `automations/` (số nhiều) không tồn tại. Nhưng `workforce/router.py` import module số ít, alias thành `automations_router`, mount ở URL số nhiều `/api/v1/automations` — không phải trùng lặp thật nhưng dễ gây hiểu nhầm khi audit. `jobs.json` không tồn tại ở đâu trong repo (cảnh báo của G1 về việc này là moot). Có 2 hệ scheduler riêng biệt chưa hợp nhất: `founder_os/tasks/scheduler_service.py`+`core/cron.py` vs `workforce/automation/*`.

## 1.13. Channels: không có interface chung thật
`backend/app/channels/*` không tồn tại — vị trí thật là `backend/app/integrations/channels/*`, mỗi adapter (telegram/zalo/gmail) tự viết riêng, không chung class. Có 1 `BaseChannelAdapter` ABC tồn tại nhưng ở `business/marketing/adapters/channel_adapter.py`, chỉ 1 method, hành vi giả lập (`# Giả lập`), không liên quan gì tới các adapter thật.

## 1.14. LiveKit dual-worker — đã hoàn thiện đúng như 2 spec muốn
Desktop→LiveKit local, Mobile/Web→LiveKit cloud đã chạy thật (`integrations/realtime/transport_resolver.py`, `docker-compose.yml` có cả `realtime-agent` và `realtime-agent-cloud`). Điểm lệch: transcript giọng nói **chủ động không lưu DB** (comment trong code giải thích rõ vì lý do privacy), và voice agent có tool registry riêng (`services/realtime_agent/tools.py::build_tools()`), không thực sự hợp nhất vào chat/mission runtime như G1 §29 mô tả "chỉ là transport".

## 1.15. Frontend: cấu trúc Hologram Hub đã đúng, nhưng nội dung Learning/Capability UI phân mảnh
`hologram_hub` đã đúng 2-tab (Command Center + Workforce), không phình thêm card top-level — khớp đúng cái G1/G2 yêu cầu. Nhưng: `waiting_for_you_widget.dart` có nút Approve, **thiếu nút Reject**; `ai_workforce_tab.dart` hiện show pack toggle, không show per-agent Capabilities/Skills/Tools/Permissions/Learning như G1 §36 muốn — UI đó **đã có sẵn** nhưng nằm ở module khác hẳn (`frontend/lib/modules/ai_team/`, gắn vào shell `dashboard` cũ, không nằm trong `hologram_hub`). Approve/Reject + risk filter chip đầy đủ cũng đã có sẵn ở `frontend/lib/modules/approvals/` (cũng chỉ vào được qua `dashboard` cũ).

## 1.16. API routes: capabilities/learning/subruns chưa live
`/api/v1/workforce/runs`, `/api/v1/workforce/skills/{key}/versions` đã live (qua router `admin_api` bị mount 2 lần ở cả `/api/v1/agent-platform` và `/api/v1/workforce`). `/api/v1/workforce/capabilities`, `/learning`, `/subruns` chưa tồn tại live (dù §1.7 cho thấy phần capabilities gần xong nhưng chưa mount).

---

# 2. Quyết định canonical (chốt cứng, áp dụng từ Phase 0A)

| Khái niệm | THẮNG (canonical, giữ) | THUA (deprecate/merge vào winner) |
|---|---|---|
| **AgentRun** | `workforce.agents.governance.models.AgentRun` (table `agent_runs`) — orchestrator thật đang dùng | `workforce.models.AgentRun` (table `platform_agent_runs`) → đổi tên ngay thành `LegacyPlatformAgentRun` để tránh nhầm import khi migrate |
| **Capability Registry** | `founder_os/strategy/models.py::CapabilityDefinition` (SQLAlchemy, `capability_definitions`) | `CAPABILITY_CATALOG` dict → seed 1 lần rồi xóa module; `business/packs/schemas.py::CapabilityDefinition` → hạ cấp thành DTO chỉ dùng khi import YAML, không query runtime nữa |
| **Skill Registry** | `SkillRegistryItem` (table `global_skill_registry`) | 3 cây SKILL.md → seed content, import 1 lần vào DB, runtime chỉ đọc DB từ đó về sau |
| **Toolset Resolver** | Module MỚI, xây trên `core/tool_registry.py::ToolSpec`/`_registry` (cái đang chạy thật) | `ToolDefinition`/`AgentToolPermission` (`workforce/models.py`) → hạ cấp thành read-model admin đồng bộ từ code registry, không còn là source of truth |
| **Learning Review Worker (storage)** | Mở rộng `AgentProposal` (đúng tinh thần G1 §9) | Không tạo `LearningCandidate` từ đầu; `SkillTrajectoryCandidate.create_candidate_from_trajectory()` (đã code sẵn, chỉ chạy test) trở thành logic extraction thật, FK vào `agent_proposals` |
| **Memory Promotion** | `workforce/memory/*` (đã có `MemoryCandidate`/`MemoryPromotion` staging thật) | `AgentMemoryItem` → gộp vocabulary category + `provenance_jsonb` vào `workforce/memory`, trỏ `LearningWriter`/`Verifier`/`ReflectionEngine` (hiện chỉ chạy test) vào đây, rồi xóa `AgentMemoryItem` |
| **Execution Subruns** | Cơ chế `parent_run_id` sẵn có trong `chief_of_staff.py`, ghi vào table `agent_runs` (winner ở trên) | Không có bản thua thật — primitive gần như chưa tồn tại, chỉ cần hoàn thiện (hiện tính `parent_run_id` nhưng chưa bao giờ insert row con) |

---

# 3. Fork kiến trúc quan trọng nhất: hợp nhất 3 orchestration engine

**Thắng: `chief_of_staff.py::ChiefOfStaffOrchestrator`** — duy nhất có side-effect thật (ghi `Outcome`/`OutcomeRun`/`agent_runs` thật + governance/budget check).

Việc cần làm để nó thực sự trở thành canonical (không chỉ "chọn tên"):
1. Tổng quát hóa `orchestrate()` từ 2 delegation hard-code thành dispatch N-agent chung — Capability/Toolset Resolver ở Phase 1B/1C cần chỗ này để cắm vào.
2. Làm nó thực sự insert `agent_runs` con cho việc delegate (hiện tính `parent_run_id` nhưng không ghi row con).
3. Trở thành nơi duy nhất mà `cosa_cofounder_service.py`'s nhánh `FOUNDER_COMMAND` gọi tới.

**Giáng cấp, không xóa: `cosa_cofounder_service.py`** — vẫn giữ vai trò mặt tiền chat/intent routing (vẫn sửa bug greeting ở đây theo G2 P0.6), nhưng xóa template string FOUNDER_COMMAND, thay bằng gọi `ChiefOfStaffOrchestrator.orchestrate()` thật. Đây chính là cách đúng để làm G2 P0.9 ("remove hard-coded business conclusions") — không phải viết template đẹp hơn.

**Nghỉ hưu: `control_plane/planner.py::GoalDecomposer` + `control_plane/execution.py::ControlPlaneExecutionManager`** — engine thứ 3, có `CapabilityGateway`/`DomainCapabilityRouter` riêng sẽ đụng độ trực tiếp với Capability Registry/Toolset Resolver của G1 nếu để sống. Đóng băng phát triển mới ngay Phase 0A → kiểm tra Phase 1A xem có logic sống nào chưa được cover ở `chief_of_staff.py` thì port qua → xóa cuối Phase 1B.

**Luật cứng: Toolset Resolver (Phase 1C) tuyệt đối không được xây dựa trên `CapabilityGateway`** — nếu không sẽ hồi sinh cái fork này dưới tên khác.

---

# 4. Fast wins (rẻ, an toàn, nên làm sớm ở Phase 0A/0B)

1. **Mount `workforce/agents/gateway/router.py`'s `capabilities` sub-router vào `main.py`.** Rẻ, chỉ thêm `include_router()`. Cần xác nhận trước nó đang import shape `CapabilityDefinition` nào (tránh tạo thêm consumer thứ 4 của bản thua) — chỉ mở `/check`, `/grants`, `/catalog` (read-only) trước, gate `/execute` sau lưng feature flag tới khi Phase 1B xong.
2. **Gắn 1 subscriber logging-only vào sự kiện `mission_completed` trên `mission_control_bus`.** Rủi ro gần 0, là cách rẻ nhất để de-risk trigger của Learning Review Worker — chứng minh event thật sự bắn ra với payload thật trước khi Phase 1E cần dùng nó.
3. **Nối `SkillTrajectoryCandidate.create_candidate_from_trajectory()` vào production** — rẻ hơn viết Learning Review Worker từ đầu vì code extraction đã tồn tại (chỉ thiếu người gọi ngoài test).
4. **Đổi tên `workforce.models.AgentRun` → `LegacyPlatformAgentRun`** — 1 commit độc lập, zero behavior change, tránh bẫy import nhầm khi các phase sau bắt đầu động vào.
5. **Sửa alias `automations_router`** trong `workforce/router.py` cho khớp tên module thật — rẻ, giảm nhầm lẫn trước khi làm automation ở Phase 2.

---

# 5. Roadmap theo Phase (giữ khung G2 0A/0B/1A/1B/1C/2, chèn thêm 1C mới + 1E mới cho G1)

## Phase 0A — Security Freeze + Chốt Canonical
**Mục tiêu:** Khóa bảo mật (theo G2: Ed25519 entitlement, persist snapshot local, tách control-plane/company-plane, WorkspaceContext, CORS) + công bố bảng quyết định canonical (mục 2) làm tài liệu tham chiếu bắt buộc từ giờ.
**Kèm theo (fast win):** đóng băng `control_plane/planner.py`+`execution.py`; đổi tên `AgentRun` trùng; mount `capabilities` router (read-only); sửa alias automations.
**Exit criterion:** Forge entitlement bằng public key thất bại (test); `GET /api/v1/capabilities/catalog` trả dữ liệu thật; grep `from workforce.models import AgentRun` toàn repo trả 0 kết quả ngoài path đã đổi tên.

## Phase 0B — Runtime Truth + Hợp nhất Orchestrator
**Mục tiêu:** Một execution chain thật duy nhất, không còn business synthesis giả.
**Deliverables:** fix greeting intent; approval API thật; Genesis-stage mặc định cho workspace mới (theo G2); xóa template FOUNDER_COMMAND trong `cosa_cofounder_service.py`, thay bằng gọi `ChiefOfStaffOrchestrator.orchestrate()` thật; **làm cùng 1 pass** với việc gắn subscriber logging cho `mission_completed` (vì đụng cùng 1 file — xem rủi ro mục 6).
**Exit criterion:** Gửi message FOUNDER_COMMAND qua chat tạo ra row thật trong `agent_runs`/`Outcome` (verify bằng query DB), không còn là template string.

## Phase 1A — Co-Founder Mission Runtime (N-agent thật)
**Mục tiêu:** Pipeline Mission/Plan/Execution tổng quát, xây hoàn toàn trên orchestrator canonical.
**Deliverables:** ContextAssembler; Mission creation/confirmation/AgentPlan/execution mapping/outcome aggregation thật (theo G2); tổng quát hóa 2 delegation hard-code thành dispatch chung; insert `agent_runs` con thật cho việc delegate; xóa `control_plane/planner.py`+`execution.py`+`CapabilityGateway`+`DomainCapabilityRouter`.
**Exit criterion:** Dispatch 1 domain agent thứ 3 (không phải sales/finance) không cần thêm nhánh hard-code; việc delegate tạo row con thật trong `agent_runs` với đúng `parent_run_id`; `control_plane` planner/execution không còn tồn tại trong tree.

## Phase 1B — Workforce Consolidation (= G1 bước 2-3)
**Mục tiêu:** Một Capability Registry duy nhất, một agent inventory canonical.
**Deliverables:** agent inventory canonical, ẩn legacy alias, workspace override không sửa global (theo G2); migrate ~40 entry `CAPABILITY_CATALOG` vào `capability_definitions`, xóa `workforce/agents/capabilities/registry.py`; **regroup 11 business pack từ theo-business-function sang theo-5-Domain-Agent** (⚠️ đây là quyết định product, không phải refactor thuần — cần founder chốt trước khi migrate, xem rủi ro mục 6).
**Exit criterion:** `founder_os/strategy/models.py::CapabilityDefinition` là model capability duy nhất được query runtime (grep xác nhận 2 class kia không còn dùng ngoài seed importer).

## Phase 1C — Toolset Resolver + Skill Registry Versioning (= G1 bước 4-5, phase mới)
**Mục tiêu:** Lọc tool động, fail-closed, theo Agent×Capability×Stage×Plan×Environment×Risk; một Skill Registry có version.
**Deliverables:** Toolset Resolver mới xây trên `ToolSpec`/`_registry`, thêm field `availability_check`/`side_effect_type`/`execution_backend`; mở rộng `tool_flat_names` từ 7 lên toàn bộ 15+ agent key; import 3 cây SKILL.md vào `global_skill_registry`, thêm state EXPERIMENTAL/ARCHIVED/BLOCKED + cờ platform-immutable-vs-workspace-fork.
**Lưu ý:** chỉ cần `workspace.stage` (đã có từ Phase 0B) làm input, **không cần chờ Stage Engine S0-S6 hoàn chỉnh** — chạy song song Phase 1D, không chờ nó xong.
**Exit criterion:** Tool có `availability_check` fail không bao giờ xuất hiện trong schema gửi cho LLM (test kiểm tra schema thật gửi ra); không còn runtime import nào trỏ tới 3 loader SKILL.md cũ.

## Phase 1D — Stage Operating Engine S0-S6 (theo G2, chạy song song 1C)
**Mục tiêu:** Stage transition thật, giờ có consumer thật (Toolset Resolver) thay vì field tĩnh.
**Exit criterion:** như G2 định nghĩa; thêm: kết quả Toolset Resolver tự đổi khi workspace chuyển stage, không cần sửa code resolver.

## Phase 1E — Learning Review Worker + Memory Promotion + Subrun hardening (= G1 bước 6-8, phase mới)
**Mục tiêu:** Vòng học an toàn (chỉ đọc mission, chỉ ghi candidate), memory có ranking/budget, subrun bị giới hạn đúng chuẩn.
**Deliverables:** nâng subscriber logging ở Phase 0B thành gọi Learning Review Worker thật; worker gọi `SkillTrajectoryCandidate.create_candidate_from_trajectory()` + ghi `agent_proposals` (đã mở rộng field); hook thêm `ApprovalRequest.reject()`/`request_revision()` và `WorkProduct.metadata_jsonb["revision_feedback"]` (đã có sẵn, chưa ai đọc) làm trigger source; **xác nhận sidecar TencentDB hoạt động trước khi bắt đầu phần memory** (blocker hạ tầng ngoài code); thêm layer L5-L7 vào `workforce/memory`, thay retrieval unranked bằng ranked/budgeted; gộp `AgentMemoryItem` vào `workforce/memory` rồi xóa; hoàn thiện Subrun: giới hạn toolset (qua resolver Phase 1C), `max_depth=1`, budget/timeout, cancel/steer, ẩn khỏi UI founder.
**Frontend (chỉ làm ở phase này, không sớm hơn):** port UI Skills/Tools/Permissions per-agent từ `ai_team` sang tab Workforce của `hologram_hub`; thêm nút Reject vào `waiting_for_you_widget.dart` (tái dùng component đã có ở module `approvals`, không viết UI approve/reject lần thứ 5).
**Exit criterion:** Reject 1 `WorkProduct` tạo ra `agent_proposals` row review được trong vòng 1 chu kỳ worker, hiển thị trong governance UI; worker không có code path nào tự send/publish/pay/delete/create-mission; query memory luôn trả kết quả có giới hạn, ranked, không bao giờ dump toàn bảng.

## Phase 2 — Central Intelligence (G2) + Automation Enhancement + A2A (= G1 bước 9-10)
**Deliverables:** theo G2, cộng hợp nhất 2 scheduler (`founder_os/tasks/scheduler_service.py`+`core/cron.py` vs `workforce/automation/*`) thành 1; A2A chỉ dùng cho hệ thống ngoài, **loại trừ hẳn 5 core domain agent nội bộ** (theo DO NOT list của G1).

---

# 6. Rủi ro/lưu ý riêng cho codebase này (không tự thấy nếu chỉ đọc G1)

- **Dead-code dễ bị tưởng nhầm là live:** sau khi mount `gateway/router.py` ở Phase 0A, thêm assertion/comment rõ ràng ở `main.py` liệt kê router nào đang mount — file này đã từng bị hiểu nhầm là chạy thật, tránh lặp lại.
- **Bẫy tên trùng `AgentRun` là rủi ro sống trong lúc consolidate**, không chỉ là chuyện lịch sử — đổi tên bản thua (Phase 0A) *trước khi* bất kỳ script migration nào động vào 1 trong 2 bảng.
- **`cosa_cofounder_service.py` là điểm hội tụ của 3 việc khác nhau** (xóa hard-code theo G2 P0.9, chuyển hand-off sang `chief_of_staff.py`, chuẩn bị subscriber `mission_completed`) — làm **1 pass duy nhất** ở Phase 0B, không tách 3 lần đụng file riêng biệt, tránh việc sửa sau vô tình hồi sinh cái sửa trước.
- **Thứ tự phụ thuộc stage:** Genesis-stage mặc định (0B) phải xong *trước* khi Toolset Resolver (1C) đọc `workspace.stage` — nếu không workspace đang migrate sẽ resolve theo stage null/undefined.
- **11 business pack quy nhóm lại theo 5 Domain Agent là quyết định product**, không phải refactor thuần — đây là rủi ro lịch trình lớn nhất trong cả roadmap, cần founder chốt trước khi Phase 1B bắt đầu migrate, không phát hiện bất đồng giữa chừng.
- **Provider memory thật là sidecar TencentDB ngoài repo** — xác nhận nó hoạt động và reachable ở môi trường target trước khi lên lịch phần memory ở Phase 1E; đây là blocker hạ tầng, không phải thứ code fix được.
- **Voice agent có tool registry riêng, transcript chủ động không lưu (privacy).** Loại voice agent khỏi phạm vi Phase 1C/1E — đưa tool call của nó vào Mission/Outcome/Learning tracking sẽ đụng độ chủ đích thiết kế hiện tại; chỉ xem lại nếu product quyết định lưu transcript sau này.
- **Frontend phân mảnh y hệt backend** — không port UI Skills/Tools/Permissions từ `ai_team` sang `hologram_hub` trước khi field backend ở Phase 1C ổn định, nếu không sẽ phải build UI 2 lần.

---

# 7. Critical files (đường dẫn đã verify trực tiếp)

- `backend/app/workforce/orchestrator/cosa_cofounder_service.py`
- `backend/app/workforce/agents/orchestration/chief_of_staff.py`
- `backend/app/workforce/agents/orchestration/mission_control_bus.py`
- `backend/app/founder_os/strategy/models.py`
- `backend/app/core/tool_registry.py`
- `backend/app/workforce/agents/gateway/router.py`
- `backend/app/workforce/models.py`
- `backend/app/workforce/agents/control_plane/planner.py` + `execution.py`
- `backend/app/workforce/skills/models.py` (`SkillRegistryItem`, `SkillTrajectoryCandidate`)
- `backend/app/workforce/memory/models.py` (`MemoryCandidate`, `MemoryPromotion`)
- `backend/app/workforce/agents/proposals/models.py` (`AgentProposal`)
- `frontend/lib/modules/hologram_hub/widgets/waiting_for_you_widget.dart`
- `frontend/lib/modules/ai_team/*`, `frontend/lib/modules/approvals/*`

# 8. Verification (khi bắt đầu triển khai ở phase sau)

- Mỗi exit criterion trong mục 5 đều test được bằng DB query hoặc test tự động — không có tiêu chí mơ hồ kiểu "trông ổn".
- Trước Phase 1B: cần founder xác nhận bằng văn bản việc regroup 11 business pack theo 5 Domain Agent (mục 6).
- Trước Phase 1E (phần memory): cần xác nhận sidecar TencentDB reachable ở target environment.

---

# 9. Chi tiết triển khai Phase 0A (đã verify trực tiếp từng file:line)

Backend-only — **không có thay đổi frontend nào trong Phase 0A** (đây là phase bảo mật/backend thuần túy; frontend chỉ vào phạm vi từ 0B).

## 9.1. P0.1 — HMAC → Ed25519 entitlement signing

**Lỗ hổng cấu trúc xác nhận trực tiếp:** `backend/app/platform/sync/entitlement_crypto.py`
- `DEFAULT_PLATFORM_SIGNING_SECRET` (dòng 25) fallback cứng `"cosa_platform_master_signing_key_2026_production"` nếu thiếu env — **không có** `COSA_PLATFORM_SIGNING_SECRET` trong docker-compose.yml hay `.env.example`, nghĩa là production có thể chạy với secret mặc định lộ trong source mà không ai biết.
- `EntitlementSigner.sign_snapshot()` (51-97) và `EntitlementVerifier.verify_signature()` (100-125) dùng **chung 1 secret đối xứng** → local có thể tự forge license của chính nó. Đây chính là lỗ hổng P0.1 phải đóng.
- `SignedEntitlementSnapshot` (`platform/sync/schemas.py:82-101`) **chưa có field `key_id`, `signature_alg`** — bắt buộc phải thêm.
- `cryptography>=42.0` đã có sẵn trong `backend/requirements.txt:36` — đủ hỗ trợ `cryptography.hazmat.primitives.asymmetric.ed25519`, không cần thêm dependency.
- `runtime_config.py:25-30` hiện đang **dùng `COSA_PLATFORM_SIGNING_SECRET` để backfill `JWT_SECRET`/`MASTER_SECRET_KEY`** nếu 2 biến này chưa set — cross-wiring nguy hiểm, cần cắt đứt khi chuyển sang Ed25519. `_REQUIRED_PRODUCTION_SECRETS` (dòng 15) hiện **không** bao gồm `COSA_PLATFORM_SIGNING_SECRET` → production có thể boot với secret mặc định mà không bị chặn.
- Central-side: `infra/supabase/migrations/001_initial_central_control_plane.sql:129-137` đã có bảng `company_entitlements` với cột `snapshot_signature` (136) nhưng chưa có `key_id`/`signature_alg`.

**Việc cần làm (theo thứ tự commit):**
1. Migration Supabase: thêm `key_id`, `signature_alg` vào `company_entitlements`.
2. `schemas.py`: thêm `key_id: str`, `signature_alg: Literal["HMAC_SHA256","ED25519"] = "ED25519"` vào `SignedEntitlementSnapshot`.
3. `runtime_config.py`: nạp cặp khóa Ed25519 mới — Central: `COSA_ENTITLEMENT_PRIVATE_KEY_B64` + `COSA_ENTITLEMENT_KEY_ID`; Local: `COSA_ENTITLEMENT_PUBLIC_KEY_B64` + `COSA_ENTITLEMENT_KEY_ID` (hỗ trợ catalog nhiều public key để rotate).
4. `entitlement_crypto.py`: thêm `Ed25519EntitlementSigner`/`Ed25519EntitlementVerifier` cạnh class HMAC cũ (không xóa ngay, giữ cho giai đoạn chuyển tiếp); verifier dispatch theo `snapshot.signature_alg`.
5. `entitlement_manager.py`: `save_snapshot()`/`get_status_mode()` gọi qua dispatcher mới thay vì thẳng `EntitlementVerifier.verify_signature`.
6. Cắt cross-wiring `runtime_config.py:25-30` (JWT_SECRET/MASTER_SECRET_KEY không còn ăn theo `COSA_PLATFORM_SIGNING_SECRET`).
7. Xóa `DEFAULT_PLATFORM_SIGNING_SECRET` hard-code hoặc thêm `COSA_PLATFORM_SIGNING_SECRET` vào `_REQUIRED_PRODUCTION_SECRETS` (chặn boot nếu thiếu) — làm cả hai nếu muốn chắc chắn.
8. Test: valid Ed25519 / invalid signature / sai key / expired / grace period / snapshot HMAC cũ vẫn verify được trong giai đoạn chuyển tiếp / **local không thể tự sign** (không có private key nội bộ).

## 9.2. P0.2 — Tách endpoint sign khỏi company runtime

- Endpoint cần cô lập: `POST /sync/entitlement/sign` — `platform/sync/router.py:145-157`, full path `/api/v1/platform/sync/entitlement/sign` (qua `platform/router.py:51` + `main.py:77`).
- Hiện **chỉ có 1 process, 1 FastAPI app** (`backend/app/main.py`, chạy qua `uvicorn app.main:app`, docker-compose.yml dòng 94-99) — chưa có `control_plane_main.py`, chưa có `COSA_RUNTIME_PLANE`.
- **Tiền lệ có sẵn để tái dùng**: docker-compose.yml đã có service `migrate-control-plane` (74-92) gated bằng `profiles: [control-plane]` (90-91) và `CONTROL_PLANE_DATABASE_URL` riêng — dùng đúng pattern profile này.
- Các endpoint láng giềng cùng router: `/sync/entitlement/refresh` (160-175, Local-facing, giữ nguyên) và `/sync/entitlement/current` (178-197, Local-facing, giữ nguyên) — chỉ `/entitlement/sign` cần cô lập.

**Khuyến nghị: chọn Option B (conditional router registration)** thay vì 2 entrypoint riêng — rẻ hơn, tận dụng đúng pattern `profiles` đã có sẵn trong docker-compose.
1. Thêm env `COSA_RUNTIME_PLANE=company|control`, mặc định `company`.
2. `platform/sync/router.py`: gate việc đăng ký route `/entitlement/sign` (và mọi endpoint issue/admin license khác nếu có) sau điều kiện `plane == "control"`.
3. `main.py`: đọc plane, chỉ include các route control-plane nếu đúng plane.
4. Test: app khởi động ở plane `company` → introspect `app.routes`, xác nhận 0 route khớp `/entitlement/sign`.

## 9.3. P0.3 — Persist entitlement snapshot local

- `platform/sync/models.py` hiện chỉ có `PlatformOutbox` (16-43), `PlatformInbox` (46-65) — **chưa có `LocalEntitlementSnapshot`**, xác nhận không có bảng tương đương ở đâu khác.
- Cache 100% in-memory: `entitlement_manager.py:32` — `_cache: Dict[str, SignedEntitlementSnapshot] = {}` (class-level dict). `get_snapshot()` (57-63) fallback về Free tier (`get_default_free_snapshot()`, 34-44) mỗi khi cache miss — **đây chính xác là bug "restart mất license Pro"**, vì cache rỗng sau mỗi lần restart process, không có gì load lại từ DB.
- Không có startup hook nào trong `main.py` gọi vào `entitlement_manager` — mọi thứ cho P0.3 là **new-build hoàn toàn**.

**Việc cần làm:**
1. Model mới `LocalEntitlementSnapshot` trong `platform/sync/models.py` (theo field đề xuất ở G2 §6.3), unique `(company_id, is_current)`.
2. Migration Alembic mới.
3. Sửa `EntitlementManager.get_snapshot`/`save_snapshot` đọc/ghi qua DB thay vì `_cache`; transaction pattern: set `old.is_current=false` + insert mới trong 1 transaction.
4. Startup hook (lifespan/startup event trong `main.py`): load current snapshot từ DB → verify → nạp cache.
5. Test: restart giữ nguyên entitlement Pro (mô phỏng bằng seed sẵn 1 row rồi gọi lại startup loader).

## 9.4. P0.4 — WorkspaceContext thống nhất

- **`WorkspaceContext`/`get_workspace_context` chưa tồn tại ở đâu** (grep 0 kết quả) — new-build hoàn toàn.
- **Building block sẵn có, dùng làm nền**: `core/auth.py:33-47::get_current_workspace_member` — đã verify membership đúng cách (`WorkspaceMember` query, raise 403 nếu không thuộc), nhưng chỉ trả về bare `WorkspaceMember`, chưa load `Workspace`, chưa derive `company_id`/`company_stage`, chưa đụng entitlement.
- **Pattern dùng đúng đã có sẵn** (tái dùng làm mẫu): `business/packs/router.py:37-46` (`_guard`/`_guard_admin`), `business/finance/routers/regimes_router.py:33-39`, và dùng trực tiếp `Depends(get_current_workspace_member)` ở nhiều router `founder_os/*`, `business/legal/router.py`, `business/marketing/routers/campaign_router.py`, `business/sales/routers/leads_router.py`.

**Điểm hổng đã xác nhận trực tiếp (đúng target của spec):**
- `workforce/api/cofounder_api.py`: `workspace_id` nhận thẳng từ body (`CoFounderChatRequest.workspace_id`, dòng 40) hoặc query (`GET /pulse` dòng 68, `GET /top3` dòng 81) — chỉ có `Depends(get_current_user)`, **không có** membership check.
- `workforce/api/packs_api.py`: tương tự — `list_workforce_packs` (dòng 48) và `TogglePackRequest.workspace_id` (dòng 37) không check membership.
- `platform/sync/entitlement_guard.py:12-35` (`get_current_company_id`, `require_feature`) — tin thẳng header `X-Company-ID`/`X-Workspace-ID`, **không có JWT auth dependency nào**, có fallback UUID cứng `"00000000-0000-0000-0000-000000000001"`. Hiện **chưa wire vào route nào** (chỉ gọi từ 1 test) — "latent nhưng nguy hiểm", nên sửa hoặc xóa hẳn trong pass này.
- `platform/sync/router.py:178-197` (`GET /entitlement/current`) — `company_id` là query param default value, **0 auth**.
- **Model có sẵn để derive field**: `platform/auth/models.py::Workspace` (26-36) có `company_stage` (default hiện tại sai, xem mục 10.2) và `platform_company_id` (unique, chính là Central company UUID); `WorkspaceMember` (38-48) có `role`.
- **Pattern thứ 3, không nhất quán**: `workforce/api/admin_api.py` dùng `current_user.workspace_id` (field gắn thẳng trên `User`, vd dòng 178/180/226/518-519) — giả định 1 user = 1 workspace, bỏ qua hoàn toàn `WorkspaceMember`/role. Không tương thích với `WorkspaceContext` chung — **khuyến nghị: ghi nhận là follow-up riêng, không cố nhét vào 0A** (0A đã đủ lớn), nhưng phải ghi rõ trong quyết định canonical để không quên.

**Việc cần làm:**
1. File mới (vd `core/workspace_context.py`) chứa `WorkspaceContext` dataclass + dependency `get_workspace_context()`, xây trên `get_current_workspace_member` — mở rộng để load `Workspace`, derive `company_id`/`company_stage`, load entitlement qua `EntitlementManager`.
2. Áp dụng cho `cofounder_api.py` (chat, pulse, top3) và `packs_api.py` (list, toggle) trước — thay raw `Query`/body `workspace_id` + `get_current_user` bằng `Depends(get_workspace_context)`.
3. Sửa hoặc xóa `entitlement_guard.py::get_current_company_id`/`require_feature` (chưa route nào dùng, nhưng nguy hiểm nếu ai đó wire nhầm sau này).
4. Ghi nhận `admin_api.py`'s `current_user.workspace_id` pattern là nợ kỹ thuật cần theo dõi, không sửa trong 0A.
5. Test: user A không đọc/sửa được workspace B qua `cofounder_api`/`packs_api`; forge `X-Workspace-ID`/`X-Company-ID` bị bỏ qua/reject.

## 9.5. P0.10 — Production CORS

`main.py:48-56` xác nhận trực tiếp:
```python
origins = ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
```
Wildcard + credentials **không điều kiện gì cả** — không có env branching, dù file này (dòng 32-37) đã có sẵn pattern branch theo `ENVIRONMENT`/`APP_ENV` ngay phía trên (dùng làm mẫu). Chưa có `COSA_ALLOWED_ORIGINS` ở đâu trong repo.

**Việc cần làm:**
1. `main.py`: thay `origins = ["*"]` bằng đọc từ `COSA_ALLOWED_ORIGINS` (comma-separated), dev fallback về `localhost` list.
2. `runtime_config.py`: thêm validation cạnh `validate_runtime_configuration()` (đã gọi ở `main.py:8-9`) — raise nếu `allow_origins == ["*"]` và `allow_credentials=True` khi `APP_ENV=production`.
3. Test: production startup fail khi cấu hình wildcard+credentials.

## 9.6. Fast-win kèm theo Phase 0A (đã verify chính xác từng call site)

**a. Đổi tên `workforce.models.AgentRun` → `LegacyPlatformAgentRun`**
- Class định nghĩa: `workforce/models.py:241-264` (`__tablename__ = "platform_agent_runs"`).
- **Xác nhận rõ: đây KHÁC với** `workforce/agents/governance/models.py:12-14::AgentRun` (`__tablename__ = "agent_runs"`, table khác, đang được dùng thật ở nhiều nơi — KHÔNG nằm trong phạm vi đổi tên).
- Toàn bộ call site cần sửa khi đổi tên (import `workforce.models.AgentRun`):
  - `workforce/models.py:241` (định nghĩa class)
  - `workforce/__init__.py:16,40`
  - `workforce/dispatcher/runner.py:8,29`
  - `workforce/api/admin_api.py:14` (import), `596,599,601,603,618,620` (usage)
  - `workforce/governance/exception_engine.py:15-17` (import), `82,84,85,89,92`
  - `workforce/automation/heartbeat_monitor.py:6`, `69,71,72,76`
  - `workforce/orchestrator/cosa_cofounder_service.py:20`, `143,144,147`
  - `workforce/work_product/work_product_service.py:6` (import không dùng — dọn luôn dead import)
  - `db/base.py:113-118` (đã alias sẵn `AgentRun as PlatformAgentRun` — chỉ cần đổi tên import gốc)
  - `tests/agent_platform/test_cosa_phase_a_control_plane.py:5,~193`
  - `tests/agent_platform/test_cosa_phase_d_automation.py:7,83`
- 1 commit độc lập, zero behavior change, làm trước mọi migration khác đụng vào bảng này.

**b. Mount `capabilities` sub-router (không mount toàn bộ `gateway/router.py`)**
- `workforce/agents/gateway/router.py:16,28` import và mount `capabilities/router.py` ở prefix `/api/v1/capabilities` — nhưng **toàn bộ gateway package hiện chưa mount vào `main.py` ở đâu cả** (xác nhận: `grep "gateway" backend/app/main.py` → 0 kết quả).
- `capabilities/router.py`'s endpoint `GET /catalog` (145-165) đọc từ `list_capabilities()` trong `workforce/agents/capabilities/registry.py` — tức là **model THUA trong bảng quyết định canonical (mục 2)**, dataclass `CAPABILITY_CATALOG` ~40 entry hard-code. Các endpoint `/grants`, `/check`, `/execute` (67-189) đi qua `CapabilityGateway`/`CapabilityGrant` (model riêng, không liên quan 3 `CapabilityDefinition`).
- **Khuyến nghị:** chỉ mount trực tiếp `capabilities/router.py` (không mount cả gateway 8-router package — 7 router còn lại chưa được audit sẵn sàng), và chỉ mở `/catalog`, `/grants`, `/check` (read/permission-check) — gate `/execute` sau feature flag. **Đây là cầu nối tạm** — dữ liệu `/catalog` trả về từ model sẽ bị deprecate ở Phase 1B; khi Phase 1B migrate xong, chỉ cần đổi nguồn đọc trong `capabilities/router.py`, không đổi shape API.
- Thêm assertion/comment rõ trong `main.py` liệt kê router nào đang mount (tránh lặp lại việc code chết bị tưởng nhầm là live).

**c. Sửa alias `automations_router`**
- `workforce/router.py:10` import `app.workforce.automation` (số ít) nhưng alias `automations_router`, mount ở `/api/v1/automations` (dòng 26, số nhiều) — không phải trùng thư mục thật, chỉ là bẫy tên. Đổi tên biến cho khớp module thật (`automation_router`) — cosmetic, rẻ.

---

# 10. Chi tiết triển khai Phase 0B (đã verify trực tiếp từng file:line, gồm cả frontend)

## 10.1. P0.6 — Fix greeting intent

`workforce/routing/deterministic.py:52-71` — xác nhận trực tiếp bug: `deterministic_intent()` **không bao giờ trả `Intent.GREETING`** dù enum này tồn tại (dòng 8) và `GREETING_EXACT` (30-49) đã liệt kê đúng "chào" (31) — mọi nhánh khớp câu chào đều trả `Intent.GENERAL_CHAT` (dòng 62, 69).

Workaround hiện tại ở `cosa_cofounder_service.py:338`:
```python
if intent == Intent.GREETING or "greetings" in decision.reason.lower():
```
`decision.reason` = `"Deterministic match for greetings/social chat."` (đặt cứng ở `routing/router.py:15-28`) — chuỗi này **chứa từ "greetings"** nên nhánh này hiện vẫn chạy đúng cho "chào", nhưng qua một string-match mong manh, không qua enum thật. Response trả về (dòng 340) cũng hard-set `intent=Intent.GREETING.value` bất kể `decision.intent` thực tế là gì — không nhất quán nội bộ. Chỉ cần đổi wording của `reason` trong tương lai là silently break, không test nào bắt được.

Đã xác nhận: nhánh greeting hiện tại **đã không query DB** (return string tĩnh ngay, trước mọi lời gọi Pulse/NBA) — phần "không load DB nặng" của yêu cầu đã đúng sẵn, chỉ cần sửa phần classification.

**Việc cần làm:**
1. `deterministic.py` dòng 62 và 69: đổi `return Intent.GENERAL_CHAT` → `return Intent.GREETING`. Giữ nguyên dòng 55 (`return Intent.GENERAL_CHAT` cho message rỗng).
2. `cosa_cofounder_service.py:338`: đơn giản hóa thành `if intent == Intent.GREETING:`, xóa `or "greetings" in decision.reason.lower()`.
3. Xác nhận không caller nào khác phụ thuộc `deterministic_intent()` trả `GENERAL_CHAT` cho câu chào (đã grep: `IntentRouter.route_message` là caller duy nhất của `deterministic_intent`, `cosa_cofounder_service.py` là caller duy nhất của `route_message`).
4. Test: `chào`, `chào!`, `xin chào`, `hello`, `hi`, `hi cosa`, `cảm ơn` → `Intent.GREETING`; không có query DB nào bị gọi (assert qua mock/spy).

## 10.2. P0.5 — Genesis stage mặc định

`platform/auth/models.py:26-32::Workspace.company_stage` — `default="S5_OPERATE_GROWTH"` (dòng 30). Nơi tạo workspace duy nhất ở production: `platform/auth/router.py:44-72::POST /register` — `Workspace(name=...)` **không truyền `company_stage`** (dòng ~63) → rơi vào default sai. Dev bootstrap script (`scripts/bootstrap_dev_user.py:37`) cùng lỗi. Fallback dự phòng cùng giá trị sai ở `founder_os/strategy/services/stage_resolver_service.py:37-46` (dòng 39).

**⚠️ Phát hiện quan trọng cần quyết định trước khi sửa:** enum `S0_GENESIS...S6_SCALE` mà G1/G2 mô tả **không tồn tại trong code ở đâu cả** — chỉ có trong 2 file markdown spec. Code hiện có **2 enum khác nhau, tên khác nhau**, cả hai đều nằm trên field khác (`Project.project_stage`, KHÔNG PHẢI `Workspace.company_stage`):
- `founder_os/strategy/schemas/stage_schemas.py:7-24::ProjectStageEnum` — `S0_EXPLORE, S1_PROBLEM_VALIDATION, S2_SOLUTION_VALIDATION, S3_BUSINESS_VALIDATION, S4_GO_TO_MARKET, S5_OPERATE_GROWTH, S6_SCALE_GOVERN`.
- `platform/sync/schemas.py:17-24::StartupStageEnum` — giống hệt `ProjectStageEnum`.

Chỉ `S4_GO_TO_MARKET`/`S5_OPERATE_GROWTH` khớp tên với spec; `S0/S1/S2/S3/S6` lệch tên hoàn toàn. May mắn: `Workspace.company_stage` là `String(50)` **không có enum/CHECK constraint**, chỉ được đọc như chuỗi opaque duy nhất tại `stage_resolver_service.py:46` (không hề chạy qua `ProjectStageEnum(...)`) — nên đổi default string là thay đổi an toàn, cô lập.

**Khuyến nghị:** trong phạm vi 0B, chỉ đổi literal string default (không định nghĩa enum mới, không đụng `ProjectStageEnum`/`StartupStageEnum`) — việc hợp nhất 3 taxonomy stage là việc của **Phase 1D (Stage Operating Engine)**, không phải P0. Nói rõ trong code/PR rằng `Workspace.company_stage` cố ý dùng tên riêng tạm thời.

**Việc cần làm:**
1. `platform/auth/models.py:30`: `default="S5_OPERATE_GROWTH"` → `default="S0_GENESIS"`.
2. `stage_resolver_service.py:39`: đồng bộ fallback literal.
3. **Không backfill workspace cũ** (đúng yêu cầu G2 P0.5 — chỉ đổi default cho workspace mới, giữ nguyên workspace hiện có).
4. Test: `/register` tạo workspace mới → `company_stage == "S0_GENESIS"`; workspace cũ trong DB không đổi.

## 10.3. P0.7 — Fake Approval success (frontend)

File: `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`, method `approveTask()` (dòng 92-102) — xác nhận trực tiếp: **không hề gọi backend**, chỉ xóa item khỏi list local + show snackbar thành công vô điều kiện. Tệ hơn "optimistic update" — hoàn toàn không có network call.

Service thật đã có sẵn và đúng: `approvals_service.dart:37-52::approve(approvalId, {comment})` — trả `bool` thật dựa trên `response.statusCode == 200` (có fallback qua `/workflows/steps/{id}/approve`). Pattern đúng **đã tồn tại ngay trong cùng file** ở 2 method khác: `resolveDecision()` (68-90) và `togglePack()` (104-131) — cả hai đều `final success = await ...; if (success) {...} else {...}`.

Không có `rejectTask`/`requestRevisionTask` nào được wire trong Hologram Hub (dù `ApprovalsService.reject()`/`.requestRevision()` đã có method sẵn) — quyết định rõ: **không** làm Reject UI trong 0B (đúng phạm vi G2 P0.7 chỉ nói approve), để dành cho Phase 1E theo roadmap ở mục 5 (lúc đó tái dùng component `approvals` module).

Đã khảo sát các pattern khác trong Hologram Hub — **đều đúng, không cần sửa**: `hub_command_mixin.dart::handleQuickApprove()` (optimistic nhưng có reconcile lại từ server), `hub_control_plane_mixin.dart::approveTaskCard/rejectTaskCard/approveAgentAction/resolveEscalation` (đều gate đúng theo kết quả thật).

**Việc cần làm:**
1. `founder_command_center_controller.dart:92-102`: thay bằng gọi `_approvalsService.approve(approvalId)`, gate mutate/snackbar theo kết quả `bool`, y hệt pattern `resolveDecision()`/`togglePack()` trong cùng file.
2. Test: mock `ApprovalsService` trả `false` → item KHÔNG bị xóa khỏi `pendingApprovals`, hiện snackbar lỗi; trả `true` → xóa + snackbar thành công.

## 10.4. P0.8 — Fake Chat fallback (frontend, 2 lớp)

Cùng file, `sendChatMessage()` (dòng 133-155) — xác nhận chuỗi giả nguyên văn (dòng 149):
```
'Tôi đã ghi nhận định hướng của bạn và đang điều phối các Domain Agents liên quan.'
```
fire bất cứ khi nào `res == null`. Không có `catch` (chỉ `try/finally`) — an toàn được vì tầng dưới đã nuốt hết lỗi:

`cofounder_api_service.dart:87-110::chatWithCoFounder()` — bắt **mọi** lỗi (status ≠ 200, network exception, JSON decode lỗi) nội bộ, chỉ `debugPrint` (không hiện cho user), luôn trả `null` khi fail. Đây là nguồn gốc thật của bug — controller chỉ là nạn nhân của service đã xóa hết thông tin lỗi.

**Việc cần làm (bắt buộc sửa cả 2 lớp):**
1. `cofounder_api_service.dart:87-110`: đổi để phân biệt được lỗi (thay vì luôn trả `null`) — ví dụ trả kiểu union/kết quả có discriminant success/network-error/server-error, thay vì `Map<String,dynamic>?`.
2. `founder_command_center_controller.dart:143-151`: nhánh lỗi hiện `error`/`message` thật (gợi ý dùng đúng câu G2 đề xuất: *"Không thể gửi yêu cầu tới COSA runtime. Yêu cầu chưa được tạo thành Mission."*) thay vì chuỗi giả "đang điều phối" — dùng pattern snackbar lỗi đã có sẵn ở `hub_stage_mixin.dart` (`Get.snackbar('Lỗi...', ..., backgroundColor: Color(0xFFEF4444))`) làm mẫu.
3. Test: mock `chatWithCoFounder` trả lỗi → `chatMessages` nhận entry lỗi thật, không bao giờ là chuỗi "đang điều phối".

## 10.5. P0.9 + hand-off orchestrator — điểm hội tụ quan trọng nhất của Phase 0B

Đọc toàn bộ `cosa_cofounder_service.py` (440 dòng) và `chief_of_staff.py` (605 dòng) trực tiếp — các phát hiện làm rõ hơn (và điều chỉnh) phân tích trước:

**a. `synthesize_cross_domain()` (299-323)** — xác nhận **0 truy vấn DB**, `workspace_id` nhận vào nhưng không dùng, toàn bộ nội dung trả về (25-30% CAC, "50 triệu/tháng", "7.5→6.2 tháng runway", "15 triệu", "Nghị định 13"...) là chuỗi cứng giống hệt nhau cho mọi câu hỏi/workspace — khớp chính xác ví dụ "sai" mà G2 §2.7 nêu ra.
→ **Khuyến nghị:** không vá riêng lẻ — route thẳng các message FOUNDER_DECISION-intent qua cùng `orchestrate()` (mục c bên dưới), vì `orchestrate()` đã tạo `sales_data`/`fin_data` thật rồi. Tránh nuôi 2 đường lấy dữ liệu "giả vs thật" song song trong cùng file.

**b. `get_company_pulse()` (96-167)** — phần lớn **đã** query thật (Project/FounderDecision/ApprovalRequest/AgentRun/TwelveWeekCycle, dòng 105-156). Phần giả: `suggested_focus` chỉ 2 chuỗi tĩnh cố định (120, 165); `major_risks_count = 1 if needs_decision > 0 else 0` (164, proxy thô); `goals_on_track` luôn bằng `total_goals` (159-160, tức luôn báo 100% on-track).
→ 0B chỉ cần: bỏ 2 chuỗi tĩnh + proxy thô, thay bằng suy ra từ chính các con số đã query được, hoặc "unknown" nếu chưa có tín hiệu thật. **Không** mở rộng thêm query mới trong 0B — Pulse v2 đầy đủ (G2 §8) là việc của Phase 1A.

**c. `get_next_best_action()` (169-263)** — genesis-case (186-210) và pending-decision case (214-235) đều dùng dữ liệu thật/hợp lý. Nhưng **2 item bị append vô điều kiện mỗi lần gọi, không backing bởi query nào**: `act_cust_interview` (238-248) và `act_weekly_review` (251-261).
→ 0B: **xóa 2 item tĩnh này** (đơn giản, trung thực) thay vì cố gate chúng bằng logic mới — ranking đầy đủ theo urgency/impact (G2 §6.9) để dành Phase 1A.

**d. `challenge_assumptions()` (265-297)** — 2 object `ChallengeAnalysis` template cố định dựa trên keyword-match. **Không cần sửa trong 0B** — đây là advisory reasoning theo đúng định nghĩa "Challenge Mode" của G2 (§7.6: "Challenge là advisory"), không phải business metric claim như 3 mục trên.

**e. Dọn dẹp phát hiện thêm khi đọc toàn file:** 2 khối "Challenge Mode" bị lặp y hệt (dòng 345-360 và 417-432) — khối thứ 2 **dead code không bao giờ chạy tới** (vì `challenge_assumptions(message)` đã gọi 1 lần ở dòng 346 và hàm này pure/deterministic, nên nếu `is_challenged=False` lần đầu thì lần gọi lại ở dòng 418 chắc chắn cũng `False`). Xóa khối chết này trong cùng lần sửa file (zero behavior change, tránh phải đụng file này lần thứ 4).

**f. FOUNDER_COMMAND branch (401-415)** — xác nhận nguyên văn template ("Kế hoạch phân rã Mission tự động: 1. Marketing Agent... 2. Build/Tech Agent... 3. Sales Agent..."), `routed_domain="MISSION_ORCHESTRATOR"` bị set nhưng **không có gì được dispatch thật** — không `Outcome`/`OutcomeRun`/`AgentRun`/`mission_id` nào được tạo, không gì được emit lên `mission_control_bus`.

**g. Target hand-off: `chief_of_staff.py::ChiefOfStaffOrchestrator.orchestrate()`** (chữ ký chính xác, dòng 65-76):
```python
async def orchestrate(cls, db: Session, workspace_id: int, user_id: int, goal: str,
                       company_id: Optional[int]=None, context: Optional[dict]=None,
                       runtime: Optional[AgentRuntime]=None, budget: Optional[MissionBudget]=None) -> ChiefOfStaffResult
```
- **`mission_id` tự sinh mới mỗi lần gọi** (`generate_snowflake_id()`, dòng 77) — method tự tạo `Outcome`/`OutcomeRun`/`AgentRun` riêng (91-127), không cần truyền Mission có sẵn vào. → gọi từ `cosa_cofounder_service.py` không cần pre-create gì cả.
- **⚠️ Blocker kỹ thuật xác nhận trực tiếp: lệch kiểu Session.** `orchestrate()` nhận `db: Session` (sync, SQLAlchemy `sqlalchemy.orm.Session`), trong khi `cosa_cofounder_service.py` dùng `self.db: AsyncSession` (constructor ~93-94). Đây là việc phải giải quyết trước khi wire — **khuyến nghị**: cấp cho `CosaCofounderService` một sync `Session` riêng (tương tự cách `worker_main.py`'s job loop lấy sync session) thay vì đổi `orchestrate()` sang async (vì `orchestrate()` còn được gọi bởi governance/budget code khác, đổi sang async sẽ lan rộng hơn cần thiết cho 0B).
- **⚠️ Điều chỉnh phát hiện trước đó: KHÔNG có branch chọn 1-trong-2 domain.** Cả `sales_specialist` (196-220, gọi `get_pipeline_summary`) và `finance_specialist` (249-273, gọi `get_financial_summary`) đều chạy **vô điều kiện mỗi lần** (trừ khi governance abort sớm) — không phải "chọn 1 trong 2 theo goal". Đây là hành vi hiện tại, không phải bug cần sửa trong 0B, nhưng cần biết để hiểu response sẽ luôn có cả 2 domain report.
- `ChiefOfStaffResult` (41-51: `mission_id, workspace_id, goal, diagnosis, specialist_reports, priorities, action_plan, required_approvals, proposals, status`) không khớp 1:1 với `CoFounderMessageResponse` hiện tại (`intent, message, pulse, next_best_actions, suggested_decisions, challenge_analysis, routed_domain`) — cần map: `diagnosis` → `message`; khuyến nghị mở rộng tối thiểu `CoFounderMessageResponse` thêm `mission_id`+`status` để test/frontend có thể assert trạng thái thật (không cần build UI đầy đủ cho `action_plan`/`required_approvals` ngay — đó là việc Phase 1A/1E).
- Method này tự emit `mission_completed` ở cuối (dòng 475: `record_event("mission_completed", {"result": result.model_dump()}, seq)`) — `record_event` là closure nội bộ của `orchestrate()` (130-150), không phải API của `mission_control_bus`.

**Việc cần làm (1 pass duy nhất trên `cosa_cofounder_service.py`, đúng cảnh báo rủi ro ở mục 6):**
1. Giải quyết sync/async session mismatch (cấp sync Session riêng cho service).
2. Xóa template FOUNDER_COMMAND (401-415), thay bằng gọi `ChiefOfStaffOrchestrator.orchestrate(db=sync_db, workspace_id=..., user_id=..., goal=message)`, map `ChiefOfStaffResult` → `CoFounderMessageResponse` (mở rộng schema thêm `mission_id`, `status`).
3. Route FOUNDER_DECISION-intent (dùng bởi `synthesize_cross_domain`) qua cùng `orchestrate()` thay vì hàm hard-code riêng.
4. Sửa `get_company_pulse()`: bỏ 2 chuỗi `suggested_focus` tĩnh + proxy `major_risks_count`/`goals_on_track` thô, suy ra từ số liệu đã query.
5. Sửa `get_next_best_action()`: xóa 2 item tĩnh không có query backing.
6. Xóa khối Challenge Mode chết (417-432).
7. Không đổi `challenge_assumptions()`.
8. Fix greeting đã làm ở 10.1 nằm trong cùng file — xác nhận không bị 1 trong các sửa đổi trên ghi đè lại.

## 10.6. Subscriber logging cho `mission_completed` — cần plumbing mới, không phải "gắn vào hook có sẵn"

Đọc toàn bộ `mission_control_bus.py` (140 dòng) — xác nhận rõ:
- `emit_event()` (49-56, chữ ký đầy đủ có `run_id, workspace_id, event_type, data, agent_key`) publish cross-process qua `publish_event()` (`core/events.py`) rồi dispatch local tới `self._subscribers[run_id]` (86-91).
- `subscribe(run_id)` (123-137) — **chỉ scope theo 1 `run_id` cụ thể**, tạo `asyncio.Queue`, tự hủy đăng ký khi gặp event terminal (`mission_completed/failed/cancelled`). Đây thuần túy là cơ chế forward SSE cho 1 client đang xem 1 run.
- `self._subscribers: dict[str, set[asyncio.Queue]]` (dòng 35) — **key theo `run_id`**, không có `self._global_subscribers`, không có wildcard `"*"` hay `run_id=None` nào được xử lý.
- **Kết luận xác nhận: hoàn toàn không có cơ chế nhận MỌI `mission_completed` process-wide.** Muốn có logging subscriber toàn cục (bao gồm mission chạy trên process khác qua NOTIFY, không chỉ process đang host logger) cần **code mới thật sự**: thêm `self._global_subscribers: list[Callable]` (hoặc queue), thêm `add_global_listener()`/`subscribe_all()`, gọi nó ở cả `emit_event()` (86-91) lẫn `_on_cross_process_envelope()` (96-121) — không phải chỉ "gọi 1 hook đã có".

**Việc cần làm:**
1. `mission_control_bus.py`: thêm `_global_subscribers` + `add_global_listener()`, invoke từ cả local-emit và cross-process-NOTIFY path.
2. Đăng ký 1 listener logging-only lúc app/worker startup — chỉ log, chưa xử lý side-effect (Learning Review Worker thật là việc Phase 1E).
3. Test (integration, không chỉ unit): 1 mission thật hoàn tất → logger nhận được event có `run_id`/`workspace_id`/payload thật.

## 10.7. Tổng hợp phạm vi frontend cho Phase 0B

Chỉ 2 file cần sửa, không hơn:
- `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart` — `approveTask()` (10.3) và `sendChatMessage()` (10.4).
- `frontend/lib/data/services/cofounder_api_service.dart` — `chatWithCoFounder()` (10.4, lớp service).

**Xác nhận rõ — không cần sửa** (đã đúng pattern, khảo sát trực tiếp): `approvals_service.dart` (đã đúng), `resolveDecision()`/`togglePack()` trong cùng controller (đã đúng, dùng làm mẫu), `hub_command_mixin.dart::handleQuickApprove()`, `hub_control_plane_mixin.dart` (approve/reject task card, approve/reject agent action, resolve escalation) — tất cả đã gate đúng theo kết quả backend thật. **Không động vào các file này trong 0B** để tránh sửa nhầm code đang hoạt động đúng.

---

# 11. Commit sequence đề xuất cho Phase 0A + 0B

```text
chore: rename workforce.models.AgentRun -> LegacyPlatformAgentRun (10 call site, zero behavior change)
chore: fix automations_router alias naming

security: add Ed25519 entitlement signing + key_id/signature_alg (giữ HMAC verify song song)
security: sever COSA_PLATFORM_SIGNING_SECRET cross-wiring khỏi JWT_SECRET/MASTER_SECRET_KEY
security: gate /entitlement/sign sau COSA_RUNTIME_PLANE=control
feat: persist LocalEntitlementSnapshot trong PostgreSQL + startup load
security: add WorkspaceContext + get_workspace_context, áp dụng cho cofounder_api.py + packs_api.py
security: fix hoặc xóa entitlement_guard.py's unauth'd header trust
security: production CORS từ COSA_ALLOWED_ORIGINS, chặn wildcard+credentials khi production
feat: mount capabilities router (read-only /catalog, /grants, /check; /execute sau feature flag)

fix: greeting intent trả Intent.GREETING thật thay vì string-match "greetings" trong reason
fix: Genesis stage default cho workspace mới (chỉ đổi literal, không đổi enum taxonomy)
fix: Hologram approveTask() gọi ApprovalsService.approve() thật, gate theo kết quả
fix: chatWithCoFounder + sendChatMessage trả lỗi thật, xóa fallback "đang điều phối" giả
refactor: cosa_cofounder_service.py — xóa hard-code Pulse/NBA/synthesize, xóa Challenge Mode dead code,
          wire FOUNDER_COMMAND + FOUNDER_DECISION vào ChiefOfStaffOrchestrator.orchestrate() thật
          (bao gồm giải quyết sync/async session mismatch)
feat: mission_control_bus global subscriber + logging listener cho mission_completed
```

Mỗi commit nhỏ, rollback được, đúng nguyên tắc G2 §25/§31.

---

# 12. Nhật ký triển khai Phase 0A/0B/1A (đã code thật, đã test, không chỉ đề xuất)

Toàn bộ mục 9-11 ở trên đã được triển khai thật trong session này, verify bằng full backend test suite trước/sau (baseline sạch: 27 fail có sẵn không liên quan; sau toàn bộ Phase 0A+0B+1A: 26 fail sẵn có — trùng khớp, 1 fail giảm vì xóa hẳn 1 file test của engine chết — 1184 test pass, +25 test mới, zero regression) và `dart analyze`/`flutter test` sạch cho phần frontend.

## 12.1. Phase 0A — đã xong 100%
Ed25519 signing (`entitlement_crypto.py`), gate `/entitlement/sign` qua `COSA_RUNTIME_PLANE`, `LocalEntitlementSnapshot` + reload lúc khởi động, `WorkspaceContext` (file mới `core/workspace_context.py`, áp dụng cho `cofounder_api.py`/`packs_api.py`/`entitlement_guard.py`/router sync), CORS allowlist, đổi tên `AgentRun`→`LegacyPlatformAgentRun`, **xóa hẳn** `control_plane/{planner,execution,router,router_api,context,evaluator}.py` + 4 file test chết theo (đã verify không route nào gọi tới), mount `capabilities` router (`/execute` sau `COSA_ENABLE_CAPABILITY_EXECUTE`), sửa alias `automations_router`.

## 12.2. Phase 0B — đã xong 100%
`deterministic.py` trả `Intent.GREETING` thật; `Workspace.company_stage` default `S0_GENESIS`; frontend `approveTask()`/`sendChatMessage()` (`founder_command_center_controller.dart`, `cofounder_api_service.dart`, `hologram_hub_view.dart`) gọi backend thật + hiện lỗi thật; `cosa_cofounder_service.py` xóa hẳn `synthesize_cross_domain()` và template FOUNDER_COMMAND, `FOUNDER_DECISION`+`FOUNDER_COMMAND` đi qua `ChiefOfStaffOrchestrator.orchestrate()` thật (cần thêm `sync_db` param vì `orchestrate()` dùng sync `Session`, `self.db` trong service là async-wrapped); `get_company_pulse`/`get_next_best_action` bỏ hết filler tĩnh; `mission_control_bus` có `add_global_listener`/`register_default_listeners()`, gắn ở cả `main.py` và `worker_main.py`.

## 12.3. Phase 1A — đã xong phần cốt lõi (dispatch N-agent + child agent_runs thật)

**Đã làm:**
- `chief_of_staff.py`: thêm `SPECIALIST_REGISTRY: dict[str, SpecialistSpec]` (sales/finance/legal) + `orchestrate(..., domains: Optional[list[str]] = None)`. 2 block delegation hard-code (sales, finance) gộp thành 1 loop generic — dispatch domain thứ 3 (`legal`) không cần thêm nhánh `if domain == ...` nào.
- Mỗi lần delegate giờ insert **child `agent_runs` row thật** (canonical `agents.governance.models.AgentRun`, `parent_run_id=mission_id`, status created→running→completed/failed qua `validate_run_transition`) — trước đây chỉ có `parent_run_id` trong `AgentRunRequest` context, không ghi row nào.
- Domain `legal` mới: `LegalDataCapability.read_legal_posture` (đã có sẵn, không bug) được đăng ký thành tool thật `app/business/legal/legal_tools.py::get_legal_posture_summary` (thêm vào `tool_bootstrap.py`), theo đúng pattern `sales_tools.py`/`finance_tools.py`.
- **Phát hiện quan trọng khi wiring legal vào Quality Gate**: `LegalQualityGate` được thiết kế để chấm **output phân tích** (cần `citations`+`disclaimer`), không phải snapshot đọc dữ liệu (`read_legal_posture` không có `citations`) — chạy generic sẽ luôn FAIL sai lý do. Thêm cờ `SpecialistSpec.quality_gate_compatible` (mặc định True, `legal=False`) để tránh false-fail thay vì loop mù quáng qua mọi domain. Đây là bằng chứng cụ thể tại sao việc gắn Quality Gate theo capability cần thiết kế đúng shape (Phase 1C/1E), không thể tự động hóa ngây thơ.
- Quality gate + `synthesis_ctx` tổng quát hóa để đọc từ `specialist_reports` (dict theo domain) thay vì 2 biến `sales_data`/`fin_data` cứng — nhưng `_derive_priorities_and_actions()` (heuristic ưu tiên) **vẫn chỉ xử lý sales/finance** — suy luận ưu tiên cho domain mới là business logic riêng, ngoài phạm vi "tổng quát hóa cơ chế dispatch".
- **Bug tìm thấy & sửa ngay**: `SPECIALIST_REGISTRY`'s `fetch_snapshot` lúc đầu trỏ thẳng vào function object (đóng băng lúc import) — làm hỏng 1 test có sẵn dùng `unittest.mock.patch("chief_of_staff.get_pipeline_summary", ...)` (patch không còn tác dụng vì `orchestrate()` không còn gọi tên module-level đó nữa). Sửa bằng lambda tra cứu tên động (`lambda db, ws: get_pipeline_summary(db, ws)`) để patch-by-module-attribute vẫn hoạt động đúng như trước.
- Test mới: dispatch domain thứ 3 không cần nhánh mới; child `agent_runs` được insert đúng `parent_run_id`; child run chuyển `failed` đúng khi `fetch_snapshot` raise; domain không tồn tại trong registry bị skip êm ái (log warning, không crash).

## 12.4. Phase 1A — phần còn lại: ContextAssembler + Mission DRAFT/confirm (đã xong)

**ContextAssembler** — file mới `app/workforce/agents/context/assembler.py::CofounderContextAssembler`, KHÔNG tái dùng `build_agent_context` hiện có vì nó luôn eager-load cố định 4 domain (sales/finance/okrs/projects) bất kể intent, ngược nguyên tắc "Minimum Viable Context" của G2 §7.2. Assembler mới scope theo `Intent`:
- `GREETING` → `{}` rỗng, 0 query DB (test khẳng định `db.query.call_count == 0`).
- `GENERAL_CHAT`/khác → chỉ `workspace` + `founder_profile`.
- `SALES`/`FINANCE`/`MARKETING`/`LEGAL` → workspace + project + 12wy + pending_decisions + **đúng 1** domain trong `business_signals`.
- `FOUNDER_REVIEW`/`FOUNDER_DECISION`/`FOUNDER_COMMAND`/`FOUNDER_REFLECTION` → full bundle (thêm weekly_plan/top_blockers/pending_approvals/evidence/recent_outcomes).
- `business_signals` tái dùng thẳng `SPECIALIST_REGISTRY[domain].fetch_snapshot` — không tạo đường lấy dữ liệu thứ hai cho cùng 1 domain. Tham số mới `business_signal_domains` cho phép caller (chief_of_staff.py) giới hạn đúng domain mission thật sự cần, tránh fetch thừa domain không liên quan — phát hiện được nhờ 1 test ban đầu vô tình gọi domain chưa mock, gây lỗi kết nối DB thật.
- Mọi field builder try/except độc lập → 1 bảng lỗi không kéo sập cả bundle (test riêng mô phỏng `db.query` luôn raise, xác nhận vẫn trả về structure rỗng thay vì crash).
- Wire vào `chief_of_staff.py`'s bước synthesis qua `synthesis_ctx["cofounder_context"]`.

**Mission DRAFT/confirm state machine** — tái dùng `Outcome` (đã có sẵn `status` default `"draft"` với đúng vocabulary `draft→planning→running→...`, không cần bảng Mission mới, đúng nguyên tắc G2 §2.5):
- Thêm `SpecialistSpec.risk_level` (mặc định `"R0"`, mọi specialist hiện tại đều R0 vì chỉ đọc dữ liệu). `AUTO_START_MAX_RISK = "R1"`.
- `orchestrate()`: tạo `Outcome(status="draft")`/`OutcomeRun(status="queued")`/`AgentRun(status="created")`, lưu `goal`/`domains`/`context`/`intent` vào `AgentRun.metadata_jsonb` (để replay sau, không cần bảng mới). Nếu risk mission ≤ R1 → tự chuyển draft→planning→running và chạy tiếp ngay (auto-start, khớp hành vi hiện tại vì mọi domain đều R0). Nếu risk > R1 → dừng lại, trả `status="waiting_confirmation"`, **không chạy delegation loop**.
- `confirm_mission(db, mission_id, user_id, workspace_id=None)`: nạp lại Outcome/OutcomeRun/AgentRun theo `mission_id`, verify `status=="draft"`, verify `workspace_id` khớp (nếu có truyền — defense in depth, không tin caller), replay đúng `goal`/`domains`/`context` đã lưu (founder không thể "confirm" mission #123 mà lại chạy nội dung khác), rồi gọi lại `orchestrate(..., _resume=...)` để tái dùng đúng các row đã tạo thay vì tạo mission mới.
- API mới: `POST /cofounder/missions/{mission_id}/confirm` (`cofounder_api.py`), dùng `WorkspaceContext` — 403 nếu mission không thuộc workspace của caller, 404 nếu không tìm thấy/không phải draft.
- `cosa_cofounder_service.py`: khi `result.status == "waiting_confirmation"`, trả message rõ ràng yêu cầu founder xác nhận (kèm mission_id) thay vì `result.diagnosis` rỗng.
- **Chưa làm — cố ý, chưa cần thiết**: UI xác nhận Mission trong chat (nút "Xác nhận") — vì mọi specialist hiện tại đều R0 (auto-start), trạng thái `waiting_confirmation` chưa có đường nào trong thực tế kích hoạt được với dữ liệu thật. Cơ chế backend đã sẵn sàng; UI sẽ làm khi Phase 1C+ thêm capability rủi ro cao hơn (gửi email, deploy...).

**Test mới**: greeting→context rỗng; domain intent→scope đúng 1 domain; full-context intent→scope đúng domain của mission; lỗi DB con→degrade an toàn; mission rủi ro cao→ở lại draft không chạy gì; `confirm_mission` chạy đúng goal đã lưu (không tin input từ lời gọi confirm); reject nếu mission không phải draft; reject nếu workspace không khớp (403 defense-in-depth).

**Verify cuối Phase 1A**: full suite trước/sau — 26 fail sẵn có không đổi (+1 fail mới phát hiện nhưng KHÔNG liên quan: `test_progress_snapshot_service.py::test_calculate_current_week_clamping`, bug có sẵn từ trước — test dùng `date.today()` local trong khi implementation dùng `datetime.now(timezone.utc).date()`, lệch ngày do phiên làm việc kéo dài qua mốc nửa đêm UTC/local; không phải regression). 1192 test pass (+33 so với đầu Phase 0A).

## 12.5. Phase 1B — Capability Registry hợp nhất (đã xong, có 1 phát hiện làm thu hẹp phạm vi xóa)

Quyết định ban đầu ở mục 2 ("Capability Registry", THUA: `CAPABILITY_CATALOG` dict → seed 1 lần rồi xóa module) **chỉ đúng một phần** — verify trực tiếp cho thấy `registry.py::get_capability_definition()` không chỉ là tra cứu dict tĩnh, nó còn có ~110 dòng logic **phân loại động** (dynamic classifier): với bất kỳ capability string nào KHÔNG có trong `CAPABILITY_CATALOG` (ví dụ `"sales.research"`, `"n8n.workflow_x"`, `"anything.read"`, `"*.draft"`...), hàm này tự suy ra risk_level/permission_level dựa trên pattern tên. Đây là hành vi runtime thật đang chạy trong `CapabilityGateway.check()`/`execute_with_capability()` cho mọi capability không nằm trong 41 entry cứng — xóa nó sẽ làm mọi capability "ngoài danh mục" bị Default Deny sai, một regression thật chứ không phải dọn dẹp. Quyết định: **giữ `registry.py`**, không xóa; ranh giới lại rõ ràng hơn quyết định ban đầu — dict `CAPABILITY_CATALOG` hạ cấp thành seed fixture (nguồn import 1 lần), còn phần dynamic-derivation vẫn là logic sống, tách bạch khỏi phần data đã merge vào DB.

**Đã làm:**
- `founder_os/strategy/models.py::CapabilityDefinition` mở rộng thêm 10 field (migration `v13_055_canon_capability`, `op.batch_alter_table` idempotent-safe) để chứa được đủ 3 shape: `description`/`domain`/`owner_agent_key`/`status`/`source`/`source_pack_key`/`requires_approval`/`content_jsonb`/`metadata_jsonb`/`updated_at`. `workspace_id`/`brain_id` nới thành nullable (capability toàn cục từ registry/pack không thuộc riêng workspace nào).
- `capability_registry_seed_service.py` (file mới): 2 pass idempotent-upsert (theo `capability_key`+`source`+`workspace_id IS NULL`) — `seed_runtime_registry_capabilities()` import 41 entry từ `CAPABILITY_CATALOG` (giữ nguyên `resource`/`action`/`permission_level`/`original_risk_level`/`original_domain` trong `metadata_jsonb` để redirect phía dưới tái tạo lại đúng object cũ), `seed_business_pack_capabilities()` import 48 capability từ 11 business pack qua `BusinessPackLoader` có sẵn (không tự parse lại YAML). Gọi cả 2 ở `main.py`'s `lifespan` mỗi lần khởi động — an toàn vì idempotent.
- **Redirect 2 consumer thật**: `capabilities/service.py` thêm `resolve_capability_definition(db, capability)` — tra DB canonical trước (`source="runtime_registry"`), map ngược `metadata_jsonb` thành đúng shape `registry.CapabilityDefinition` cũ (kể cả `RiskLevel`/`PermissionLevel` enum), chỉ fallback về `get_capability_definition()` (dynamic classifier) khi DB miss. `CapabilityGateway.check()`/`execute_with_capability()` giờ gọi hàm này thay vì gọi thẳng registry. `/catalog` endpoint (`capabilities/router.py`) đổi hẳn sang query DB (`source="runtime_registry"`, `status="ACTIVE"`), filter theo `domain` cũ đọc từ `metadata_jsonb["original_domain"]` để giữ đúng semantics endpoint trước đó.
- Verify hành vi: test mới `test_capability_check_uses_db_canonical_row_over_static_catalog` chứng minh 1 row DB (admin sửa risk_level thành REGULATED) thắng đúng entry tĩnh trong dict cho cùng capability_key — proof DB đã thực sự canonical, không phải chỉ mount thêm cho có.
- 3 test file có SQLite fixture tự dựng (`test_capability_gateway.py`, `test_action_center.py`, `test_observation_provenance.py`) thiếu bảng `capability_definitions` mới — build lỗi `no such table` khi `resolve_capability_definition` query — sửa bằng thêm `CanonicalCapabilityDefinition.__table__` vào danh sách bảng test tạo.

**Cố ý chưa làm — phạm vi ngoài "merge 3 bản":**
- `business/packs`' live request path (Business Packs Store) **vẫn đọc YAML trực tiếp** qua `BusinessPackLoader`, không đổi sang đọc từ `capability_definitions`. Bảng DB giờ có đủ 48 dòng business-pack (nguồn tra cứu chéo/canonical inventory), nhưng con đường phục vụ UI Store thật chưa trỏ vào đó — đây là follow-up cơ học, không phải phần bắt buộc của việc "gộp 3 model thành 1", vì risk thay đổi hành vi UI Store hiện tại (đã chạy ổn, có override-aware logic) không tương xứng với lợi ích ở phase này.
- 11 business pack **không** bị quy nhóm lại theo 5 Domain Agent (rủi ro product đã nêu ở mục 6, chưa có quyết định founder) — `PACK_DOMAIN_MAP` trong seed service map 4/11 pack sạch, 7 pack còn lại về `CROSS_DOMAIN`, đúng tinh thần "không tự ý quyết định sản phẩm".

**Verify cuối Phase 1B**: full suite trước/sau (stash-based) — baseline 28 fail (main, có `test_control_plane.py` vì file này chỉ bị xóa ở nhánh làm việc từ Phase 0A) khớp đúng 27 fail trên nhánh làm việc (28 − 1 file đã xóa từ trước) + 0 regression thật. 1198 test pass.

## 12.6. Phase 1C — Toolset Resolver + Skill Registry Versioning (đã xong, deliverable gốc bị thu hẹp/điều chỉnh sau khi verify thực địa)

Trước khi viết code đã dispatch 2 Explore agent song song để lập bản đồ chính xác hệ tool registry và hệ skill registry. Cả 2 báo cáo đều cho thấy giả định ban đầu ở mục Phase 1C (mô tả gốc phía trên) sai ở vài điểm quan trọng — sửa lại đúng thực tế trước khi code thay vì làm đúng-chữ-nhưng-sai-nghĩa kế hoạch cũ, cùng kỷ luật đã áp dụng ở Phase 1B.

**Phát hiện làm đổi hướng deliverable "mở rộng tool_flat_names từ 7 lên 15+":**
- `AgentPreset.tool_flat_names` (7 agent key, `agents/registry/presets.py`) **không hề được đọc** ở 2 nơi thật sự dựng schema tool gửi cho LLM (`company_tools.py::tool_specs()` và `deepseek_harness.py`'s tool loop) — đây là một manifest khai báo nhưng chưa từng được enforce, gần như tách rời khỏi runtime.
- Cơ chế Agent×Tool THẬT đang chạy là `ToolSpec.allowed_agent_keys` (field có sẵn, set trực tiếp tại từng lệnh gọi `@register(...)`) — `deepseek_harness.py` đã tự lọc bằng field này từ trước.
- Ngoài ra hệ thống có tới **3 vùng tên agent-key không trùng khớp nhau**: `AGENT_PRESETS` (7 key), `DEFAULT_AGENT_MANIFESTS`/bảng `agent_definitions` (22 key, DB-backed, trông "canonical" nhất trên giấy nhưng KHÔNG phải cơ chế gating thật), và `trust_boundary.yaml` (một biến thể tên thứ 3). Việc "mở rộng tool_flat_names lên 15+" giả định `AGENT_PRESETS` là vùng tên thật — không đúng. Quy về 1 vùng tên canonical là một quyết định lớn, rủi ro cao (đổi tên chuỗi literal rải rác ở ≥4 file `allowed_agent_keys=[...]`, dễ âm thầm gãy ACL) và **không cần thiết để Toolset Resolver hoạt động đúng** — resolver chỉ cần đọc đúng `allowed_agent_keys` sẵn có. Quyết định: **không đụng tới việc canonical hóa vùng tên agent-key trong phase này**, để lại làm technical debt đã ghi nhận rõ, không phải việc bị bỏ sót.

**Đã làm — Toolset Resolver:**
- `ToolSpec` (`core/tool_registry.py`) thêm 4 field mới, tất cả default trung tính (không ảnh hưởng ~30 tool đã đăng ký): `availability_check` (callable fail-closed), `side_effect_type` (phân loại tự do, chưa gán cho tool nào), `execution_backend` (mặc định `"native"`), `available_stages` (mặc định `None` = không giới hạn stage).
- File mới `core/toolset_resolver.py::resolve_toolset(db, workspace_id, agent_key=None, company_stage=None, require_chat_schema=False)` — lọc theo thứ tự: feature flag (tái dùng `available_tools` có sẵn) → `allowed_agent_keys` (bỏ qua nếu `agent_key=None`) → `available_stages` → `availability_check` (bọc try/except, lỗi/False đều loại tool, fail-closed đúng tinh thần default-deny của `CapabilityGateway`).
- Redirect 2 call site thật: `company_tools.py::tool_specs()` gọi `resolve_toolset(..., agent_key=None, require_chat_schema=True)` — **cố ý giữ `agent_key=None`** vì chat surface chưa từng có khái niệm 1 agent duy nhất, thêm lọc `allowed_agent_keys` ở đây sẽ là thay đổi hành vi (ẩn bớt tool đang hiện), không phải chỉ thêm cơ chế. `deepseek_harness.py`'s tool loop gọi `resolve_toolset(db, ws_id, agent_key=request.agent_key)` thay hẳn list-comprehension thủ công cũ.
- Test mới `test_toolset_resolver.py` (9 case): fail-closed khi `availability_check` trả False/raise exception, context truyền đúng agent_key/workspace_id/company_stage, `available_stages` lọc đúng, `agent_key=None` giữ nguyên hành vi chat cũ, `require_chat_schema` gộp đúng 2 điều kiện `chat_tools()` cũ.
- **Cố ý chưa làm**: chưa gán `availability_check`/`available_stages`/`side_effect_type` cho bất kỳ tool thật nào — quyết định TOOL NÀO giới hạn theo stage nào là quyết định sản phẩm (ví dụ "email.send chỉ available từ S3+"), không phải thứ suy ra được từ code. Hạ tầng đã sẵn sàng, gán giá trị là việc của phase sau khi có input sản phẩm cụ thể.

**Đã làm — Skill Registry Versioning:**
- **Phát hiện quan trọng, sửa lại hiểu biết cũ**: kế hoạch gốc giả định có "3 loader SKILL.md cạnh tranh nhau" cần hợp nhất — thực tế cả 3 cây (`workforce/skills/*` 6 file, `workforce/agents/skills_library/*` 2 file, `business/packs/factory/*/skills/*` 20 file) **đã được quét bởi đúng 1 hàm** `DynamicSkillLoader.scan_physical_skills()` từ trước (`search_dirs` liệt kê cả 3). Exit criterion "không còn runtime import nào trỏ tới 3 loader cũ" **coi như đã đạt từ trước khi phase này bắt đầu** — không có gì để xóa/hợp nhất ở đây, khác với capability registry ở Phase 1B nơi thực sự có 3 model riêng biệt.
- **Bug tìm thấy & sửa (vi phạm Runtime Truth)**: `workforce/skills/router.py`'s `list_skills()` (GET, trông như read-only) có side-effect tự động seed + **tự động promote thẳng lên `active`**, gán `approved_by_user_id = current_user.id` — tức là người dùng đầu tiên mở trang Skills của workspace vô tình trở thành "người đã duyệt" toàn bộ 28 skill built-in mà không hề bấm duyệt gì. `sync-built-in` endpoint có cùng lỗi. Sửa bằng service method mới `seed_platform_skill()`: set thẳng `status="active"`, `is_system=True`, **không gán `approved_by_user_id`** (không bịa người duyệt) — khác hẳn `promote_skill()` (vẫn giữ nguyên invariant "NO AGENT SELF-PROMOTION", áp dụng cho candidate/trajectory/upload).
- `SkillRegistryItem` thêm cột `is_system: bool` (migration `v13_056_skill_registry_v`) — hiện thực hóa "platform-immutable vs workspace-fork": `update_skill()` giờ raise `PermissionError` nếu `item.is_system`, buộc founder muốn tùy biến 1 skill built-in phải tạo skill mới do workspace tự sở hữu thay vì sửa đè bản gốc. Không thêm `forked_from_id` (liên kết fork→gốc) vì kiến trúc hiện tại chưa có khái niệm "1 skill gốc dùng chung nhiều workspace" — mỗi workspace tự seed bản riêng, không có gốc chung để trỏ về; thêm cột đó lúc này sẽ là suy đoán, không phục vụ nhu cầu thật nào.
- Thêm state mới vào vocabulary của `status` (cột String(30) không ràng buộc, không cần migration schema): `experimental` (qua `promote_skill(..., target_status="experimental")`, vẫn cần người duyệt thật), `archived` (`archive_skill()`, nghỉ hưu hẳn), `blocked` (`block_skill()`, kill-switch khẩn cấp, **bắt buộc phải có `reason`** — khác `deprecate`/`archive` vốn optional, vì đây là ghi đè trạng thái bất kỳ không qua luồng thường). 3 endpoint API mới: `POST /{skill_id}/archive`, `POST /{skill_id}/block`, `POST /{skill_id}/promote` nhận thêm body tùy chọn `target_status`.
- Test mới `test_skill_registry_versioning.py` (10 case): seed platform skill không bịa approver, vẫn chạy safety scanner, promote mặc định active/có thể target experimental, reject target_status không hợp lệ, archive/block đúng hành vi, block bắt buộc reason, update_skill từ chối sửa skill `is_system=True` nhưng vẫn cho sửa skill do workspace tự tạo.

**Verify cuối Phase 1C**: full suite — 27 fail khớp đúng baseline đã xác lập từ Phase 1B (0 regression), 1217 test pass (+19 so với cuối Phase 1B — đúng bằng 9 test resolver + 10 test skill versioning mới).

## 12.7. Phase 1D — Stage Operating Engine (đã xong, phát hiện lớn nhất: "phần lớn engine đã có sẵn")

Trước khi code, dispatch 1 Explore agent map toàn bộ hệ stage. Kết quả đảo ngược hẳn giả định ban đầu của roadmap (mục "Phase 1D — Stage Operating Engine S0-S6"): đây **không phải** primitive cần xây từ đầu.

**Sự thật phát hiện được:**
- `Project.project_stage` đã có **một engine S0-S6 hoàn chỉnh, thật, evidence-gated**: `StageGateService.evaluate_stage_readiness()` tính điểm từ dữ liệu thật (`Hypothesis.evidence_score`, `Evidence.ladder_level`, `PestelSignal`, `SwotItem.evidence_refs`) ra `StageTransitionAudit` (readiness_score/APPROVED/CONDITIONAL/REJECTED), `apply_stage_advancement()` mới thực sự ghi `project.project_stage`. Có đầy đủ guardrail chống premature-scaling (`PrematureScalingAlert`, cảnh báo BSC dùng sớm). Frontend cũng đã xây đầy đủ và **đã mount**: `stage_service.dart`, `stage_badge.dart`, `stage_selector_header.dart`, `stage_gate_audit_modal.dart`.
- Ngược lại, `Workspace.company_stage` (field mà roadmap tưởng là trọng tâm S0-S6) **chưa từng được ghi ở bất kỳ đâu** ngoài giá trị default lúc tạo workspace — `grep "\.company_stage\s*="` toàn repo ra 0 kết quả. Không frontend nào đọc nó.
- Phát hiện thêm: G2 §9.1 (Stage matrix văn bản), `ProjectStageEnum` (code thật), và `Workspace.company_stage` (chỉ có 1 giá trị thật) là **3 biến thể vocabulary khác nhau** cho cùng 1 khái niệm S0-S6 (ví dụ G2 tách "Problem Discovery"/"Problem Validation" thành 2 stage, `ProjectStageEnum` gộp làm 1 `S1_PROBLEM_VALIDATION`). Quyết định: **không đổi tên `ProjectStageEnum`** để khớp chữ với G2 — rủi ro/lợi ích không tương xứng cho một hệ đã chạy thật đầy đủ 2 đầu BE/FE; chỉ ghi nhận lệch chữ.

**Quyết định canonical**: `Project.project_stage` (qua `StageGateService`) tiếp tục là engine chuyển giai đoạn DUY NHẤT — không xây engine thứ hai cho `company_stage`. Thay vào đó biến `company_stage` thành **giá trị phái sinh thật**, đồng bộ theo dự án chủ lực (P0/mới nhất, cùng quy ước với `StageResolverService._resolve_project()`), thay vì tiếp tục đóng băng ở default.

**Đã làm:**
- `StageGateService.apply_stage_advancement()` thêm `_is_primary_project()` + đồng bộ `workspace.company_stage = audit.to_stage` **chỉ khi** dự án vừa nâng cấp là dự án chủ lực của workspace (dự án phụ nâng cấp không ảnh hưởng company_stage — 1 workspace có thể có nhiều dự án ở stage khác nhau). Bug tự phát hiện qua test: quên bọc `desc()` quanh `strategic_priority == "P0"` trong `order_by`, đảo ngược thứ tự ưu tiên — sửa ngay, khớp đúng quy ước gốc trong `stage_resolver_service.py`.
- `core/toolset_resolver.py` thêm `get_workspace_company_stage(db, workspace_id)` — cả 2 call site thật của Phase 1C (`company_tools.py`, `deepseek_harness.py`) đổi từ truyền `company_stage=None` (placeholder từ Phase 1C) sang giá trị thật. Test end-to-end mới `test_stage_advancement_flows_end_to_end_into_the_live_chat_toolset` chứng minh đúng **exit criterion đề ra ban đầu**: 1 tool gắn `available_stages` tự xuất hiện/biến mất trong `tool_specs()` thật khi dự án chủ lực nâng cấp giai đoạn qua cổng thẩm định — không sửa 1 dòng nào trong `resolve_toolset()`.
- `cosa_cofounder_service.py::get_next_best_action()` (endpoint thật `/cofounder/top3`, đang hiển thị trên Hologram Hub) — trước đây 0 lượt đọc "stage" nào trong toàn file. Thêm `_build_stage_goal_action()`: khi Top3 còn chỗ trống, đọc `project_stage` thật của dự án chủ lực, lấy `primary_goal` thật từ `ManagementPolicyEngine.get_policy()` (nguồn sự thật G2 §9.1 Stage matrix, không bịa số/chuỗi). `get_company_pulse()` cũng thêm field `company_stage` (giá trị thật, cả 2 nhánh Genesis và bình thường).
- Frontend: `CompanyPulseModel` thêm field `companyStage`; `hologram_hub_view.dart`'s header giờ hiện `StageBadge` (tái dùng widget đã có cho `Project.project_stage`, `ProjectStage.fromString()` map "S0_GENESIS" về hiển thị S0 hợp lý — không viết widget hiển thị stage lần thứ 2). `dart analyze` sạch, `flutter test` qua hết.
- Test mới: `test_stage_operating_engine.py` (5 case, DB SQLite thật không mock) + 5 case bổ sung trong `test_phase2_cofounder_engine.py` (đọc `project_stage`/`company_stage` thật, None khi không có dự án).
- 2 test file có sẵn (`test_phase2_cofounder_engine.py`, `test_phase5_cofounder_e2e.py`) dùng `db_mock.execute.return_value = <1 mock dùng chung cho mọi query>` — collision với query `company_stage` mới (Pydantic reject vì nhận nhầm int đếm dòng thay vì string). Sửa bằng `side_effect` phân biệt theo nội dung SQL, cùng pattern đã dùng ở Phase 1B/1C.

**Phát hiện quan trọng, cố ý CHƯA xử lý trong phase này — 1 fork kiến trúc mới, độ lớn tương đương AgentRun/Capability/Orchestrator ở các phase trước:**
- Tồn tại **engine Next Best Action thứ 2**, đầy đủ hơn hẳn: `NextBestActionService` (mCOSA V12 Spec §37) — chấm điểm R0 (Urgency/Impact/Effort) + R1 rule bonus + R2 AI rerank thật, sinh candidate từ `GateDecision`/`ProjectPestelImpact`/`Hypothesis`/**`StageTransitionAudit` weak-areas**/`TowsOption` — đã stage-aware sẵn, tốt hơn bản vá tối thiểu vừa thêm ở trên. Có router thật đã mount (`/api/v1/strategy/ceo/next-actions`), feature flag bật mặc định (`FLAG_NEXT_BEST_ACTION_V12 = True`), **và có widget frontend riêng** `next_actions_panel.dart` — nhưng widget này **không được import ở bất kỳ đâu khác**, tức chưa từng render cho founder thấy. Widget đang thật sự hiển thị (`top3_focus_widget.dart` trong `hologram_hub_view.dart`) đi qua `/cofounder/top3` — bản mỏng hơn, vừa được vá tối thiểu ở phase này.
- Không gộp 2 engine trong phase này vì: (1) `evaluate_and_rank()` ghi `NextActionCandidate`+`NextActionRanking` row MỚI vào DB mỗi lần gọi — gắn thẳng vào endpoint `/cofounder/top3` (khả năng bị gọi lại mỗi lần Hologram Hub load/refresh) sẽ phình bảng nhanh, cần xem lại chiến lược cache/idempotency trước; (2) lại là bài toán sync/async quen thuộc (`NextBestActionService` cần sync `Session`, `cosa_cofounder_service.py` dùng `AsyncSession`) cần thread `sync_db` giống các lần trước — không khó nhưng tốn thêm 1 pass riêng; (3) quyết định "mount `next_actions_panel.dart` ở đâu trong Hologram Hub, có thay hẳn `top3_focus_widget.dart` không" là quyết định UI/product, không tự quyết. Ghi nhận rõ ở đây làm việc cần làm cho phase sau, không lặp lại kiểu "gateway/router.py chết tưởng sống" đã gặp ở Phase 0A.
- Cũng cố ý chưa làm: "capability recommendation" stage-gated (gán `available_stages` thật cho các dòng `capability_definitions`/tool thật theo đúng Stage matrix G2 §9.1) và "PESTEL/SWOT/TOWS/BSC as capability" — cả hai đều là quyết định product (cái gì áp dụng cho giai đoạn nào) chứ không suy ra được từ code; BSC đã có cảnh báo `PREMATURE_BSC_OVERENGINEERING` (WARNING, không phải hard block) làm lớp phòng vệ tạm đủ dùng.

**Verify cuối Phase 1D**: full suite (so với baseline Phase 1C) — 26 fail (giảm 1 so với 27 vì `test_progress_snapshot_service.py::test_calculate_current_week_clamping` hết flaky theo mốc thời gian, không liên quan thay đổi của phase này), 0 regression thật. 1228 test pass (+11 so với cuối Phase 1C). Frontend: `dart analyze` + `flutter test` sạch cho mọi file đã sửa.

## 12.8. Phase 1E — Learning Review Worker + Memory Promotion + Subrun hardening (đã xong, thu hẹp có chủ đích ở 2 mục con)

Trước khi code, dispatch 2 Explore agent song song map toàn bộ Learning/Proposal/Memory/Subrun/Frontend. Không phát hiện nào đảo ngược tiền đề như 2 phase trước, nhưng có vài chi tiết cấu trúc quan trọng làm thay đổi cách triển khai.

**Đã làm — Learning Review Worker:**
- File mới `workforce/agents/learning/review_worker.py::LearningReviewWorker`. Bất biến an toàn (G1 §6) được đảm bảo **cấu trúc**, không chỉ quy ước: mỗi entrypoint tự mở `SessionLocal()` riêng, commit, đóng — không bao giờ nhận session của caller, nên worker lỗi không bao giờ rollback được state thật của caller và ngược lại. Chỉ ghi `AgentProposal(proposal_type="learning_candidate")` + (khi có) `SkillTrajectoryCandidate` qua đúng service đã có sẵn (`SkillLifecycleService.create_candidate_from_trajectory`, đã safety-scan PII/secret từ trước) — không bao giờ đụng `ApprovalRequest`/`WorkProduct`/`AgentRun`/`Outcome`.
- **Phát hiện cấu trúc quan trọng**: `AgentProposalService.create_proposal()` (hàm helper có sẵn) bắt buộc payload phải qua `parse_proposal_command()`, chỉ chấp nhận đúng 3 `command_type` literal (`okr_objective.create`/`strategy_task.create`/`project_cycle.setup`, `extra="forbid"`) — nghĩa là **không thể** tạo proposal `learning_candidate` qua helper đó. Worker insert `AgentProposal` trực tiếp, bỏ qua `create_proposal()`. Điều này VÔ TÌNH càng làm chắc bất biến an toàn: `AgentProposalService.apply_proposal()`'s type-dispatch chỉ nhận 3 type đó, `learning_candidate` rơi thẳng vào nhánh `else: raise HTTPException(400, "Unsupported proposal type")` — kể cả bấm nhầm "Apply" cũng không thể tự thực thi được gì.
- 3 nguồn trigger, đúng như kế hoạch: (1) `mission_control_bus` — nâng `register_default_listeners()` từ chỉ-logging (Phase 0B) thành đăng ký thêm `LearningReviewWorker.on_mission_terminal_event` làm listener thứ 2 (giữ nguyên listener logging cũ, không thay thế). Chỉ xử lý `MISSION_COMPLETED` — `MISSION_FAILED` chỉ có `{reason, message}`, không có trajectory nào để học. (2) `WorkProductService.request_revision()`/`reject_work_product()` (method **mới** — `WorkProduct.status="REJECTED"` đã có sẵn trong vocabulary từ trước nhưng chưa từng có method nào set nó, chỉ có accept/revise; thêm luôn endpoint `POST /work-products/{id}/reject` khớp đúng pattern 2 endpoint đã có). (3) `ApprovalInboxService.reject()`/`request_revision()`.
- Mission-completed path đọc thật: `AgentRun` con theo `parent_run_id`, `AgentToolCall.tool_name` thật (không suy đoán), resolve `source_outcome_id` thật qua chuỗi FK có sẵn `AgentRun.outcome_run_id → OutcomeRun.outcome_id` (đường đi không ai dùng tới trước đây nhưng hoàn toàn có thật).
- **Bẫy circular import tự gây ra & tự sửa**: import `review_worker.py` ở top-level trong `approval_service.py`/`work_product_service.py` kéo theo toàn bộ package `orchestration` (`chief_of_staff.py` và mọi thứ nó import) — làm vỡ 1 import vòng không liên quan qua `workforce/__init__.py → skill_loader.py → permission_engine.py → governance/__init__.py → approval_service.py`, phát hiện qua `test_migration_metadata.py` (2 test fail mới xuất hiện). Sửa bằng lazy import (bên trong hàm, đúng pattern đã dùng sẵn trong chính `review_worker.py` và `mission_control_bus.register_default_listeners()`), khớp nguyên tắc layering: service governance cấp thấp không nên eager-import cả package orchestration cấp cao.
- `AgentProposal` mở rộng 6 field mới (`domain`/`target_key`/`diff_jsonb`/`confidence`/`evidence_ids_jsonb`/`source_outcome_id`, migration `v13_057_learning_memory`), tất cả nullable, chỉ `learning_candidate` dùng.
- Test mới `test_learning_review_worker.py` (10 case, DB SQLite thật): đúng 1 proposal/mission, trích đúng `SkillTrajectoryCandidate`, gộp domain thành `cross_domain` khi >1 specialist, resolve đúng `source_outcome_id` thật, bỏ qua `mission_failed`, không ghi gì khi 0 domain/event hỏng, và quan trọng nhất — **test khẳng định số dòng `AgentRun`/`AgentToolCall` không đổi** trước/sau khi worker chạy (chứng minh "chỉ đọc mission" bằng dữ liệu thật, không chỉ assert mock).

**Đã làm — Memory:**
- **Phát hiện làm giảm mức độ nghiêm trọng của blocker hạ tầng đã lo trước (TencentDB sidecar)**: retrieval unranked/không giới hạn (`list_layer_memories`/`get_founder_rules`) hoàn toàn thuộc `AgentMemoryEntry` — bảng Postgres cục bộ, **độc lập với sidecar TencentDB** (sidecar chỉ đứng sau `TencentDBAgentMemoryAdapter`, một class hoàn toàn khác, tự động degrade về `NullAgentMemoryAdapter` khi flag tắt hoặc sidecar chết). Sửa ranked/budgeted retrieval **không cần** xác nhận sidecar hoạt động như lo ngại ban đầu.
- `list_layer_memories()` giờ sắp theo `relevance_score DESC, last_accessed_at DESC` (cột `relevance_score` đã tồn tại từ trước, default 1.0, nhưng **chưa từng được đọc ở đâu** — silent no-op). `get_founder_rules()` trước đây **không có LIMIT nào cả** (dump toàn bảng L2_FOUNDER) — giờ dùng chung `list_layer_memories()`. Thêm hằng số cứng `MAX_MEMORY_RESULTS=200`, mọi query đều clamp về giá trị này bất kể caller truyền limit gì.
- Gộp `AgentMemoryItem` (`control_plane/models.py`, bảng `agent_business_memories`) vào `workforce/memory` rồi xóa hẳn, đúng theo kế hoạch — verify trước bằng grep: 0 reader production, đúng 1 writer (`LearningWriter.record_learning()`, bản thân hàm này cũng 0 caller production, chỉ chạy trong test). `AgentMemoryEntry` thêm 2 cột `domain`/`provenance_jsonb` (migration cùng file `v13_057`) để giữ đúng shape cũ; `LearningWriter` giờ ghi qua `FiveLayerMemoryManager.store_memory()` — một write path duy nhất, không còn 2 bảng song song cho cùng khái niệm.
- Test mới `test_memory_ranked_retrieval.py` (5 case): rank đúng theo relevance trước recency, cap cứng hoạt động dù caller đòi limit khổng lồ, `get_founder_rules` có rank+cap, domain/provenance được lưu đúng.

**Đã làm — Subrun hardening:**
- **Phát hiện thực địa quan trọng**: đọc kỹ `chief_of_staff.py`'s delegation loop cho thấy **subrun depth >1 hiện không thể xảy ra** — mỗi specialist delegation gọi `spec.fetch_snapshot(db, workspace_id)`, một hàm Python đọc dữ liệu thuần túy, KHÔNG phải một lời gọi `orchestrate()` đệ quy; và `orchestrate()` không có tham số nào để tự nhận một `parent_run_id` cho chính nó. "Giới hạn max_depth=1" vì vậy không phải sửa một lỗ hổng đang sống, mà là **rào chắn phòng ngừa** cho ngày một specialist trong tương lai trở thành 1 agent-runtime loop thật (qua `deepseek_harness.py`) thay vì hàm đọc dữ liệu trực tiếp.
- Thêm hằng số `MAX_SUBRUN_DEPTH=1` + guard: nếu `AgentRun` của chính mission đang chạy đã có `parent_run_id` (tức bản thân nó đã là 1 subrun), từ chối toàn bộ delegation loop (log warning, `active_domains=[]`) thay vì đệ quy thêm 1 tầng. Test mới cố tình bơm thẳng 1 `AgentRun` đã có `parent_run_id` qua tham số `_resume` (cùng cơ chế `confirm_mission()` dùng) để buộc code đi đúng nhánh guard — chứng minh guard thật sự chặn, không chỉ tồn tại trên giấy.
- Toolset-per-subrun: không cần cơ chế mới — `permission_profile="read_only"` (đã có từ Phase 1A) đã hẹp hơn permission của mission cha qua chính `PolicyEngine` có sẵn; và vì delegation không phải tool-loop thật nên Toolset Resolver (Phase 1C) chưa có gì để áp dụng lên nó — sẽ tự động áp dụng đúng lúc delegation trở thành tool-loop thật (không cần sửa gì thêm khi ngày đó tới, nhờ `agent_key` đã truyền đúng qua `AgentRunRequest`).
- **Cố ý CHƯA làm**: budget/timeout riêng cho subrun (`BudgetTracker.check()` hiện chỉ tính trên `agent_run` cha, dùng 1 pool ngân sách chung cho cả mission tree) và cancel/steer cho 1 subrun cụ thể (không tồn tại ở tầng orchestration, chỉ có cancel 1 lời gọi LLM đơn lẻ ở tầng adapter) — cả hai đòi hỏi thiết kế mới không nhỏ cho một tình huống (subrun chạy lâu/runaway) hiện chưa xảy ra được với shape code hiện tại (mọi `fetch_snapshot` hoàn thành gần như tức thời). "Ẩn khỏi UI founder" đã đúng sẵn — subrun con chưa từng có UI riêng.

**Đã làm — Frontend:**
- `waiting_for_you_widget.dart` (trước đây chỉ có nút "Phê duyệt") thêm nút "Từ chối" — bấm mở dialog nhập lý do (bắt buộc, khớp `ApprovalInboxService.reject()`'s `reason: str` không optional), gọi `controller.rejectTask()` mới → tái dùng đúng `ApprovalsService.reject()` mà module `approvals` độc lập đã dùng, không viết service call thứ 5 cho cùng 1 hành động.
- `dart analyze` sạch (chỉ info-level pre-existing), `flutter test` qua hết.

**Cố ý thu hẹp phạm vi — ghi rõ lý do, không lặng lẽ bỏ:**
- **Port UI Skills/Tools/Permissions per-agent từ `ai_team` sang `hologram_hub`**: kế hoạch gốc giả định UI này "khó tới, gắn vào shell dashboard cũ" — verify thực địa cho thấy nó **đã reachable thật** (`dashboard_view.dart` case 20, không orphan như `next_actions_panel.dart` ở phát hiện dưới). `AiTeamAgentDetailModal` là UI thật, phức tạp (system prompt editor, tool picker, model profile selector), nối backend thật — port nguyên khối này là việc lớn, không có exit criterion cụ thể để verify "xong", nên hoãn — mức độ cấp thiết thấp hơn hẳn so với giả định ban đầu vì UI không hề bị mất khả năng truy cập.
- **Budget/timeout + cancel/steer riêng cho subrun**: xem mục Subrun hardening ở trên — hoãn vì chưa có tình huống thật nào cần tới.

**Phát hiện quan trọng ngoài phạm vi yêu cầu, ghi nhận làm nợ kỹ thuật cho phase sau:** tồn tại **engine Next Best Action thứ 2** hoàn chỉnh hơn hẳn bản đang sống (`NextBestActionService`, đã ghi ở §12.7 Phase 1D) — không xử lý ở đây vì nằm ngoài phạm vi Phase 1E, chỉ nhắc lại để không bị quên khi lên kế hoạch phase kế tiếp.

**Verify cuối Phase 1E**: full suite — 26 fail khớp đúng baseline đã xác lập từ Phase 1D (0 regression), 1244 test pass (+16 so với cuối Phase 1D). Frontend: `dart analyze` + `flutter test` sạch.
