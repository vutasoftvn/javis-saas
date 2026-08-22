# Tách `cosa_core` — nền tảng Agent Harness tái sử dụng được

**Status:** SUPERSEDED BY docs/architecture/COSA_ARCHITECTURE_ADJUSTMENT_ADDENDUM_2026-08-22.md (§2.5) — Đợt 1 KHÔNG được bắt đầu. Lý do chính: bounded-context của plan này tạo một Control Plane Python thứ hai (auth/control_plane/identity), trùng `services/control-plane` + `services/identity` đã tồn tại. Lý do phụ: giả định `backend/` là monolith đang sống không còn đúng (đã tách vào `legacy/`, frozen theo ADR-012). Chi tiết: docs/architecture/COSA_ARCHITECTURE_REVIEW_2026-08-22.md.
**Date:** 2026-08-22
**Liên quan:** `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`, `docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md`

## Context

`javis-saas` hiện là một backend Python monolith (không có `pyproject.toml` con nào, không có ranh giới package). Kiến trúc COSA đã được thiết kế theo mô hình phân lớp (Business Core / Co-founder Orchestrator / Agent Runtime / Agent Profiles / Skills / Tools / Workflows / Memory / Executors — xem `CLAUDE.md`), và tài liệu `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` đã xác định rõ ai sở hữu cái gì. Tuy nhiên tất cả các lớp này đang nằm chung trong một app, import chéo tự do, không có gì ngăn cản code nghiệp vụ (CRM, Finance, chính sách tài trợ chính phủ...) rò rỉ vào lớp hạ tầng agent.

Người dùng muốn, **ngay từ giai đoạn hiện tại**, tách phần "core" (Agent Harness + hạ tầng nền tảng tổng quát) ra khỏi phần nghiệp vụ đặc thù của javis-saas, để sau này dùng lại làm nền cho các hệ thống AI Agent khác. Mục tiêu không phải là viết lại (rewrite) — mà là **di chuyển (move, không copy)** code đã có vào một package riêng, có ranh giới import rõ ràng, trong cùng monorepo.

Các quyết định phạm vi người dùng đã chốt:
- **Phạm vi rộng**: không chỉ phần runtime agent thuần, mà cả các phần tổng quát của `platform_core` (auth, control_plane/multi-tenancy, WorkforceMember identity) đều nằm trong initiative tách này.
- **Hình thức**: package Python riêng (`backend/cosa_core/`, có `pyproject.toml` riêng) nằm trong cùng monorepo — không tách repo Git riêng.
- **DeepSeek Harness = runtime mặc định của core**: không chỉ interface, mà cả implementation DeepSeek Harness đầy đủ nằm trong `cosa_core`, `deepseek-harness-sdk` là dependency chính thức của package core. Đây là runtime chính (không phải plugin ngoại vi) — vì bản thân DeepSeek Harness chính là engine thực thi agent, là giá trị cốt lõi của nền tảng, không phải một "vendor LLM" cần cách ly.
- **Google ADK LÀ orchestrator sản xuất chính thức của core** — theo đúng hướng đã chốt ở `COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md` (Quyết định 1, 2026-08-20/21): `AdkCofounderWorkflow` (dựng bằng `google.adk.workflow.Workflow/Graph/FunctionNode` thật, đã verify bằng import trực tiếp `google-adk==2.7.0`) thay thế hoàn toàn `ChiefOfStaffOrchestrator`, không chạy song song 2 orchestrator. **Không build orchestrator mới** — di chuyển nguyên trạng code ADK thật đã chạy production (`workforce/agents/orchestration/adk/*` + `service.py` làm seam mỏng) vào `cosa_core`. Ràng buộc bắt buộc phải giữ khi move: **test chống ADK bypass GovernanceKernel** (lý do lần tích hợp ADK đầu tiên thất bại) phải đi theo, không được bỏ.
- **ID: dùng thuần Snowflake ID cho mọi model mới/di chuyển trong `cosa_core`, không dùng UUIDv7** — khớp đúng Quyết định 5 (bản sửa cuối) của chính tài liệu ADK proposal. Dùng lại `core.snowflake.generate_snowflake_id`/`generate_snowflake_str` (đã có sẵn, chuyển vào `cosa_core/snowflake.py` ở Đợt 1) cho bất kỳ bảng/model nào cosa_core sở hữu hoặc tạo mới — không tự ý đổi sang kiểu ID khác.

