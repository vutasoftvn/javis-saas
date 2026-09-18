# Kế Hoạch Triển Khai: Xây Dựng Skillpack `workspace-site-builder` Cho CTO Agent

**Ngày lập:** 2026-09-18  
**Tài liệu tham chiếu:** [`docs/cosa.md`](file:///Volumes/SSD/javis-saas/docs/cosa.md), [`shared/contracts/executive-advisor-roles.json`](file:///Volumes/SSD/javis-saas/shared/contracts/executive-advisor-roles.json), [`skillpacks/executive/cto-advisor/SKILL.md`](file:///Volumes/SSD/javis-saas/skillpacks/executive/cto-advisor/SKILL.md)  
**Trạng thái:** Chờ phê duyệt từ Founder (Planning Mode - Chưa tạo mã nguồn)

---

## 1. Tóm Tắt Mục Tiêu & Ranh Giới Kiến Trúc

Kế hoạch này nhằm xây dựng một Skillpack chuyên biệt mang tên **`engineering.workspace-site-builder`** ghim trực tiếp cho **CTO Agent**, cho phép CTO tự động hóa quy trình kiến trúc, chỉ đạo phát triển và phát hành ứng dụng web cho từng Workspace khách hàng theo mô hình **Human-Light, Agent-Heavy**.

### Ranh Giới Hệ Thống Tuyệt Đối (Strict System Boundaries):
1. **Tuyệt đối tách biệt với [`landing/`](file:///Volumes/SSD/javis-saas/landing):**
   - Thư mục `landing/` là Landing Page của chính nền tảng COSA SaaS. CTO Agent **tuyệt đối KHÔNG đụng chạm, KHÔNG import, KHÔNG chỉnh sửa** bất kỳ tệp nào trong `landing/`.
2. **Môi Trường Thực Thi Cô Lập (Isolated Workspace Sandbox):**
   - Mọi hoạt động sinh mã, cài đặt phụ thuộc (`npm install`), biên dịch và kiểm thử diễn ra hoàn toàn trong môi trường **Sandbox cô lập** dành riêng cho Workspace đó (ví dụ: `var/sandboxes/{workspace_id}/sites/{site_id}/` hoặc OpenSandbox container).
3. **Quy Trình Phát Hành (Domain Deployment Pipeline):**
   - Sau khi ứng dụng web trong Sandbox hoàn thành toàn bộ chuỗi kiểm chuẩn (`lint` ➔ `typecheck` ➔ `test` ➔ `build`), bản đóng gói (artifact) sẽ được đẩy lên:
     - **Subdomain của Workspace:** `https://{workspace_slug}.cosa.site` (hoặc `.javis.ai`).
     - **Domain Riêng (Custom Domain):** `https://{custom_domain}` (hỗ trợ xác thực DNS CNAME và cấu hình SSL tự động).
4. **Trần Tự Trị & Chốt Chặn Con Người (`L1_PROPOSE`):**
   - CTO Agent chỉ đạo sinh mã và thử nghiệm trong Sandbox.
   - Việc kích hoạt phát hành (Publish) lên Subdomain hoặc Custom Domain Production **bắt buộc phải có sự phê duyệt (Approval) của Founder hoặc Quản trị viên Workspace**.

---

## 2. Thiết Kế Chi Tiết Skillpack `engineering.workspace-site-builder`

### 2.1. Cấu Trúc Thư Mục Skillpack
```
skillpacks/engineering/workspace-site-builder/
├── manifest.yaml                                       # Chuẩn agentos.ai/v1
├── SKILL.md                                            # Quy trình 7 bước điều hành của CTO
└── references/
    ├── sandbox_isolation_guide.md                      # Tiêu chuẩn cô lập Sandbox & bảo mật secrets
    ├── site_and_block_specifications.md                # Schema JSON Block cho Web & Landing Page
    ├── form_survey_engine_spec.md                      # Schema Form/Khảo sát, branching & lead scoring
    └── ecommerce_checkout_integration.md               # Schema Sản phẩm, 1-Page Checkout, VietQR & Stripe
evals/engineering/workspace-site-builder.yaml           # Bộ kiểm chuẩn an toàn & cô lập workspace
```

---

## 3. Các Thay Đổi Đề Xuất (Proposed Changes)

### Vùng 1: Tạo Skillpack (`skillpacks/engineering/workspace-site-builder/`)

#### [NEW] [`manifest.yaml`](file:///Volumes/SSD/javis-saas/skillpacks/engineering/workspace-site-builder/manifest.yaml)
- Khai báo theo chuẩn `agentos.ai/v1`:
  - `metadata.id`: `engineering.workspace-site-builder`
  - `metadata.name`: "Workspace Website, Form & Commerce Builder (Sandbox Execution)"
  - `capability.intents`: `["workspace site builder", "sandbox web app generator", "survey form builder", "ecommerce storefront generator", "subdomain deploy"]`
  - `autonomy.ceiling`: `L1_PROPOSE`, `side_effect_class`: `A`
  - `permissions.required`: `[READ_LOCAL]`
  - `applicability.project_stages`: `[P3_BUILD_VALIDATE, P4_GO_TO_MARKET, P5_OPERATE_GROWTH, P6_SCALE_GOVERN]`
  - `applicability.gates`: `[G3, G4, G5, G6]`
  - `evidence.min_source_refs`: 1, `evidence.self_validation_forbidden`: true
  - `quality.eval_suite`: `evals/engineering/workspace-site-builder.yaml`

#### [NEW] [`SKILL.md`](file:///Volumes/SSD/javis-saas/skillpacks/engineering/workspace-site-builder/SKILL.md)
Khung quy trình điều phối 7 bước chuyên sâu của CTO:
1. **Bước 1 - Khảo sát & Định hình Kiến trúc (Architecture Framing):**
   - Phân loại: Landing Page đơn / Web đa trang / Form khảo sát / Cửa hàng E-commerce.
   - Soạn thảo Mini-ADR về kiến trúc: Next.js SSG / Astro, Component UI Block, cơ chế lưu trữ dữ liệu.
2. **Bước 2 - Cấp phát Môi trường Sandbox (Sandbox Provisioning):**
   - Khởi tạo thư mục sandbox cô lập theo `workspace_id` và `site_id`.
   - Thiết lập cấu trúc dự án mẫu (Scaffolding: package.json, tsconfig, tailwind, router).
3. **Bước 3 - Chỉ đạo Sinh Mã Giao diện & Tính năng (Code Generation Orchestration):**
   - *Web/Landing Module:* Trang chủ (`/`) và các trang con (`/about`, `/pricing`, `/services`, v.v.) theo cấu trúc JSON Blocks.
   - *Form/Survey Module:* Form thu thập thông tin cơ bản + Khảo sát chọn lọc (Multi-step, Single-choice, Dropdown, Rating) kèm validation Zod.
   - *E-Commerce Module:* Catalog sản phẩm/dịch vụ, mini-cart, 1-Page Checkout, cổng thanh toán VietQR (PayOS/SePay) & Stripe.
4. **Bước 4 - Kiểm soát Chất lượng Trong Sandbox (In-Sandbox Quality Loop):**
   - Thực thi chuỗi lệnh kiểm thử tự động bên trong sandbox:
     `npm run lint` ➔ `npm run typecheck` ➔ `npm run build`.
   - Đảm bảo 0 lỗi biên dịch, không lỗi hydration, hiệu năng Core Web Vitals đạt chuẩn.
5. **Bước 5 - Thẩm định & Phê duyệt Bản Preview (Human Review & Approval):**
   - Khởi chạy dev server preview trong sandbox.
   - Gửi bản đề xuất phát hành (`L1_PROPOSE`) kèm link preview và báo cáo chất lượng cho Founder.
6. **Bước 6 - Đóng gói & Phát hành Lên Domain (Deployment Pipeline):**
   - Khi có sự phê duyệt: Đóng gói artifact (`out/` static bundle hoặc docker image).
   - Cấu hình Ingress/Reverse Proxy trỏ tới:
     - Subdomain: `https://{workspace_slug}.cosa.site`
     - Custom Domain: Cấu hình bản ghi CNAME, cấp chứng chỉ SSL tự động (Let's Encrypt / Cloudflare).
7. **Bước 7 - Bàn giao & Kích hoạt Webhook (Post-Deploy Handover):**
   - Kiểm tra Health check 200 OK trên domain thực tế.
   - Kích hoạt Webhook tiếp nhận Form Leads về CRM và Webhook ngân hàng cho đơn hàng E-Commerce.

#### [NEW] Bộ Tài Liệu Kỹ Thuật Tham Khảo (`references/`):
- `references/sandbox_isolation_guide.md`: Hướng dẫn cô lập Sandbox, bảo vệ secrets, tách biệt hoàn toàn khỏi core COSA.
- `references/site_and_block_specifications.md`: Đặc tả JSON Block Schema cho giao diện Web, Header, Footer, Hero, Grid, SEO meta.
- `references/form_survey_engine_spec.md`: Đặc tả Form đa bước, logic phân nhánh (conditional branching), chống bot spam (Turnstile/Honeypot), tính điểm tiềm năng (lead scoring).
- `references/ecommerce_checkout_integration.md`: Đặc tả Product/Service, giỏ hàng, 1-Page Checkout, tích hợp Webhook VietQR & Stripe, máy trạng thái đơn hàng.

#### [NEW] [`evals/engineering/workspace-site-builder.yaml`](file:///Volumes/SSD/javis-saas/evals/engineering/workspace-site-builder.yaml)
- Test suite kiểm chuẩn: Chặn sửa đổi ngoài sandbox, chặn tác động vào `landing/`, chặn deploy tự động khi chưa có Human Approval.

---

### Vùng 2: Hợp Đồng Vai Trò & Ghim Kỹ Năng Cho CTO

#### [MODIFY] [`shared/contracts/executive-advisor-roles.json`](file:///Volumes/SSD/javis-saas/shared/contracts/executive-advisor-roles.json)
- Cập nhật vai trò `cto` bổ sung kỹ năng mới:
  ```json
  "requiredSkillPins": [
    "skillpack:executive/cto-advisor@1.0.0",
    "skillpack:engineering/workspace-site-builder@1.0.0"
  ]
  ```

#### [EXEC] Sinh Mã Đồng Bộ:
- Chạy `node scripts/gen-executive-advisor-roles.mjs` để cập nhật TypeScript interfaces và Python role definitions.

---

### Vùng 3: Kiểm Thử & Xác Thực Toàn Diện

#### [NEW] [`tests/agent/executive_board/test_workspace_site_builder_skill.py`](file:///Volumes/SSD/javis-saas/tests/agent/executive_board/test_workspace_site_builder_skill.py)
- Kiểm tra tính hợp lệ của skill pin `skillpack:engineering/workspace-site-builder@1.0.0`.
- Kiểm tra vai trò `cto` sở hữu đầy đủ 2 skill pins (Advisor + Builder).

---

## 4. Kế Hoạch Kiểm Thử (Verification Plan)

1. **Kiểm tra Schema Skillpack:**
   ```bash
   make skillpacks-validate
   ```
2. **Kiểm tra Đồng bộ Hợp đồng Role:**
   ```bash
   node scripts/gen-executive-advisor-roles.mjs --check
   ```
3. **Chạy Unit Tests Executive Board:**
   ```bash
   .venv/bin/pytest tests/agent/executive_board/
   ```
4. **Kiểm tra TypeScript Typecheck & Python Lint:**
   ```bash
   npm --prefix services/company run typecheck
   npm --prefix services/cosa run typecheck
   make lint
   ```
