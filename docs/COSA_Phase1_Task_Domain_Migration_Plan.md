# BUSINESS CORE MIGRATION: DI CHUYỂN DOMAIN LOGIC VÀO backend/core/

> **Tài liệu tham chiếu chuẩn:**
> - [markdown/Structure.md](file:///Volumes/SSD/javis-saas/markdown/Structure.md) §4, §5, §49, §50
> - Trạng thái: **8/9 domain hoàn thành, verify sạch**
> - Ngày lập: 2026-08-20, cập nhật liên tục cùng ngày

---

## Context

Sau khi đối chiếu `markdown/Structure.md` với codebase, đã xác nhận `backend/core/` hiện chỉ là scaffold rỗng (`base.py` khai báo `BaseDomainEntity`/`IRepository`, không có entity thật nào), trong khi toàn bộ Business Core thật (Company/Project/OKR/Task/CRM/Marketing/Sales/Finance/Legal) nằm ở `backend/app/founder_os/` và `backend/app/business/`. Người dùng muốn hiện thực hoá đúng nghĩa đen kiến trúc §49 của Structure.md: `backend/core/` phải chứa business logic thật, `backend/app/` chỉ nên là tầng API/orchestration mỏng gọi vào đó.

Đây là việc lớn nếu làm một lần (toàn bộ 8 domain, hàng chục nghìn dòng). Theo đúng §50 "Migration Strategy" của Structure.md ("Không rewrite toàn bộ một lần"), bắt đầu với **1 domain thí điểm: Task** — di chuyển vật lý thật (không phải chỉ re-export facade), để xác lập pattern trước khi làm các domain còn lại.

Khảo sát kỹ cho thấy ngay cả Task — domain đơn giản nhất — cũng có ~45 file import trực tiếp `from app.founder_os.tasks.models import Task` (không qua hub `app.db.models`), cộng thêm `app/db/base.py` là hub đăng ký model trung tâm cho Alembic. Sửa cả 45 file cùng lúc là rủi ro không cần thiết. Giải pháp: di chuyển **định nghĩa class thật** sang `backend/core/tasks/`, giữ lại 1 dòng re-export tương thích ngược tại vị trí cũ — vừa đúng nghĩa "logic thật nằm ở core/", vừa không phải sửa 45 file cùng lúc trong 1 lần thay đổi.

## Phạm vi

**Di chuyển:** `Task`, `TaskDependency`, `TaskSchedule` (3 SQLAlchemy model) + `validate_no_dependency_cycle`/`DependencyCycleError` (`cycle_validator.py`).

**Không di chuyển:** `Agent` (lớp thứ 4 trong cùng file `models.py` hiện tại) — đây là entity cấu hình AI agent (`system_prompt`, `provider`, `model`), không phải business domain Task, ở lại `app/founder_os/tasks/models.py`. Router (`router.py`, `agents_router.py`), service tầng ứng dụng (`scheduler_service.py` — cron poller, `task_dispatcher.py` — background poll loop) ở lại `app/founder_os/tasks/` — đây là tầng API/Application per Structure.md §4 (COSA APPLICATION API nằm trên COSA BUSINESS CORE), không phải Core.

## Thay đổi cụ thể

**File mới:**
- `backend/core/tasks/__init__.py` — package init
- `backend/core/tasks/models.py` — định nghĩa thật `Task`, `TaskDependency`, `TaskSchedule` (copy nguyên trạng từ `app/founder_os/tasks/models.py`, giữ nguyên `__tablename__`, cột, `Base` import từ `app.db.base_class` — KHÔNG đổi schema). `IRepository`/`BaseDomainEntity` ở `core/base.py` giữ nguyên, KHÔNG ép Task kế thừa (contract Pydantic/UUID hiện không tương thích SQLAlchemy/snowflake-id; việc hợp nhất 2 contract là việc riêng, không làm trong lần này).
- `backend/core/tasks/cycle_validator.py` — copy nguyên trạng từ `app/founder_os/tasks/cycle_validator.py`, sửa import `TaskDependency` thành nội bộ.

**File sửa:**
- `app/founder_os/tasks/models.py` — xoá phần định nghĩa `Task`/`TaskDependency`/`TaskSchedule`, giữ nguyên `Agent`, thêm re-export tương thích ngược từ `core.tasks.models`.
- `app/founder_os/tasks/cycle_validator.py` — xoá file (đã chuyển hẳn sang core/, chỉ có 1 consumer là test, sửa trực tiếp test đó thay vì để lại shim).
- `app/db/base.py` — hub Alembic trỏ thẳng về nguồn thật (`core.tasks.models`), không qua shim.
- `app/tests/test_p0_task_cycle_validator.py` — import trỏ về `core.tasks.*`.

**Không đổi (nhờ shim + hub hấp thụ blast radius):** `app/founder_os/tasks/router.py`, `scheduler_service.py`, `task_dispatcher.py`, `agents_router.py`, toàn bộ ~45 file production/test còn lại import trực tiếp `app.founder_os.tasks.models`.

## Rủi ro & cách kiểm soát

- **Circular import**: đã trace — `app/db/base.py → core.tasks.models → app.db.base_class` (không quay lại `app.db.base`) — không có vòng lặp.
- **Alembic/schema drift**: không đổi `__tablename__`, cột, `Base` dùng chung — di chuyển file Python thuần, không đổi schema. Verify bằng so sánh `Base.metadata.tables.keys()` trước/sau.
- **Import path `core.*` khi chạy app thật**: đã xác nhận hoạt động qua `test_phase1_core_contracts.py` (41 test pass) dùng cùng cơ chế sys.path.

## Kế hoạch verify

1. Quét cú pháp toàn repo (`ast.parse`) — 0 lỗi.
2. `import app.main`, `import app.db.base` — sạch, không traceback.
3. So sánh `sorted(Base.metadata.tables.keys())` trước/sau — giống hệt nhau.
4. Chạy toàn bộ `pytest app/tests/` — so sánh qua `git stash` với baseline, đảm bảo không regression mới.
5. Chạy riêng test liên quan Task: `test_p0_task_cycle_validator.py`, `test_scheduler_service.py`, `app/tests/company_runtime/*.py`, `test_state_service.py`, `test_dependency_service.py`, `test_checkpoint_resume.py`.
6. `git status` + đọc diff trước khi báo hoàn thành.

## Các domain tiếp theo (Legal → Strategy) — ✅ hoàn thành cùng ngày

Pattern Task ổn, đã lặp lại cho toàn bộ domain còn lại trong danh sách `core/` của Structure.md §49, mỗi domain 1 vòng khảo sát blast-radius + di chuyển + shim riêng:

| Domain | Số class | Ghi chú |
|---|---|---|
| Legal | 2 | `LegalChecklistItem`, `LegalObligation` — toàn bộ file di chuyển. |
| Learning | 1 | `Lesson`. |
| Finance | 14 | `AccountingProfile`, `AccountingFiscalProfile`, ..., `FinanceManagementSnapshot` — toàn bộ file di chuyển. |
| Sales | 6 | `Account`, `Contact`, `SalesLead`, `SalesOpportunity`, `SalesActivity`, `Customer`. Service logic (`sales/domain/*.py`) ở lại `app/` — chỉ model di chuyển. |
| Marketing | 30 | 3 file gốc (`models.py`, `models_validation.py`, `form_models.py`) → 3 file tương ứng trong `core/marketing/`. |
| Strategy | 70 | Domain lớn nhất (Company/Project/OKR/12WY/Portfolio) — **tách thành 17 file logic** thay vì 1 file 1352 dòng: `core/strategy/{canvas,evidence,analysis,decisions,metrics,scorecard,okr,project,templates,capability,stage,initiative,twelve_week_year,methodology,portfolio,founder,next_action}.py`. `core/strategy/models.py` giữ làm aggregator re-export (không xóa) để `app/db/base.py` + shim cũ không cần đổi thêm lần nữa. |
| Startup (validation) | 38 (21 enum + 17 model) | ✅ **Xong** — `app/founder_os/validation/` (644 dòng, 12 importer) tách thành 4 file: `core/validation/{enums,session,evidence_chain,customer_discovery}.py`. `enums.py` giữ chung 21 enum, mỗi file model chỉ import đúng enum nó dùng (đã kiểm bằng grep tự động, không thủ công). |

**Tổng cộng đã di chuyển**: 9/9 domain trong danh sách `core/` của Structure.md §49 hoàn tất — Task, Legal, Learning, Finance, Sales, Marketing, Strategy, Startup/Validation. ~3550 dòng model thật, verify **hash `Base.metadata.tables` (270 bảng) giống hệt nhau tuyệt đối** qua toàn bộ 9 lần migrate — xác nhận 0 thay đổi schema. Full test suite giữ nguyên đúng 24 fail pre-existing (không liên quan tới migration), 0 regression mới trong suốt quá trình. Repo-wide syntax check 0 lỗi, `import app.main` sạch sau mỗi bước.

## Trạng thái cuối: Business Core migration HOÀN TẤT

`backend/core/` giờ chứa toàn bộ 9 domain business thật (company/projects/startup/okr/twelve_week_year/tasks/crm/marketing/sales/finance/legal theo đúng liệt kê §49, "company/projects/okr/12wy" gộp trong `core/strategy/`). `backend/app/{founder_os,business}/*/models.py` chỉ còn shim re-export tương thích ngược — router/service tầng ứng dụng vẫn ở nguyên vị trí theo đúng layering §4.

## Phase 2 (cùng ngày) — Agent Runtime data models + vá gap Marketing — ✅ HOÀN TẤT

**Quyết định kiến trúc quan trọng chốt với người dùng ở Phase 2**: `agent/` → đổi tên **`agent_runtime/`** (Python không cho phép `import agent-runtime`, dùng gạch dưới) — "Engine dùng chung để chạy agent". `agents/` (số nhiều — 12 agent theo phòng ban) **không tạo thư mục riêng** — người dùng xác nhận rõ COSA chỉ có **1 COSA Co-founder duy nhất** làm founder-facing identity (đúng Structure.md §1: agent theo domain chỉ tồn tại ở mức UX/business-role, không phải runtime độc lập). "Đồng bộ agents/" = sửa thẳng `chief_of_staff.py::SPECIALIST_REGISTRY` (composition nội bộ của 1 orchestrator), không tạo agent thứ 4/5/6/7.

**Bước 0 — Đổi tên scaffold**: `backend/agent/` (40 file, 0 caller sản xuất) → `git mv` thành `backend/agent_runtime/`, sửa import trong 8 file `test_phaseN_*.py` + 2 file cross-reference nội bộ scaffold (`tools/dispatcher.py`, `workflows/engine.py`) từ `agent.` → `agent_runtime.`. 41/41 test scaffold pass sau đổi tên.

**Bước 1 — Di chuyển 5 nhóm model thật** (theo đúng pattern Business Core: model thật → `agent_runtime/`, shim tương thích ngược ở vị trí cũ, `app/db/base.py` trỏ thẳng nguồn thật):

| Đích | Nguồn | Class |
|---|---|---|
| `agent_runtime/sessions/models.py` | `workforce/agents/governance/models.py` | `AgentRun` |
| `agent_runtime/events/models.py` | `workforce/agents/governance/models.py` | `AgentEventRecord` |
| `agent_runtime/permissions/models.py` | `workforce/agents/governance/models.py` | `AgentToolCall`, `AgentApproval` |
| `agent_runtime/sandbox/models.py` (thư mục mới) | `workforce/agents/execution/models.py` | `ExecutionJob`, `ExecutionStep`, `SandboxPolicyRecord` |
| `agent_runtime/memory/models.py` (thư mục mới) | `workforce/memory/models.py` | 8 class (`AgentMemoryEngine`...`AgentMemoryEntry`) |

`sessions/`, `events/`, `permissions/` đã có sẵn `base.py` (contract Pydantic trừu tượng từ scaffold cũ) — model thật thêm vào không xung đột tên, `__init__.py` cập nhật export cả 2.

**Bước 2 — Vá gap Marketing trong SPECIALIST_REGISTRY**: tạo `app/business/marketing/marketing_tools.py::get_marketing_overview` (đăng ký `@register(namespace="marketing", ...)`, tái dùng `MarketingDataCapability.read_marketing_overview` đã có sẵn/có caller thật), thêm vào `tool_bootstrap.py`, thêm entry `"marketing"` vào `SPECIALIST_REGISTRY` theo đúng mẫu sales/finance/legal. **Không** thêm vào `DEFAULT_ORCHESTRATION_DOMAINS` (giữ nguyên `("sales", "finance")`) — marketing trở thành specialist khả dụng như "legal" (đăng ký nhưng không tự động trigger mặc định), không đổi hành vi mặc định của orchestrator.

**Verify Phase 2**: hash `Base.metadata.tables` (270 bảng) giống hệt trước/sau, repo-wide syntax 0 lỗi, `app.main` sạch, full test suite đúng 24 fail pre-existing + 0 regression, test mới `test_marketing_specialist_registered_and_tool_resolves` pass (xác nhận `SPECIALIST_REGISTRY["marketing"]` tồn tại và `tool_flat_name` resolve được qua `get_tool_by_flat_name`).

## Việc còn lại, không thuộc phạm vi 2 phiên này
- `agent_runtime/{runtime,orchestrator,routing,context,models}/` (business logic thật: Model Router, Intent Router, Context Engine...) — đang có 2 stack Orchestrator song song + 3-4 stack Governance trùng lặp trong `app/workforce/`, cần hợp nhất TRƯỚC khi di chuyển. Việc lớn, rủi ro cao, để riêng.
- Hợp nhất `core/base.py` (`BaseDomainEntity`/`IRepository`, Pydantic/UUID) với các model SQLAlchemy/snowflake-id thật — chưa domain nào ép kế thừa.
- Governance/Orchestrator consolidation (3-4 bản trùng lặp), sandbox hoá Claude Code path (`desktop_worker/main.py` không sandbox) — đã ghi nhận từ các đợt phân tích trước, chưa xử lý.

**Trade-off kỹ thuật đã chấp nhận**: mọi `core/*/models.py` vẫn `from app.db.base_class import Base` (dùng chung 1 SQLAlchemy declarative Base + Alembic registry) — `core/` phụ thuộc ngược 1 phần hạ tầng `app/db/`. Chấp nhận vì đây là persistence primitive hẹp, không phải business logic; việc di dời hẳn `app/db/base_class.py`/session/engine xuống `core/` là việc lớn hơn, để sau nếu cần.

**Việc hợp nhất domain thật với contract `BaseDomainEntity`/`IRepository`** (`core/base.py`, Pydantic/UUID) vẫn để riêng — chưa có domain nào ép kế thừa, vì contract hiện không tương thích SQLAlchemy/snowflake-id dùng xuyên suốt hệ thống.