Lưu ý: các ràng buộc "Business Core không phụ thuộc vendor LLM" trong `CLAUDE.md` §5/§6 không áp dụng cho quyết định DeepSeek ở trên — người dùng đã chủ động quyết định coi DeepSeek Harness là hạ tầng lõi chứ không phải vendor cần cách ly, và có thể sửa/bỏ `CLAUDE.md` nếu nó không còn phản ánh đúng kiến trúc sau khi tách. Quyết định ADK ở trên không mâu thuẫn với nguyên tắc đó: ADK chỉ đảm nhiệm tầng orchestration/routing, còn `DeepSeekHarnessAdapter` vẫn là nơi thực thi thật (execution), và mọi lệnh gọi rủi ro vẫn đi qua `GovernanceKernel`/`ModelGateway` — đúng như proposal đã verify.

Vì một số phần (đặc biệt `auth` + `control_plane`) có độ liên kết chéo rất cao và rủi ro lớn nếu di chuyển cùng lúc với runtime/governance, kế hoạch chia thực thi thành 2 đợt kế tiếp nhau trong cùng một initiative (không phải "để dành vô thời hạn" — đợt 2 bắt đầu ngay sau khi đợt 1 xanh).

---

## Cấu trúc package mới: `backend/cosa_core/`

```
backend/cosa_core/
├── pyproject.toml            # package riêng, cài dạng editable (pip install -e)
├── README.md                 # public API, quy tắc dependency, sơ đồ
├── __init__.py
├── db/base.py                 # SQLAlchemy Base gốc cho các bảng cosa_core
├── snowflake.py                # FROM backend/core/snowflake.py
├── telemetry.py                 # FROM backend/core/telemetry.py
├── feature_flags.py             # FROM backend/core/feature_flags.py
├── runtime/                    # AgentRuntime abstraction + runtime mặc định
│   ├── base.py, types.py, errors.py, execution_scope.py, json_output.py, manager.py
│   └── adapters/
│       ├── contract.py         # interface adapter (để sau này cắm thêm runtime khác)
│       └── deepseek_harness.py # FROM workforce/agents/runtime/adapters/deepseek_harness.py — runtime MẶC ĐỊNH, đầy đủ implementation, deepseek-harness-sdk là dependency chính thức của cosa_core
├── governance/                  # GovernanceKernel, policy, approval, budget
│   └── kernel.py, policy_engine.py, approval_service.py, models.py, budget.py, stuck_detector.py
├── reliability/                 # ModelGateway
│   └── gateway.py, model_profiles.py, patterns.py
├── profiles/                    # Agent Profile Registry
├── capabilities/                # Capability gateway
├── tools/                       # Tool registry + dispatch + invocation engine
│   ├── registry.py (FROM core/tool_registry.py), dispatch.py (FROM core/tool_dispatch.py)
│   ├── invocation/service.py, input_validation.py, output_safety.py, contracts.py
│   └── transports/mcp_adapter.py
├── identity/                    # WorkforceMember — định danh thống nhất người + AI
│   └── models.py (FROM platform_core/organization/models.py), service.py
├── models.py                     # AgentDefinition (FROM workforce/models.py)
├── delegation/                  # TaskBoard, provider manager (ĐỢT 2)
├── orchestration/                # ADK LÀ orchestrator sản xuất chính thức (ĐỢT 2, move nguyên trạng, không build mới)
│   ├── service.py                # FROM workforce/agents/orchestration/service.py — seam mỏng (orchestrate_mission/confirm_mission/resume_mission), không import google.adk trực tiếp ở phía gọi
│   ├── mission_resume_models.py, mission_resume_service.py, runtime_session_models.py, mission_control_bus.py, result.py  # FROM workforce/agents/orchestration/*
│   └── adk/                      # FROM workforce/agents/orchestration/adk/* — nguyên trạng: workflow.py, model_adapter.py, session_bridge.py, session_service_factory.py, governed_tool.py, specialist_delegation.py, nodes/{create_mission,build_company_context,risk_classification,planning,specialist_delegation,approval_gate,execution,quality_gate,synthesis}_node.py
├── workflows/                    # Engine workflow generic (ĐỢT 2, xác minh trước khi move)
├── extensions/                   # MCP connector registry (ĐỢT 2)
├── auth/                         # User/Workspace/WorkspaceMember (ĐỢT 2)
└── control_plane/                # multi-tenancy routing, session (ĐỢT 2)
```

