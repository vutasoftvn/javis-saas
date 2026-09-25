# Kế Hoạch Triển Khai: Tích Hợp Product Manager Skills & Quantitative Analyzers vào COSA

**Ngày lập:** 2026-09-19  
**Tài liệu tham chiếu:**  
- [`Digidai/product-manager-skills`](https://github.com/Digidai/product-manager-skills) (Commit SHA: `ab7a40662c8455ece631834dee9670b3322f465b`, MIT License)  
- [`packages/agent/workforce/catalog.py`](../../../packages/agent/workforce/catalog.py)  
- [`apps/cosa/agents/specs.py`](../../../apps/cosa/agents/specs.py)  
- [`skillpacks/executive/cpo-advisor/SKILL.md`](../../../skillpacks/executive/cpo-advisor/SKILL.md)  
- [`packages/agent/executive_board/analyzers.py`](../../../packages/agent/executive_board/analyzers.py)  
**Trạng thái:** Đang triển khai

---

## 1. Mục Tiêu & Ranh Giới Thiết Kế

Kế hoạch này tích hợp tri thức quản trị sản phẩm cao cấp từ `Digidai/product-manager-skills` vào nền tảng **COSA (javis-saas)**:
1. **Workforce & Agent Specialization:** Bổ sung `product_spec_specialist` vào danh mục `FUNCTIONAL_AGENT_CATALOG`, nâng cấp `COSA_PRODUCT_AGENT_SPEC` và `COSA_EXECUTIVE_CPO_AGENT_SPEC` với Voice Guidelines, Framing Gate và danh mục kỹ năng được ghim cụ thể.
2. **Nâng Cấp Skillpacks Sản Phẩm:** Nâng cấp 4 skillpack sản phẩm hiện có (`prd`, `user-story-and-acceptance`, `backlog-prioritization`, `cpo-advisor`) từ dạng khung xương sơ khai (~44 dòng) lên chuẩn thực chiến 10 mục hoàn chỉnh.
3. **Bộ 3 Skillpacks Chiến Lược Mới:**
   - `ai.ai-product-craft`: Khung năng lực AI-Shaped, Context Engineering (chống context rot bằng chu trình Research->Plan->Reset->Implement), 5 loại PoL Probes và cẩm nang xử lý Hallucination / Latency.
   - `growth.plg-activation`: Phương pháp 4 bước tìm kiếm Activation Event (Aha Moment), chẩn đoán rớt phễu Onboarding, Viral Loop & K-factor, mô hình Freemium và Reverse Trial.
   - `finance.saas-metrics-diagnostic`: Bảng chẩn đoán sức khỏe SaaS 4 chiều, Churn compounding (`1 - (1-r)^12`), LTV:CAC vs Payback, phân tích ROI tính năng và kinh tế kênh.
4. **Bộ Công Cụ Phân Tích Định Lượng (Deterministic Analyzers):** 5 hàm tính toán tất định 100% Python Standard Library trong `packages/agent/executive_board/analyzers.py`.
5. **Minh Bạch Bản Quyền:** Ghi nhận nguồn gốc giấy phép MIT và commit SHA `ab7a40662c8455ece631834dee9670b3322f465b` vào Sổ cái nguồn gốc `docs/integrations/skill-source-attribution.md`.

### Ranh Giới Quản Trị & An Toàn Bắt Buộc:
- **Trần Tự Trị Tuyệt Đối L1_PROPOSE:** Mọi agent sản phẩm chỉ tạo tài liệu nháp và kiến nghị; quyền quyết định phát hành, ngân sách hay xóa tính năng luôn thuộc về Founder con người.
- **100% Python Standard Library:** Không thêm package phụ thuộc bên ngoài vào `requirements.txt` hay `pyproject.toml`.
- **Chuẩn Hóa 10 Mục Skillpack & Evals:** Mọi skillpack mới/nâng cấp đều có `manifest.yaml` (chuẩn `agentos.ai/v1`), `SKILL.md` tiếng Việt 10 mục và file kiểm chuẩn `evals/<domain>/<name>.yaml`.

---

## 2. Các Hạng Mục Triển Khai Chi Tiết

### Hợp Phần 1: Workforce Catalog & Agent Specs
- **`packages/agent/workforce/catalog.py`**: Bổ sung `product_spec_specialist` thuộc phòng ban `Product`.
- **`tests/apps/cosa/test_workforce_routes.py`**: Chuyển assert cứng độ dài danh mục sang `len(FUNCTIONAL_AGENT_CATALOG)`.
- **`apps/cosa/agents/specs.py`**: Cập nhật instructions, Voice Guidelines và bump version lên `1.1.0` cho `COSA_PRODUCT_AGENT_SPEC` và `COSA_EXECUTIVE_CPO_AGENT_SPEC`.
- **`apps/cosa/tests/test_product_cpo_specs.py`**: Cập nhật test hash và version `1.1.0`.

### Hợp Phần 2: Analyzers Định Lượng (`packages/agent/executive_board/analyzers.py`)
- `calculate_compounded_churn(monthly_churn_pct)`
- `diagnose_saas_health_scorecard(metrics, stage)`
- `score_growth_experiment_ice(impact, confidence, ease)`
- `calculate_viral_k_factor(invites_sent_per_user, invite_conversion_rate_pct)`
- `analyze_feature_investment_roi(dev_cost, expected_annual_value, cogs_annual, feature_type)`
- Unit tests: `tests/agent/executive_board/test_product_and_plg_analyzers.py`

### Hợp Phần 3: Skillpacks Nâng Cấp & Mới
- Nâng cấp: `skillpacks/product/prd/SKILL.md`, `skillpacks/product/user-story-and-acceptance/SKILL.md`, `skillpacks/product/backlog-prioritization/SKILL.md`, `skillpacks/executive/cpo-advisor/SKILL.md`.
- Tạo mới: `skillpacks/ai/ai-product-craft/`, `skillpacks/growth/plg-activation/`, `skillpacks/finance/saas-metrics-diagnostic/` cùng các file `manifest.yaml` và `evals/`.

### Hợp Phần 4: Sổ Cái Nguồn Gốc (Attribution)
- Cập nhật `docs/integrations/skill-source-attribution.md` (Nhóm H: `product-manager-skills`, commit `ab7a40662c8455ece631834dee9670b3322f465b`).
