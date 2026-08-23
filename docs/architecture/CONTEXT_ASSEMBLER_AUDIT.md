# Audit Báo Cáo: Context Assembler Prior Art (`legacy/agent_runtime/workforce/agents/context/`)

> **Mục đích:** Thực hiện yêu cầu bắt buộc của Phase 0 trong `docs/architecture/roadmap/hermes-langgraph-integration/phase-00-inventory-salvage.md` và `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3.  
> **Nguyên tắc:** Audit toàn diện 4 file context prior art trong legacy trước khi thiết kế/triển khai bất kỳ module context nào trong `packages/agent_core/` hoặc `apps/cosa/`.

---

## 1. Tổng quan kiểm tra 4 file mã nguồn Legacy

Các file được phân tích trực tiếp tại `legacy/agent_runtime/workforce/agents/context/`:
1. `assembler.py` (286 dòng) — `CofounderContextAssembler`
2. `builder.py` (151 dòng) — `ContextSection`, `AgentContext`, `_check_governance`, `_safe_fetch_section`, `build_agent_context`
3. `compiler.py` (132 dòng) — `ProgressiveContextCompiler`, `ContextBudget`, `CompiledContext`
4. `scope_resolver.py` (80 dòng) — `ScopeResolver`, `ScopeSet`

---

## 2. Phân tích chi tiết từng file

### 2.1. `assembler.py` (`CofounderContextAssembler`)
- **Ý tưởng cốt lõi:**
  - Định nghĩa Minimum Viable Context theo `intent`:
    - `GREETING`: Trả về `{}` rỗng.
    - `GENERAL_CHAT` và fallback: Chỉ load `workspace` và `founder_profile`.
    - `_DOMAIN_INTENTS` (`SALES`, `FINANCE`, `MARKETING`, `LEGAL`): Chỉ load domain business signal tương ứng.
    - `_FULL_CONTEXT_INTENTS` (`FOUNDER_REVIEW`, `FOUNDER_DECISION`, `FOUNDER_COMMAND`, `FOUNDER_REFLECTION`): Load đầy đủ `workspace`, `project`, `stage`, `founder_profile`, `active_12wy`, `pending_decisions`, `business_signals`, `weekly_plan`, `top_blockers`, `pending_approvals`, `evidence`, `recent_outcomes`.
  - Tái sử dụng `SPECIALIST_REGISTRY.fetch_snapshot()` thay vì re-query lại DB lần hai.
  - Graceful degradation: Mỗi field query độc lập trong `try...except`, lỗi trả về giá trị mặc định/rỗng thay vì crash toàn bộ request.
- **Coupling và vi phạm Boundary:**
  - **Vi phạm nghiêm trọng:** Query trực tiếp SQLAlchemy ORM models của tầng nghiệp vụ (`Workspace`, `Project`, `TwelveWeekCycle`, `WeeklyPlan`, `FounderDecision`, `ApprovalRequest`, `EvidenceItem`, `Outcome`) thông qua `db: Session`.
  - Nếu port nguyên xi vào `packages/agent_core/` sẽ phá vỡ quy tắc "Agent Core không phụ thuộc vào business domain models".
  - Nuốt ngoại lệ quá thô (`except Exception: return {}`), không phân biệt "dữ liệu thực sự rỗng" với "lỗi hệ thống/mất kết nối".

### 2.2. `builder.py` (`ContextSection`, `build_agent_context`)
- **Ý tưởng cốt lõi & Invariant đáng giá:**
  - Cấu trúc `ContextSection`: `data`, `source`, `fetched_at`, `status`, `error` giúp bảo toàn xuất xứ (provenance) và độ tươi (freshness) của dữ liệu.
  - **Governance-before-fetch (`_check_governance`):** Đánh giá quyền truy cập thông qua `GovernanceKernel.evaluate_and_audit_tool_call` **TRƯỚC** khi gọi hàm fetch dữ liệu thực tế. Nếu governance từ chối (`not decision.allowed`), lập tức trả về `ContextSection(status="error", error="Governance denied...")` mà không thực thi hàm fetch.
- **Hạn chế:**
  - Hàm `build_agent_context` eager-load cố định 4 sections (sales, finance, okrs, projects) bất kể intent, gây lãng phí context budget.

### 2.3. `compiler.py` (`ProgressiveContextCompiler`, `ContextBudget`)
- **Ý tưởng cốt lõi:**
  - Khái niệm phân tầng Progressive Context (L0 - L5):
    - `L0`: Session & Founder Preferences
    - `L1`: Company / Founder Index
    - `L2`: Project Context (chỉ khi intent liên quan project)
    - `L3`: Domain Context (Marketing, Sales, Finance, Dev)
    - `L4`: Selected Skill Context
    - `L5`: Relevant Artifacts & Evidence Chunks
- **Đánh giá thực tế (KHÔNG production-ready):**
  - `L5_Artifacts` chưa được implement thực tế (chỉ là placeholder).
  - Ước lượng token rất thô sơ: `len(text) // 4`.
  - Xử lý tràn token giả (`truncate_to_budget` chỉ cắt chuỗi thô và gán `is_trimmed=True`), không có thuật toán redistribute/rebalance token giữa các tầng.
  - Đọc trực tiếp từ file markdown ảo thông qua `workspace_manager.read_file()`.