**KHÔNG di chuyển** (ở lại app, nghiệp vụ đặc thù javis-saas):
`business_core/*`, `platform_core/license/*`, `platform_core/policy_funding/*`, `platform_core/tech_radar/*`, `platform_core/reports/*`, phần `entitlement_manager/entitlement_crypto` trong `platform_core/sync/*` (bản thân pattern outbox thì generic, tách phần model outbox nếu cần ở đợt sau).

Cũng ở lại app (đã verify code thật, không phải suy đoán): `workforce/agents/orchestration/router.py` (FastAPI `APIRouter`, import `core.auth.get_current_workspace_member` + `db.session.get_db` — dây nối API/app-layer, không phải logic core) — router này gọi vào `cosa_core.orchestration.service` sau khi move, không tự nó move.

---

## Các quyết định về ranh giới (điểm mơ hồ)

1. **DeepSeek adapter**: `deepseek_harness.py` + `deepseek-harness-sdk` chuyển thẳng vào `cosa_core` làm runtime **mặc định**, không phải chỉ interface. Đây là quyết định chủ động của người dùng — coi DeepSeek Harness là engine thực thi agent (hạ tầng lõi của nền tảng), không phải "vendor LLM" cần cách ly khỏi core.
2. **Google ADK orchestration**: ADK là orchestrator sản xuất chính thức của `cosa_core`, move nguyên trạng `orchestration/adk/*` + `service.py` (seam) + các model phụ trợ. Có 1 điểm coupling cần xác minh trước khi move: `service.py` và `continuation.py` hiện import `founder_os.outcomes.models.{Outcome, OutcomeRun}` — đây là model theo dõi mục tiêu (OKR-adjacent), nhiều khả năng là khái niệm nghiệp vụ javis-saas chứ không phải khái niệm core tổng quát. Cần xác minh: nếu `Outcome/OutcomeRun` là khái niệm chung của bất kỳ hệ agent nào (kết quả một mission cần đạt) thì đưa cả vào core; nếu là khái niệm nghiệp vụ founder-specific thì giữ ở app và inject vào seam qua tham số/callback thay vì import cứng. `router.py` (FastAPI layer) và có thể `continuation.py` ở lại app nếu phụ thuộc business, gọi vào `cosa_core.orchestration.service` qua seam.
3. **Vault/embedding**: `embedding_service.py` hiện gọi thẳng OpenAI — vi phạm CLAUDE.md §5. Trước khi/khi move vault vào core, cần thêm interface `EmbeddingProvider` (~50 dòng), implementation OpenAI cụ thể ở lại app. Vault xếp vào đợt 2 vì phụ thuộc `ModelGateway` (đợt 1) đã sẵn sàng trước.
4. **`platform_core/license/*`**: ở lại app hoàn toàn — đây là nghiệp vụ phân rã công việc theo chức năng (LEGAL/SALES/FINANCE...) đặc thù javis-saas, không phải pattern tổng quát.

