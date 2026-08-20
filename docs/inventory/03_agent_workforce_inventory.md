# BÁO CÁO KIỂM KÊ AI WORKFORCE, TOOLS, PROMPTS & WORKFLOWS
## (PHASE 0 - INVENTORY REPORT 03)

> **Dự án:** COSA (Founder / Company Operating System)  
> **Ngày thực hiện:** 2026-08-20  
> **Trạng thái:** Hoàn tất khảo sát

---

## 1. KIỂM KÊ DANH SÁCH AGENT PROFILES HIỆN TẠI (12 ROLES)

Hiện tại, các vai trò Agent đang được tổ chức trong `backend/app/workforce/`:

| Tên Agent Role | Vị trí Profile / Prompt | Skills được gán | Tools được gán | Đánh giá Tái cấu trúc |
| :--- | :--- | :--- | :--- | :--- |
| **Co-founder Orchestrator** | `app/workforce/agents/cofounder/` | Intent routing, Capability selection | Toàn bộ tools | Chuyển thành `agent/orchestrator/` |
| **Marketing (CMO)** | `app/workforce/agents/marketing/` | Market research, ICP, Copywriting | Web search, Analytics, CRM | Chuyển thành `agents/marketing/` (Profile) |
| **Sales (Head of Sales)**| `app/workforce/agents/sales/` | Lead scoring, Outreach | CRM, Email, Outbox | Chuyển thành `agents/sales/` (Profile) |
| **Finance (CFO)** | `app/workforce/agents/finance/` | TT58 Audit, Runway calculation | DB Finance, Calculator | Chuyển thành `agents/finance/` (Profile) |
| **Legal (General Counsel)**| `app/workforce/agents/legal/` | Contract review, Compliance | Filesystem, Knowledge | Chuyển thành `agents/legal/` (Profile) |
| **Research (Head of Research)**| `app/workforce/agents/research/` | Deep research, Trend analysis | Web, Knowledge vector | Chuyển thành `agents/research/` (Profile) |
| **Coding / DevOps** | `app/workforce/agents/developer/`| Scaffolding, Refactoring, Tests | Shell, Filesystem, Claude Code | Chuyển thành `executors/claude_code/` |

---

## 2. KIỂM KÊ TOOLS REGISTRY & RISK LEVELS

| Tool Name | Vị trí Code | Input Schema | Risk Level | Presenter Formatter |
| :--- | :--- | :--- | :--- | :--- |
| `web.search` | `app/workforce/tools/web_search.py` | `{query: str}` | `LOW` | Chưa có (Raw JSON) $\rightarrow$ Cần bổ sung |
| `filesystem.read` | `app/workforce/tools/file_tools.py` | `{path: str}` | `LOW` | Có code diff viewer |
| `filesystem.write`| `app/workforce/tools/file_tools.py` | `{path: str, content: str}` | `MEDIUM` | Cần approval nếu ngoài sandbox |
| `crm.create_lead` | `app/workforce/tools/crm_tools.py` | `LeadCreateDTO` | `MEDIUM` | Cần format thẻ khách hàng |
| `deploy.execute` | `app/workforce/tools/deploy_tools.py` | `{target: str, env: str}` | `HIGH` | Bắt buộc Founder Approval |
| `shell.execute` | `app/workforce/tools/shell_tools.py` | `{command: str}` | `HIGH` | Bắt buộc Sandboxed & Approval |

---

## 3. RÀ SOÁT LỖI GREETING & CONTEXT LOADING (REGRESSION ROOT CAUSE)

* **Hiện tượng:** Khi người dùng gửi lời chào ("chào", "hello", "hi"), hệ thống tự động kích hoạt Agent Session nạp toàn bộ thông tin dự án và quét cơ sở dữ liệu.
* **Nguyên nhân cốt lõi:**
  - Entrypoint chat thiếu tầng **Intent Classification độc lập**.
  - Pipeline chat hiện tại tự động inject `project_context` vào system prompt trước khi phân tích ý định của người dùng.
* **Giải pháp khắc phục trong Phase 3:**
  - Tạo `agent/routing/intent_router.py` phân loại trước: nếu `intent == "conversation.greeting"`, lập tức trả về câu chào lịch sự và ngắt luồng, giữ `context = None`.
