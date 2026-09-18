# Sandbox Isolation & Security Guide for Workspace Site Builder

Tài liệu hướng dẫn tiêu chuẩn an toàn và cô lập môi trường Sandbox dành cho **CTO Agent** và các subagents khi thực thi tác vụ sinh mã, cài đặt phụ thuộc, kiểm thử và đóng gói website/storefront cho từng Workspace riêng biệt.

---

## 1. Nguyên Tắc Cốt Tử: Tách Biệt Tuyệt Đối Với Core SaaS & Landing

> [!CAUTION]
> **Ranh Giới Bất Khả Xâm Phạm (Absolute Boundary):**
> - Thư mục `landing/` ở gốc repository là Landing Page của chính nền tảng COSA SaaS.
> - CTO Agent và bất kỳ coding subagent nào **tuyệt đối không được đọc, sửa, ghi đè hoặc import** tài nguyên từ `landing/` hoặc các package lõi (`services/cosa/`, `services/company/`, `shared/`).
> - Mọi thao tác I/O chỉ được phép diễn ra trong thư mục Sandbox được phân bổ cụ thể cho Workspace.

---

## 2. Cấu Trúc Không Gian Môi Trường Sandbox (Directory Structure)

Mỗi website của workspace được cô lập trong đường dẫn tiêu chuẩn:
`var/sandboxes/{workspace_id}/sites/{site_id}/`

```
var/sandboxes/{workspace_id}/sites/{site_id}/
├── .env.sandbox                 # Chỉ chứa public/client-safe envs hoặc test keys
├── package.json                 # Phụ thuộc đóng gói độc lập
├── tsconfig.json                # TypeScript strict mode
├── tailwind.config.ts           # Token thiết kế riêng của Workspace
├── next.config.mjs              # Cấu hình Next.js (output: 'export' hoặc standalone)
├── app/
│   ├── layout.tsx               # Root layout tích hợp font & metadata
│   ├── page.tsx                 # Trang chủ
│   ├── [slug]/page.tsx          # Dynamic routing cho các trang nội dung
│   ├── api/                     # Backend handlers nội bộ (submit form, checkout)
│   │   ├── forms/submit/route.ts
│   │   └── checkout/webhook/route.ts
│   └── globals.css              # Style nền tảng
├── components/
│   ├── blocks/                  # Thư viện Block giao diện (Hero, Features, FAQ...)
│   ├── forms/                   # Thư viện Form & Survey wizard
│   └── commerce/                # Cart drawer, Product card, Checkout form
├── data/
│   ├── site-config.json         # Cấu trúc toàn site, navigation, branding
│   └── catalog.json             # Danh mục sản phẩm/dịch vụ
└── out/                         # Thư mục artifact sau khi chạy `npm run build`
```

---

## 3. Quản Lý Secrets & Biến Môi Trường (Secrets Isolation)

1. **Không rò rỉ Secrets của Hệ Thống:**
   - Không được truyền bất kỳ biến môi trường nào của COSA SaaS (như `DATABASE_URL`, `COSA_JWT_SECRET`, Stripe master keys) vào tiến trình chạy trong Sandbox.
2. **Quản lý Secrets riêng của Workspace:**
   - Các API keys của bên thứ ba do Workspace cấu hình (ví dụ: `PAYOS_CLIENT_ID`, `PAYOS_API_KEY`, `PAYOS_CHECKSUM_KEY`, `RESEND_API_KEY`) được nạp qua Vault hoặc Secret Broker dạng masked/injected lúc runtime, không commit trực tiếp vào git hay mã nguồn mở.
   - Các biến public dùng prefix `NEXT_PUBLIC_` (như `NEXT_PUBLIC_SITE_NAME`, `NEXT_PUBLIC_TURNSTILE_SITE_KEY`).

---

## 4. Kiểm Soát Tài Nguyên & Rủi Ro Thực Thi (Resource & Runtime Limits)

Khi CTO chỉ đạo khởi chạy các lệnh trong sandbox, phải tuân thủ các hạn mức sau:

| Chỉ số | Hạn mức cho phép | Biện pháp xử lý khi vượt |
| :--- | :--- | :--- |
| **Thời gian chạy Build** | Tối đa 300 giây (5 phút) | Timeout kill process, log cảnh báo tối ưu bundle |
| **Bộ nhớ RAM** | Tối đa 2GB per build container | OOM killer bảo vệ node host |
| **Dung lượng đĩa Sandbox** | Tối đa 1GB (bao gồm `node_modules` và `.next`) | Xóa cache trung gian sau build |
| **Quyền mạng (Network Egress)** | Chỉ cho phép outbound tới npm registry và webhook endpoints được whitelist | Ngăn chặn botnet/data exfiltration |

---

## 5. Vòng Lặp Kiểm Chuẩn Chất Lượng (In-Sandbox Quality Gates)

Trước khi CTO Agent tạo bản đề xuất `L1_PROPOSE` gửi tới Founder, dự án trong Sandbox bắt buộc phải vượt qua 4 chốt kiểm tra tuần tự:

```bash
# 1. Kiểm tra Linter: Không có cú pháp lỗi thời hoặc cú pháp gây crash
npm run lint

# 2. Kiểm tra TypeScript: Strict typecheck 100%, không sử dụng 'any' bừa bãi
npm run typecheck

# 3. Chạy Unit Tests: Đảm bảo logic tính toán tiền tệ, validate form chạy chính xác
npm run test

# 4. Biên dịch Production: Đảm bảo build static/SSG hoặc standalone server thành công
npm run build
```

Nếu bất kỳ bước nào thất bại, tiến trình đóng gói bị chặn lại ngay lập tức. Coding subagent nhận phản hồi lỗi từ terminal log để tự động debug và sửa lỗi trong Sandbox.

---

## 6. Cơ Chế Bàn Giao Bản Đóng Gói (Artifact Export & Ingress Routing)

Sau khi Founder phê duyệt (**Human Approval**):
1. Thư mục artifact hoàn chỉnh (`out/` hoặc container image) được gắn cờ `RELEASE_READY`.
2. Hệ thống Ingress Router của COSA trỏ routing:
   - **Subdomain:** `{workspace_slug}.cosa.site` ➔ Liên kết với storage/bucket của `out/`.
   - **Custom Domain:** Kiểm tra CNAME `domain.com` ➔ `proxy.cosa.site`, tự động xin chứng chỉ TLS qua ACME (Let's Encrypt).
3. Sandbox được chuyển về trạng thái lưu trữ (Archived) hoặc duy trì làm môi trường Staging/Preview cho lần chỉnh sửa tiếp theo.