## Quy tắc dependency & cách kiểm soát

Một chiều: `app → cosa_core` (được phép), **cấm** `cosa_core → app/workforce/platform_core/business_core`.

Kiểm soát nhẹ, phù hợp team nhỏ — thêm CI check dạng grep:
```bash
rg "^from (app|workforce|platform_core|business_core)" backend/cosa_core --glob "*.py" && exit 1 || exit 0
```
cộng với `python -c "import cosa_core"` để bắt lỗi import cycle sớm.

## Thứ tự thực thi (an toàn, tăng dần rủi ro)

**Đợt 1 — nền tảng + runtime + governance + identity + tools** (rủi ro thấp→trung bình):
1. Utility thuần: `snowflake.py`, `telemetry.py`, `feature_flags.py` + khởi tạo `pyproject.toml`, `db/base.py`
2. Runtime: `runtime/{base,types,errors,execution_scope,json_output,manager}.py` + `adapters/{contract.py, deepseek_harness.py}` — thêm `deepseek-harness-sdk` vào `cosa_core/pyproject.toml` làm dependency chính thức (KHÔNG move `scope_resolver.py` — nó import `business_core`, để lại app, xem rủi ro)
3. Tools + Governance: `core/tool_registry.py`, `core/tool_dispatch.py`, `workforce/tools/invocation/*`, `workforce/tools/transports/mcp_adapter.py`, `workforce/agents/governance/{kernel,policy_engine,approval_service,models,budget,stuck_detector}.py`
4. Identity: `workforce/models.py` (AgentDefinition), `platform_core/organization/models.py` + `service.py` (WorkforceMember/WorkforceRelation)
5. Reliability/Profiles/Capabilities: `workforce/agents/{reliability,profiles,capabilities}/*`

