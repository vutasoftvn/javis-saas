# BÁO CÁO HIỆN TRẠNG KIẾN TRÚC: COSA BUSINESS KNOWLEDGE PACK
## (BUSINESS_PACK_CURRENT_STATE.md)

**Ngày thực hiện:** 2026-08-18  
**Tài liệu tham chiếu:** [E1-COSA_Business_Knowledge_Pack_Integration_Spec.md](file:///Volumes/SSD/javis-saas/markdown/E1-COSA_Business_Knowledge_Pack_Integration_Spec.md)  
**Tiêu chí đánh giá:** `EXISTS` (Đã có đầy đủ), `PARTIAL` (Có một phần, cần mở rộng), `MISSING` (Chưa có), `CONFLICT` (Có mâu thuẫn cần điều chỉnh).

---

## 1. Bảng Đánh giá Tổng thể Thành phần (Architecture Components Matrix)

| Thành phần (Component) | Trạng thái | Vị trí hiện tại trong Codebase | Đánh giá chi tiết & Đề xuất điều chỉnh |
| :--- | :---: | :--- | :--- |
| **1. Skill Registry & Loader** | `PARTIAL` | `backend/app/workforce/skills/` (`skill_loader.py`, `models.py`) | Đã có `PhysicalSkillDocument` đọc `SKILL.md` (YAML frontmatter + Markdown body) và `SkillRegistryItem`. **Cần bổ sung:** Cấu trúc pack phân tầng (`factory/` vs `company/`), nạp dynamic theo `pack.yaml`. |
| **2. Prompt Storage & Versioning** | `EXISTS` | `backend/app/workforce/prompts/`, `models.py` (`PlatformPromptTemplate`) | Đã có hệ thống lưu prompt theo domain, hỗ trợ versioning và rollback. |
| **3. Local File Structure & Pack Directory** | `MISSING` | Chưa có thư mục chuẩn `packs/` | Hiện tại skills và prompts lưu rải rác trong `workforce/`. **Cần tạo:** `backend/app/business/packs/factory/` và `company/` chứa `capabilities/`, `sops/`, `templates/`, `references/`, `legal/`. |
| **4. Company-level Local Data & Tenant Isolation** | `PARTIAL` | `workspaces.id` trong PostgreSQL & `SnowflakeIDMixin` | Đã có phân lập workspace ID trên DB. **Cần bổ sung:** Storage folder cho Company overrides và local file isolation. |
| **5. Living Artifact & Work Product** | `PARTIAL` | `backend/app/workforce/work_product/`, `models.py` (`WorkProduct`) | Đã có `WorkProduct`, `DecisionRecord`, `WorkProductTransformer`. **Cần mở rộng:** Thêm metadata liên kết `factory_template_id`, `template_version`, `legal_sources`, `document_type` (POL, SOP, FRM, RPT, MAN). |
| **6. Admin Permissions & Governance** | `EXISTS` | `backend/app/workforce/governance/` (`permission_engine.py`, `risk_evaluator.py`) | Đã có `UnifiedPermissionEngine`, `RiskPolicyEvaluator` (LOW, HIGH, CRITICAL), `ApprovalRequest` cho Founder/Lead. Phù hợp nguyên tắc chỉ Admin mới được override/reset. |
| **7. Factory Reset Mechanism** | `PARTIAL` | `PlatformPromptTemplate.default_content`, `ToolDefinition.default_config_jsonb` | Đã có cơ chế khôi phục mặc định cho Prompt & Tool. **Cần bổ sung:** `reset_to_factory()` cho Pack Assets (SOP, Template, Capability). |
| **8. Legal Knowledge Subsystem** | `PARTIAL` | `backend/app/business/legal/` (`models.py`, `legal_review_service.py`) | Đã có checklist và obligations. **MISSING:** Entity `LegalSource` (văn bản bất biến có version, status, ngày hiệu lực), `LegalAnnotation` (ghi chú doanh nghiệp), và `LegalResolver`. |
| **9. Update / Versioning Mechanism** | `PARTIAL` | `backend/app/workforce/skills/versioning.py`, `PlatformToolVersion` | Đã có tracking version cho tool/prompt. **Cần bổ sung:** `UpdateManifest` schema, local sha256 comparator và conflict resolver (`KEEP_COMPANY`, `ACCEPT_FACTORY`, `MERGE`, `RESET`). |
| **10. Marketing Domain Integration** | `EXISTS` | `backend/app/business/marketing/` | Đã có form engine, lead capture, marketing services. Sẽ gắn Template/SOP vào module hiện hữu, không tạo hệ thống marketing thứ 2. |
| **11. Finance & Accounting Integration** | `EXISTS` | `backend/app/business/finance/` (`tt58_engine.py`, `finance_tools.py`) | Đã có kế toán TT58, sổ cái, phân tích chi phí. Sẽ cung cấp template Cashflow Forecast và P&L chuẩn kết nối vào engine. |
| **12. CRM & Sales Integration** | `EXISTS` | `backend/app/business/sales/` (`revenue_engine_service.py`, `sales_tools.py`) | Đã có CRM DB làm System of Record. Không biến template thành nơi lưu lead/deal. |
| **13. Hologram Hub / Strategy Integration** | `EXISTS` | `backend/app/founder_os/strategy/`, `outcomes/` | Đã có Strategy Canvas, 12-Week Year cycle, Action Decision Records. Sẽ lấy `decisions` & `issues` từ Weekly Report / SOPs đưa vào Hologram. |

---

## 2. Đánh giá Mức độ Tương thích 12 Business Domains

| Business Domain | Phân loại Triển khai | Trạng thái Codebase | Định hướng Tích hợp Native |
| :--- | :---: | :---: | :--- |
| **1. Governance** | `CORE` (Pilot) | `PARTIAL` | Ưu tiên số 1: NDA, Service Agreement, RACI, Compliance Checklist, Document Approval. |
| **2. Operations** | `CORE` (Pilot) | `PARTIAL` | Ưu tiên số 1: Standard SOP Template, Daily Checklist, Incident Handling SOP, Meeting Minutes. |
| **3. Sales** | `CORE` (Pilot) | `EXISTS` | Ưu tiên số 1: Sales Process SOP, Quotation SOP, Objection Handling; nối trực tiếp vào Sales CRM. |
| **4. Reporting** | `CORE` (Pilot) | `PARTIAL` | Ưu tiên số 1: Weekly Report Template, KPI Dictionary, Monthly Management Report; nạp data cho Hologram. |
| **5. Finance** | `CORE` (Phase 4) | `EXISTS` | Bổ sung Cashflow Forecast, Financial Scenario, Monthly Close SOP tương thích TT58. |
| **6. Marketing** | `CORE` (Phase 4) | `EXISTS` | Tích hợp Content Strategy, SEO SOP, Ads SOP với Marketing module hiện tại. |
| **7. Customer** | `CORE` (Phase 4) | `PARTIAL` | Onboarding SOP, Complaint Handling SOP, CSAT/NPS survey. Tách biệt CRM (data) & Customer (methodology). |
| **8. Product & Technology** | `CORE` (Phase 4) | `PARTIAL` | Product Roadmap, Quality Control SOP, IT Policy, Backup SOP. Giữ nguyên Build Spec native. |
| **9. People** | `OPTIONAL` | `PARTIAL` | Org Chart, JD Template, Onboarding SOP (bật khi có nhân viên, ẩn với founder solo). |
| **10. Training** | `OPTIONAL` | `MISSING` | Training Policy, Needs Assessment, Training Material (bật theo maturity). |
| **11. Growth** | `OPTIONAL` | `PARTIAL` | Pitch Deck, Valuation Model, Cap Table (áp dụng High-Risk policy). |
| **12. Strategy** | `FEATURE-FLAG` | `EXISTS` | Đã có `founder_os/strategy`. Không tự ý bật lại SWOT/PESTEL nếu đang tắt. Tuân thủ feature flag. |

---

## 3. Kết luận & Chiến lược Chuyển tiếp (Migration Strategy)

1. **Không Rewrite:** Tận dụng 100% nền tảng FastAPI + PostgreSQL + SQLAlchemy + SnowflakeID hiện có.
2. **Kế thừa & Mở rộng:**
   - Mở rộng `WorkProduct` để đáp ứng chuẩn **Living Artifact**.
   - Mở rộng `PhysicalSkillDocument` & `DynamicSkillLoader` để nạp từ Business Pack `factory/` và `company/`.
   - Bổ sung `app/business/packs/` làm kho lưu trữ Factory & Company Overrides.
3. **Thực thi tuần tự:** Bắt đầu Phase 1 (Core Engine) và Phase 2 (4 Pilot Packs: Governance, Operations, Sales, Reporting) với 3–5 capabilities mỗi pack.