### 2.4. `scope_resolver.py` (`ScopeResolver`, `ScopeSet`)
- **Ý tưởng cốt lõi:**
  - Định nghĩa `ScopeSet` chứa: `workspace_id`, `project_id`, `job_type`, `domain`, `allowed_namespaces`, `token_budget`, `needs_heavy_priming`.
  - Áp dụng nguyên tắc "No Job -> No Heavy Priming".
- **Lưu ý điều kiện thực tế:**
  - Invariant "No Job -> No Heavy Priming" trong code thực tế chỉ áp dụng khi `not gate_decision.needs_job AND not gate_decision.needs_project`. Khi có `needs_project`, hệ thống vẫn bật `needs_heavy_priming=True`.

---

## 3. Bảng tổng kết Salvage Invariants: GIỮ vs BỎ

| Thuộc tính / Khái niệm | Nguồn Legacy | Trạng thái Salvage | Quyết định & Định hướng trong Kiến trúc Mới |
|---|---|---|---|
| **Governance-before-fetch** | `builder.py` | **GIỮ (BẮT BUỘC)** | Kiểm tra quyền truy cập qua Governance Engine TRƯỚC khi fetch từng fragment, không fetch trước rồi mới lọc. |
| **Intent-based Scoping** | `assembler.py` | **GIỮ (Tổng quát hóa)** | Thay thế 5 enum hardcoded của founder bằng `ContextIntent(kind, domain)` framework-neutral trong `packages/agent_core/contracts/context.py`. |
| **Context Section Provenance & Freshness** | `builder.py` | **GIỮ** | Chuẩn hóa thành `ContextFragment` với `source_kind`, `source_ref`, `lifetime` (STABLE, RUN, CURRENT, EPHEMERAL), `freshness`, `provenance`. |
| **ScopeSet & Token Budgeting** | `scope_resolver.py` | **GIỮ** | Giữ shape giới hạn namespace và token budget, tích hợp vào runtime request. |
| **Progressive Disclosure Concept (L0-L5)** | `compiler.py` | **GIỮ Ý TƯỞNG** | Giữ khái niệm phân tầng theo độ ưu tiên, nhưng implement dần theo use case thật từ Phase 7 (L0-L2) đến Phase 9 (L5). |
| **Direct SQLAlchemy ORM Queries** | `assembler.py` | **BỎ HOÀN TOÀN** | Cấm Agent Core truy cập trực tiếp DB nghiệp vụ. Mọi truy xuất context trong `apps/cosa/` phải đi qua RPC client / Service Ports. |
| **Crude Token Estimation (`// 4`) & Fake Trimming** | `compiler.py` | **BỎ** | Thay bằng cơ chế tính token chuẩn xác hoặc tokenizer adapter khi cần thiết ở Phase 9. |
| **Blind Error Swallowing (`except Exception: return {}`)** | `assembler.py` | **BỎ** | Thay bằng observability & error logging phân biệt rõ "không có dữ liệu" vs "lỗi RPC/kết nối". |
| **Eager 4-section loading** | `builder.py` | **BỎ** | Chỉ nạp context đúng theo intent scope. |

---

## 4. Kết luận cho các Phase tiếp theo

1. **Phase 1:** Định nghĩa `ContextFragment` và `ContextSnapshot` trong `packages/agent_core/contracts/context.py` dạng pure contracts (BaseModel/Protocol), không import bất kỳ business domain nào.
2. **Phase 7:** Triển khai `COSAContextAssembler` trong `apps/cosa/composition/context_assembler.py` tuân thủ nghiêm ngặt bảng Invariants trên: gọi qua RPC/Service Client tới `services/company`, kiểm tra governance trước khi nạp từng fragment, gán đúng `lifetime`.
3. **Phase 9:** Hoàn thiện mở rộng L0-L5 và lexical/semantic conversation search khi có use case thực tế.