**Đợt 2 — auth/control_plane + delegation/orchestration + workflows/extensions + vault** (rủi ro trung bình→cao, bắt đầu ngay sau khi Đợt 1 xanh, không phải "để sau vô thời hạn"):
6. Auth + control_plane (`platform_core/auth/*`, `platform_core/control_plane/*`) — độ liên kết cao nhất, cần review kỹ interface trước khi move
7. Delegation + Orchestration: `workforce/agents/delegation/{models,task_board,manager,provider,...}.py` (lưu ý: file thực tế là `task_board.py`, không phải `task_board_service.py`); move nguyên trạng `orchestration/{service.py, mission_resume_models.py, mission_resume_service.py, runtime_session_models.py, mission_control_bus.py, result.py, adk/*}.py` sang `cosa_core/orchestration/` — trước tiên xác minh boundary `founder_os.outcomes` (xem mục quyết định #2), sau đó move; port kèm test governance-bypass-guard hiện có sang test suite của `cosa_core`; `router.py` ở lại app, sửa import trỏ sang `cosa_core.orchestration.service`
8. Workflows (`integrations/workflows/*`) + Extensions (`workforce/extensions/*`) — xác minh mức phụ thuộc `business_core` trước khi move
9. Vault (`platform_core/vault/*`) sau khi có `EmbeddingProvider` interface

## Việc cần xác minh trước khi move orchestration (không phải build mới)

- Đọc kỹ `service.py`, `continuation.py`, `mission_resume_service.py` để liệt kê toàn bộ import từ `founder_os.*` — quyết định từng trường hợp: đưa `Outcome/OutcomeRun` vào core (nếu là khái niệm mission-result tổng quát) hay giữ app-side + inject qua callback.
- `google-adk==2.7.0` phải được thêm vào `cosa_core/pyproject.toml` làm dependency chính thức (song song với `deepseek-harness-sdk`) — cả hai đều là runtime mặc định của core theo quyết định của người dùng, không phải optional extras.
- Xác định lại vị trí test governance-bypass-guard hiện có (theo proposal, đây là rào chắn bắt buộc chống lần thất bại tích hợp ADK trước) và đảm bảo nó chạy trong `cosa_core` sau khi move, không bị rơi mất.
- Mọi model mới phát sinh trong quá trình move (nếu cần) dùng `generate_snowflake_id`/`generate_snowflake_str`, không dùng UUIDv7.

## Rủi ro cụ thể cần theo dõi

- **DeepSeek SDK + google-adk SDK trở thành dependency bắt buộc của `cosa_core`**: ai dùng lại core cho hệ thống khác cũng phải cài cả hai — chấp nhận được vì đây là 2 runtime/orchestrator mặc định có chủ đích, nhưng cần ghi rõ trong `README.md`.
- **`founder_os.outcomes` coupling trong orchestration**: nếu không tách rõ, việc move orchestration sẽ kéo theo cả khái niệm nghiệp vụ founder-specific vào core, phá vỡ ranh giới "core không phụ thuộc business" — đây là rủi ro cụ thể nhất của bước 7, cần xử lý trước khi move chứ không phải sau.
- **Mất test governance-bypass-guard khi move**: đây chính là nguyên nhân cụ thể khiến lần tích hợp ADK đầu tiên thất bại (nhìn an toàn trên giấy nhưng bỏ qua GovernanceKernel) — bắt buộc port theo, không coi là "chi tiết phụ" có thể bỏ qua để tiết kiệm thời gian.
- **Circular import**: `scope_resolver.py` import `business_core` → giữ lại app ở đợt 1, refactor thành injectable param ở đợt 2.
- **FK xuyên schema DB**: `WorkforceMember` (control_plane schema) tham chiếu `AgentDefinition` (agent_runtime schema) — đây là kiến trúc đã tồn tại, chỉ di chuyển code không đổi schema; cần test join xuyên schema sau khi move.
- **Alembic**: giữ nguyên `backend/alembic/` và `backend/alembic_control_plane/` làm nguồn migration trong Đợt 1–2; không tạo Alembic env mới cho cosa_core ở giai đoạn này (tránh mở rộng phạm vi ngoài "move").
- **docker-compose / packaging**: cần `pip install -e backend/cosa_core` trong Dockerfile backend; kiểm tra build không xung đột dependency.

## Tiêu chí hoàn thành Đợt 1

- `backend/cosa_core/` tồn tại, cài được qua `pip install -e`, `python -c "import cosa_core"` chạy được
- CI grep-check chặn import ngược (`app/workforce/platform_core/business_core`) trong `cosa_core/` — 0 match
- Toàn bộ test hiện có (`pytest backend/tests/`) pass không có lỗi mới phát sinh
- Test tool registry, runtime manager (mock adapter), governance kernel (policy evaluation) pass
- Test FK xuyên schema `WorkforceMember` ↔ `AgentDefinition` pass
- `docker build` backend thành công với package mới cài dạng editable
- `cosa_core/README.md` mô tả public API + quy tắc dependency (bao gồm ghi rõ DeepSeek Harness SDK và google-adk SDK là dependency chính thức, không phải optional); tài liệu ngắn ghi lại cái gì đã move, cái gì chưa, vì sao (nối tiếp `COSA_CANONICAL_OWNERSHIP_MAP.md` và `COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md`)

## Xác minh

1. `pip install -e backend/cosa_core && python -c "import cosa_core"` — không lỗi
2. `rg "^from (app|workforce|platform_core|business_core)" backend/cosa_core` — không có kết quả
3. `pytest backend/tests/ -v` — không có test nào fail mới so với trước khi tách
4. Test riêng cho FK WorkforceMember ↔ AgentDefinition (join query thực tế)
5. `docker compose build backend` (hoặc tương đương trong `docker-compose.yml` hiện tại) — build thành công
