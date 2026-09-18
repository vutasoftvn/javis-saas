---
name: engineering-workspace-site-builder
description: Kỹ năng chuyên sâu cho CTO Agent chỉ đạo và điều phối xây dựng website đa trang, landing page, form/khảo sát tương tác và cửa hàng thương mại điện tử trong môi trường Sandbox cô lập, sau đó phát hành lên subdomain hoặc domain riêng của Workspace.
---

# Workspace Website, Form & Commerce Builder (Sandbox Execution)

Khung kỹ năng thực thi kỹ thuật dành cho **CTO Agent** để chỉ đạo kiến trúc, điều phối sinh mã trong môi trường **Sandbox cô lập**, kiểm thử chất lượng và phát hành trọn gói ứng dụng web (Landing Page, Website đa trang, Khảo sát tương tác, Cửa hàng E-Commerce) lên **Subdomain** hoặc **Custom Domain** của Workspace.

---

## 1. Định Vị Kỹ Năng & Ranh Giới Cô Lập Tuyệt Đối (Boundary Isolation)

> [!CAUTION]
> **Ranh Giới Bất Khả Xâm Phạm Với `landing/`:**
> Thư mục `landing/` là trang chủ tiếp thị của chính nền tảng COSA SaaS. CTO Agent và các coding agents cấp dưới **tuyệt đối KHÔNG đụng chạm, KHÔNG import, KHÔNG sửa đổi** bất kỳ tệp tin nào trong `landing/`. Mọi hành vi làm biến đổi `landing/` bị coi là vi phạm an toàn hệ thống nghiêm trọng.

### Các Nguyên Tắc Cô Lập Bắt Buộc:
1. **Môi trường Sandbox Độc lập (Isolated Workspace Sandbox):**
   - Mọi mã nguồn, cấu hình `package.json`, cài đặt thư viện (`npm install`), sinh giao diện và biên dịch chạy trong thư mục sandbox được chỉ định:  
     `var/sandboxes/{workspace_id}/sites/{site_id}/` (hoặc OpenSandbox container).
   - Không được phép truy cập file hệ thống ngoài phạm vi thư mục sandbox của workspace đó.
2. **Trần Tự Trị & Chốt Chặn Phê Duyệt (`L1_PROPOSE`):**
   - CTO Agent có quyền chỉ đạo tạo mã nguồn, chạy thử nghiệm và kiểm thử tự động trong Sandbox.
   - Hành động đóng gói và kích hoạt phát hành (Publish/Deploy) lên **Subdomain** hoặc **Custom Domain Production** bắt buộc phải có sự phê duyệt (**Human Approval**) từ Founder hoặc Quản trị viên Workspace.
