# BÁO CÁO KIỂM KÊ API ENDPOINTS & ROUTERS BACKEND
## (PHASE 0 - INVENTORY REPORT 01)

> **Dự án:** COSA (Founder / Company Operating System)  
> **Ngày thực hiện:** 2026-08-20  
> **Trạng thái:** Hoàn tất khảo sát

---

## 1. TỔNG QUAN HỆ THỐNG ROUTERS

Backend hiện tại được tổ chức thành **5 Domain Master Routers** nạp vào `backend/app/main.py` cùng `capabilities_router`:

| Domain Router | File Router chính | Tiền tố Router | Số lượng Sub-Routers |
| :--- | :--- | :--- | :--- |
| **1. Founder OS** | `app/founder_os/router.py` | `/api/v1/` | 10 routers (tasks, agents, strategy, okrs, execution, portfolios, next-actions, outcomes, workspace, validation) |
| **2. Business Domain** | `app/business/router.py` | `/api/v1/` | 9 routers (business/packs, marketing, public marketing, sales, revenue, public-leads, finance, tt58, legal, learning) |
| **3. AI Workforce** | `app/workforce/router.py` | `/api/v1/` | 11 routers (chat, ai, agent-memory, skills, functions/ai-team, automations, agent-platform, workforce-admin, runtime, ai-programs, cofounder) |
| **4. Integrations** | `app/integrations/router.py` | `/api/v1/` | 10 routers (channels, connectors, zalo, google, email-approvals, email-webhooks, plugins, outbox, realtime, devices, workflows) |
| **5. Platform** | `app/platform/router.py` | `/api/v1/` | 15 routers (auth, vault, sync, brains, company-runtime, admin, feature-flags, prompts, domain, events, founder-hub, missions, organization, tech-radar, policy-funding) |
| **Capabilities Registry**| `app/workforce/agents/capabilities/router.py` | `/api/v1/capabilities` | 1 router độc lập (check, grants, catalog) |

---

## 2. MA TRẬN CHI TIẾT CÁC ENDPOINT VÀ ĐÁNH GIÁ MỨC ĐỘ COUPLING

### 2.1. Domain Founder OS
| Method | Endpoint Path | Chức năng nghiệp vụ | Request/Response DTO | Đánh giá Tầng (Clean / Coupled) |
| :--- | :--- | :--- | :--- | :--- |
| `GET/POST` | `/api/v1/tasks/` | Quản lý tác vụ vận hành | `TaskCreate`, `TaskResponse` | Clean: Qua `TaskService` & DB Session |
| `GET/POST` | `/api/v1/strategy/` | Quản lý chiến lược & Định vị | `StrategyCanvasDTO` | Clean: Strategy Service |
| `GET/POST` | `/api/v1/okrs/` | Quản trị OKRs quý & 12WY | `OKRCreateDTO`, `OKRResponse` | Clean: OKR Service |
| `POST` | `/api/v1/execution/` | Bảng thực thi Tactics tuần | `WeeklyTacticDTO` | Clean: Execution Service |
| `GET/POST` | `/api/v1/outcomes/` | Đo lường kết quả & Bằng chứng | `OutcomeDTO` | Clean: Outcome Service |
| `GET/POST` | `/api/v1/workspace/` | Quản lý Project Workspace | `WorkspaceDTO` | Clean: Workspace Service |
| `POST` | `/api/v1/validation/`| Thẩm định giả thuyết PMF | `HypothesisDTO` | Coupled: Gọi sang một số Agent runner |

### 2.2. Domain Business
| Method | Endpoint Path | Chức năng nghiệp vụ | Request/Response DTO | Đánh giá Tầng (Clean / Coupled) |
| :--- | :--- | :--- | :--- | :--- |
| `GET/POST` | `/api/v1/marketing/` | Chiến dịch & ICP Positioning | `CampaignDTO`, `ICPDTO` | Coupled: Import trực tiếp marketing prompts |
| `POST` | `/api/v1/sales/leads`| Quản lý Leads & Opportunities | `LeadDTO` | Clean: CRM Repository |
| `GET/POST` | `/api/v1/finance/tt58`| Kế toán quản trị TT58 VN | `TT58RecordDTO`, `BalanceDTO` | Clean: Pure Python accounting logic |
| `GET/POST` | `/api/v1/legal/` | Hợp đồng & Rà soát pháp lý | `ContractDTO` | Coupled: Trộn lẫn prompt review và entity |
| `GET/POST` | `/api/v1/business/packs`| Tri thức ngành đóng gói | `BusinessPackDTO` | Clean: YAML loader |

### 2.3. Domain AI Workforce
| Method | Endpoint Path | Chức năng nghiệp vụ | Request/Response DTO | Đánh giá Tầng (Clean / Coupled) |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/chat/message` | Gửi tin nhắn Agent | `ChatMessageRequest` | ⚠️ **Cần Refactor:** Chưa có Intent Router chặn greeting |
| `GET/POST` | `/api/v1/skills/` | Quản lý danh mục Skills | `SkillDefinitionDTO` | Clean: Skills Registry |
| `GET` | `/api/v1/runtime/health`| Chẩn đoán Runtime Engine | `RuntimeStatusDTO` | Clean |
| `GET` | `/api/v1/capabilities/catalog` | Catalog năng lực khả thi | `CapabilityCatalogDTO` | Clean: Seeded registry |

---

## 3. CÁC ĐIỂM NGHẼN CẦN CHUẨN HÓA TRONG GIAI ĐOẠN 1
1. **Thiếu Envelope chuẩn thống nhất:** Một số router trả về raw dict `{...}`, một số trả về Pydantic Model. Cần chuẩn hóa toàn bộ về `APIResponse[T]` với `success`, `data`, `error`, `metadata`.
2. **Loại bỏ Router lặp tiền tố (Duplicate Routes):** Hiện có một số router mount 2 lần (ví dụ `/api/v1/founder-hub` và `/api/v1`), cần dọn dẹp để router nhất quán.
