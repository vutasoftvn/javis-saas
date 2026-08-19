# COSA CO-FOUNDER ARCHITECTURE — MASTER SPECIFICATION
## TÀI LIỆU ĐẶC TẢ KIẾN TRÚC TOÀN DIỆN (F4 SPEC CONSOLIDATION)

> **Trạng thái:** HOÀN TẤT TRIỂN KHAI & NGHIỆM THU (PHASES 1 — 5)  
> **Phiên bản:** 2.0.0 (COSA OS Autonomous Enterprise)  
> **Đặc tả nguồn:** [markdown/F4.md](file:///Volumes/SSD/javis-saas/markdown/F4.md)

---

## 1. TỔNG QUAN KIẾN TRÚC & NGUYÊN TẮC CỐT LÕI

```text
                                HUMAN FOUNDER
                        (Quyền Ra Quyết Định Tối Cao)
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │      COSA CO-FOUNDER      │
                        │  (CosaCofounderService)   │
                        └─────────────┬─────────────┘
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           ▼                          ▼                          ▼
     [Mission / Task]           [Evidence Query]          [Decision Proposal]
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      ▼
                  ┌───────────────────────────────────────┐
                  │          CORE DOMAIN WORKFORCE        │
                  │  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
                  │  │  Sales  │ │Marketing│ │ Finance │  │
                  │  └─────────┘ └─────────┘ └─────────┘  │
                  │  ┌─────────┐ ┌─────────┐              │
                  │  │  Legal  │ │  Build  │              │
                  │  └─────────┘ └─────────┘              │
                  └───────────────────┬───────────────────┘
                                      │
       ┌──────────────────────────────┴──────────────────────────────┐
       ▼                                                             ▼
[SHARED CAPABILITY]                                         [CROSS-CUTTING POLICY]
  `investigate`                                               `QualityGatePolicy`
(Fact, Web, Docs, Data)                                     (Completeness, Evidence,
       │                                                      Compliance, Actionable)
       ▼                                                             │
[TOOL REGISTRY]                                                      ▼
(CRM, TT58, Sandbox, Policy)                                   [WORK PRODUCT]
```

### 8 Nguyên tắc F4 bất biến:
1. **COSA Co-Founder $\neq$ Domain Agent:** COSA là lớp điều phối, đồng hành, tư duy và tổng hợp nằm trên Workforce.
2. **Founder $\neq$ COSA:** Human Founder là chủ sở hữu và người đưa ra quyết định cuối cùng; COSA hỗ trợ phân tích, đề xuất và phản biện (`Challenge Mode`).
3. **Mission-Centric (`Mission > Agent`):** Founder giao mục tiêu (`Goal`), COSA tự động sinh `Mission` và điều phối đa Domain Agent song song.
4. **5 Core Domain Agents mặc định:** `Sales`, `Marketing`, `Finance`, `Legal`, `Build/Tech`.
5. **Optional Packs Store:** `Operations`, `People/HR`, `Customer Support` (bật/tắt linh hoạt theo quy mô Workspace).
6. **Xóa bỏ các Agent Anti-Patterns:**
   - *Strategy* $\rightarrow$ Năng lực tư duy trực thuộc Co-Founder (`CosaCofounderService`).
   - *Research* $\rightarrow$ Shared capability `investigate` (`InvestigateService`).
   - *QA/Quality* $\rightarrow$ Cross-cutting `QualityGatePolicy`.
   - *Automation* $\rightarrow$ Tool Registry & Background Triggers (cron, webhook, celery, n8n).
   - *Voice* $\rightarrow$ Giao thức tương tác (Modality).
   - *Domain Taxonomy* $\rightarrow$ Phân loại tri thức, không sinh bot thừa.
7. **Phân định rõ `Decision` vs `Approval`:**
   - `FounderDecision`: Lựa chọn chiến lược kinh doanh của Founder (lưu trữ vào `Decision Memory` kèm Evidence IDs).
   - `ApprovalRequest`: Cổng kiểm soát kỹ thuật và chi phí vận hành.
8. **Founder Command Center (Flutter UI):**
   - Co-Founder Card + Company Pulse.
   - Top 3 Focus theo 12 Week Year.
   - Hàng đợi `Waiting for You` (Strategic Decisions + Approvals).
   - Tab phụ `AI Workforce & Packs Store`.

---

## 2. CHI TIẾT TẦNG BACKEND (PYTHON / FASTAPI / SQLALCHEMY)

### 2.1. Tầng Dữ liệu & Models ([models.py](file:///Volumes/SSD/javis-saas/backend/app/workforce/models.py))
- `AgentDefinition.category`: `ORCHESTRATOR` | `DOMAIN` | `OPTIONAL_DOMAIN` | `LEGACY`.
- `AgentDefinition.is_default_active`: `bool`.
- `FounderDecision`: Quản lý câu hỏi, bối cảnh, các options, AI recommendation, evidence IDs, trạng thái (`PENDING`, `DECIDED`, `DISMISSED`, `DEFERRED`), lựa chọn và ghi chú của Founder.
- `AgentAlias`: Bảng migration mềm giải quyết alias cũ.

### 2.2. Co-Founder Service ([cosa_cofounder_service.py](file:///Volumes/SSD/javis-saas/backend/app/workforce/orchestrator/cosa_cofounder_service.py))
- **`handle_founder_message()`:** Nhận diện và xử lý intent.
- **`get_company_pulse()`:** Tổng hợp số liệu nhịp tim doanh nghiệp (Goals on track, Active missions, Quyết định tồn đọng, Rủi ro).
- **`get_next_best_action()`:** Gợi ý Top 3 hành động tốt nhất trong ngày gắn với 12 Week Year.
- **`challenge_assumptions()` (Challenge Mode):** Đối chiếu giả định với Evidence Engine (F1/F2/F3) để ngăn ngừa Solution Bias.
- **`synthesize_cross_domain()`:** Tổng hợp đa chiều Marketing ROI + Finance Cashflow Runway + Pháp lý.

### 2.3. Shared Capability & Quality Gate
- **`InvestigateService` ([investigate_service.py](file:///Volumes/SSD/javis-saas/backend/app/workforce/capabilities/investigate_service.py)):** Tra cứu Web, Vector Docs, Sổ cái TT58, Lead CRM và trả về Evidence Items chuẩn.
- **`QualityGatePolicy` ([quality_gate_policy.py](file:///Volumes/SSD/javis-saas/backend/app/workforce/governance/quality_gate_policy.py)):** Chấm điểm tự động 4 trụ cột (*Completeness*, *Evidence-backed*, *Policy compliance*, *Actionability*).

### 2.4. REST APIs
- `POST /api/v1/cofounder/chat`
- `GET /api/v1/cofounder/pulse`
- `GET /api/v1/cofounder/top3`
- `POST /api/v1/cofounder/challenge`
- `GET/POST /api/v1/cofounder/decisions` & `POST /api/v1/cofounder/decisions/{id}/resolve`
- `GET /api/v1/workforce/packs` & `POST /api/v1/workforce/packs/{pack_key}/toggle`

---

## 3. CHI TIẾT TẦNG FRONTEND FLUTTER (FOUNDER COMMAND CENTER)

### 3.1. Data Layer & Services
- **Models:** [founder_decision_model.dart](file:///Volumes/SSD/javis-saas/frontend/lib/data/models/founder_decision_model.dart), [company_pulse_model.dart](file:///Volumes/SSD/javis-saas/frontend/lib/data/models/company_pulse_model.dart), [workforce_pack_model.dart](file:///Volumes/SSD/javis-saas/frontend/lib/data/models/workforce_pack_model.dart).
- **API Service:** [cofounder_api_service.dart](file:///Volumes/SSD/javis-saas/frontend/lib/data/services/cofounder_api_service.dart).

### 3.2. State Management & Controllers
- **[founder_command_center_controller.dart](file:///Volumes/SSD/javis-saas/frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart):** Quản lý Reactive State của Pulse, Top 3 Focus, Waiting for You Queue, Active Missions, Chốt quyết định và Chat Co-Founder.

### 3.3. Views & Widgets
- **[cofounder_card_widget.dart](file:///Volumes/SSD/javis-saas/frontend/lib/modules/hologram_hub/widgets/cofounder_card_widget.dart):** Thẻ Co-Founder AI Hero & Pulse Counters.
- **[top3_focus_widget.dart](file:///Volumes/SSD/javis-saas/frontend/lib/modules/hologram_hub/widgets/top3_focus_widget.dart):** Top 3 hành động 12WY.
- **[waiting_for_you_widget.dart](file:///Volumes/SSD/javis-saas/frontend/lib/modules/hologram_hub/widgets/waiting_for_you_widget.dart):** Hàng đợi Decisions + Approvals.
- **[decision_modal_sheet.dart](file:///Volumes/SSD/javis-saas/frontend/lib/modules/hologram_hub/widgets/decision_modal_sheet.dart):** BottomSheet phân tích đa miền và lựa chọn phương án chốt.
- **[ai_workforce_tab.dart](file:///Volumes/SSD/javis-saas/frontend/lib/modules/hologram_hub/widgets/ai_workforce_tab.dart):** Quản lý 5 Core Domains & Optional Packs Store.
- **[hologram_hub_view.dart](file:///Volumes/SSD/javis-saas/frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart):** Giao diện Founder Command Center hoàn chỉnh kèm Drawer Chat.

---

## 4. BẢNG TỔNG KẾT KẾT QUẢ KIỂM THỬ (TEST VERIFICATION MATRIX)

| Phase | Phạm vi nghiệm thu | Test Suite | Kết quả |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Database Schema, Decision Entity & Alias Resolver | `test_phase1_cofounder_schema.py` | ✅ 4/4 PASS |
| **Phase 2** | Co-Founder Engine, Intent Router & Challenge Mode | `test_phase2_cofounder_engine.py` | ✅ 5/5 PASS |
| **Phase 3** | 5 Core Domains, Shared Capability & Quality Gate | `test_phase3_domain_workforce.py` | ✅ 4/4 PASS |
| **Phase 4** | Frontend Flutter Models, Controller, Widgets & View | `flutter analyze` | ✅ 0 Errors |
| **Phase 5** | End-to-End Complete Founder Workflow | `test_phase5_cofounder_e2e.py` | ✅ 1/1 PASS |
| **Hệ thống**| Toàn bộ Agent Platform & Workforce Backend | `app/tests/agent_platform/`, `app/tests/workforce/` | ✅ **87/87 PASS** (0 warnings) |