3. **Mục Tiêu Phát Hành (Target Deployment):**
   - **Subdomain của Workspace:** `https://{workspace_slug}.cosa.site` (hoặc `.javis.ai`).
   - **Tên miền Riêng (Custom Domain):** `https://{custom_domain}` (hỗ trợ xác thực DNS CNAME và cấp chứng chỉ SSL Let's Encrypt tự động).

---

## 2. Quy Trình 7 Bước Điều Hành Triển Khai Của CTO (Execution Workflow)

```
[B1: Khảo Sát & Kiến Trúc] ➔ [B2: Cấp Phát Sandbox] ➔ [B3: Điều Phối Sinh Mã]
                                                          │
                                                          ▼
[B6: Deploy Subdomain/Domain] ◄─ [B5: Human Approval] ◄─ [B4: In-Sandbox Build/Test]
          │
          ▼
[B7: Bàn Giao & Webhooks]
```

### Bước 1: Tiếp Nhận Yêu Cầu & Lập Bản Thảo Kiến Trúc (Architecture Framing)
- Xác định phạm vi dự án từ yêu cầu của Founder:
  - **Type A: Landing Page Đơn (Single Page)** — Giới thiệu sản phẩm, dịch vụ, chuyển đổi leads nhanh.
  - **Type B: Website Đa Trang (Multi-Page CMS)** — Trang chủ (`/`), Giới thiệu (`/about`), Tính năng/Dịch vụ (`/services`), Bảng giá (`/pricing`), Blog, Liên hệ (`/contact`).
  - **Type C: Form Thu Thập & Khảo Sát Tương Tác (Survey & Qualification)** — Multi-step wizard, khảo sát trắc nghiệm, tính điểm tiềm năng (lead score).
  - **Type D: Cửa Hàng E-Commerce (Storefront & Checkout)** — Bán sản phẩm số, dịch vụ tư vấn, khóa học hoặc hàng vật lý kèm giỏ hàng và thanh toán.
- Soạn thảo Mini-ADR lựa chọn Tech Stack trong Sandbox: Next.js SSG / App Router, Tailwind CSS, Lucide Icons, Zod Validation, SQLite/PostgreSQL Client.

### Bước 2: Cấp Phát Môi Trường Sandbox (Sandbox Provisioning)
- Khởi tạo không gian làm việc cô lập: `var/sandboxes/{workspace_id}/sites/{site_id}/`.
- Khởi tạo bộ khung dự án sạch (Scaffolding):
  - `package.json` với các dependency tiêu chuẩn an toàn.
  - `tsconfig.json` cấu hình strict mode.
  - `tailwind.config.ts` nạp hệ thống màu sắc/typography theo thương hiệu của Workspace.
  - Cấu trúc thư mục: `app/`, `components/blocks/`, `components/forms/`, `components/commerce/`, `lib/`.

### Bước 3: Điều Phối Sinh Mã Giao Diện & Tính Năng (Code Generation)
CTO phân rã tác vụ và chỉ đạo Coding Agent sinh mã theo 3 Module:

#### Module 1: Web & Landing Page Engine
- Áp dụng cấu trúc **JSON Block Tree** (xem [references/site_and_block_specifications.md](file:///Volumes/SSD/javis-saas/skillpacks/engineering/workspace-site-builder/references/site_and_block_specifications.md)).
- Xây dựng các khối giao diện: `Navbar`, `HeroBlock`, `FeatureGridBlock`, `ContentSectionBlock`, `PricingTableBlock`, `TestimonialBlock`, `FAQBlock`, `FooterBlock`.
- Thiết lập dynamic routing `app/[slug]/page.tsx` để render mọi trang con theo dữ liệu.
- Tự động sinh thẻ Meta SEO, OpenGraph tags, sitemap.xml và robots.txt.

#### Module 2: Form Thu Thập & Khảo Sát Tương Tác
- Triển khai bộ sinh Form đa bước (Multi-step Survey) (xem [references/form_survey_engine_spec.md](file:///Volumes/SSD/javis-saas/skillpacks/engineering/workspace-site-builder/references/form_survey_engine_spec.md)).
- Hỗ trợ các trường: Thông tin cơ bản (Tên, Email, SĐT), Chọn 1 (Single-choice), Chọn nhiều (Multiple-choice), Thang điểm (Rating 1–5), Ý kiến mở (Textarea).
- Tích hợp Zod schema validation tại client và server.
- Bảo mật: Tích hợp trường ẩn chống bot (**Honeypot field**) và Cloudflare Turnstile captcha.
- Lưu trữ kết quả submit vào SQLite/JSONB nội bộ và cấu hình gửi webhook/email thông báo.

#### Module 3: E-Commerce Storefront & Checkout
- Quản lý catalog sản phẩm/dịch vụ: Sản phẩm số (Ebook/Khóa học), Dịch vụ tư vấn (Booking), Sản phẩm vật lý (xem [references/ecommerce_checkout_integration.md](file:///Volumes/SSD/javis-saas/skillpacks/engineering/workspace-site-builder/references/ecommerce_checkout_integration.md)).
- Mini-cart drawer trượt bên hông mượt mà.
- Trang thanh toán tinh gọn **1-Page Checkout** (giảm thiểu tỷ lệ bỏ rơi giỏ hàng):
  - Tích hợp **VietQR tự động (SePay/PayOS)**: Tự động hiển thị mã QR kèm số tiền và mã đơn hàng; webhook ngân hàng xác nhận thanh toán trong 2–5 giây.
  - Tích hợp **Stripe Checkout** cho khách hàng quốc tế.
- Máy trạng thái đơn hàng (Order State Machine): `PENDING` ➔ `PAID` ➔ `FULFILLED`.

### Bước 4: Kiểm Soát Chất Lượng Trong Sandbox (In-Sandbox Quality Loop)
Trước khi thông báo cho con người, CTO bắt buộc thực thi chuỗi kiểm chuẩn tự động ngay trong Sandbox:
```bash
# 1. Kiểm tra cú pháp và quy chuẩn mã nguồn
npm run lint

# 2. Kiểm tra an toàn kiểu dữ liệu TypeScript (0 errors)
npm run typecheck

# 3. Chạy unit tests các logic tính toán (tính tiền giỏ hàng, điểm khảo sát)
npm run test

# 4. Biên dịch Production bundle thử nghiệm (kiểm tra không bị lỗi SSR/Hydration)
npm run build
```
Nếu có lỗi phát sinh: Coding Agent tự động sửa chữa ngay trong sandbox cho đến khi `npm run build` đạt Exit Code 0.

### Bước 5: Preview & Trình Phê Duyệt Của Con Người (Human Review & Approval)
- Khởi chạy preview server cục bộ nội bộ sandbox (hoặc export static preview).
- CTO Agent tổng hợp hồ sơ đề xuất phát hành (`L1_PROPOSE`):
  ```text
  1. Bottom Line: Đã xây dựng hoàn tất website/storefront cho workspace trong Sandbox.
  2. Báo cáo chất lượng: Lint (Pass), Typecheck (Pass), Build (Pass - Bundle size: XX kB).
  3. Danh sách trang & tính năng: Trang chủ, 3 trang con, Form khảo sát 2 bước, Cửa hàng 4 sản phẩm.
  4. Link xem trước (Preview URL): http://localhost:PORT (hoặc preview token).
  5. Quyết định cần duyệt: Xác nhận phát hành lên Subdomain: https://{slug}.cosa.site?
  ```

### Bước 6: Đóng Gói & Phát Hành Lên Domain (Deployment Pipeline)
Khi Founder hoặc Quản trị viên bấm nút **Phê duyệt**:
1. Đóng gói bản build sạch (`out/` directory cho static export hoặc Docker container image).
2. Đẩy artifact vào hạ tầng Ingress / CDN phục vụ của hệ thống.
3. Cấu hình định tuyến:
   - **Subdomain:** Tạo bản ghi routing trỏ `subdomain.cosa.site` về thư mục build của workspace.
   - **Custom Domain:** Kiểm tra bản ghi CNAME của khách hàng ➔ Kích hoạt cấp chứng chỉ SSL Let's Encrypt / Cloudflare SSL tự động.

### Bước 7: Bàn Giao, Kiểm Tra Sau Triển Khai & Webhooks (Post-Deploy Handover)
- Kiểm tra tính sẵn sàng: Gửi HTTP GET request tới domain thật, đảm bảo trả về `200 OK` và SSL hợp lệ (`https://`).
- Kích hoạt luồng Webhooks:
  - Form Leads tự động đồng bộ vào CRM nội bộ của Workspace.
  - Thông báo thanh toán thành công tự động bắn qua Telegram/Email cho chủ doanh nghiệp.

---

## 3. Báo Động Đỏ Kỹ Thuật (Red Flags)

- Phát hiện bất kỳ hành vi đọc/ghi nào nhắm vào thư mục `landing/` hoặc mã nguồn core của COSA ➔ Dừng tiến trình ngay lập tức.
- Build time trong Sandbox vượt quá 5 phút ➔ Yêu cầu tối ưu hóa dung lượng dependencies và assets hình ảnh.
- Thiếu Honeypot hoặc Captcha trên các Form công khai ➔ Nguy cơ bị spam bot tấn công phá hoại database.
- Tích hợp thanh toán thiếu Idempotency key hoặc thiếu kiểm tra chữ ký Webhook (HMAC signature verification).
- Tự ý deploy lên domain thật mà chưa có bản ghi Human Approval từ Founder con người.

---

## 4. Tài Liệu Tham Khảo Kèm Theo (References)

- [references/sandbox_isolation_guide.md](file:///Volumes/SSD/javis-saas/skillpacks/engineering/workspace-site-builder/references/sandbox_isolation_guide.md) — Tiêu chuẩn cô lập Sandbox, phân tách tài nguyên và bảo vệ secrets.
- [references/site_and_block_specifications.md](file:///Volumes/SSD/javis-saas/skillpacks/engineering/workspace-site-builder/references/site_and_block_specifications.md) — Đặc tả cấu trúc JSON Blocks cho giao diện Web, Header, Hero, Features, Pricing, SEO.
- [references/form_survey_engine_spec.md](file:///Volumes/SSD/javis-saas/skillpacks/engineering/workspace-site-builder/references/form_survey_engine_spec.md) — Đặc tả Form/Khảo sát tương tác đa bước, logic phân nhánh, Turnstile và chấm điểm leads.
- [references/ecommerce_checkout_integration.md](file:///Volumes/SSD/javis-saas/skillpacks/engineering/workspace-site-builder/references/ecommerce_checkout_integration.md) — Mô hình sản phẩm, 1-Page Checkout, tích hợp VietQR (PayOS/SePay) & Stripe.
