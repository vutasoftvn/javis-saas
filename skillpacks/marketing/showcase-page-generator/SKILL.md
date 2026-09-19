---
name: marketing-showcase-page-generator
description: Hướng dẫn tạo trang web giới thiệu sản phẩm tương tác cao dạng single-file HTML trong môi trường Sandbox cô lập của Workspace, sử dụng GSAP 3D và parallax mà không can thiệp vào mã nguồn gốc.
---

# Bộ Sinh Trang Giới Thiệu Tương Tác 3D Trong Sandbox (Showcase Page Generator)

## 1. Mục Tiêu (Objective)
Tạo ra một trang web giới thiệu sản phẩm visual premium dạng tệp HTML đơn lẻ (Single-file self-contained `.html`), tích hợp hoạt ảnh GSAP 3D, hiệu ứng chiều sâu theo chuyển động chuột (mouse-parallax) và cuộn trang (scroll-trigger). Trang web được khởi tạo tức thì trong **môi trường Sandbox cô lập của Workspace** để phục vụ việc demo sản phẩm, pitching nhà đầu tư hoặc thử nghiệm chiến dịch ra mắt mà không cần chạy quy trình build phức tạp.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi cần tạo trang landing page visual "Wow factor" trong vài giây cho một sản phẩm, tính năng mới hoặc sự kiện của Workspace.
  - Khi cần một file HTML độc lập có thể xem offline, gửi đính kèm hoặc host thử nghiệm nội bộ trong Sandbox.
  - Khi muốn tối ưu hóa yếu tố ấn tượng thị giác (Visual Premium) thay vì cấu trúc form thu thập phức tạp.
- **Khi nào KHÔNG dùng**:
  - Khi cần xây dựng website đa trang đầy đủ tính năng thanh toán giỏ hàng, blog CMS (dùng `engineering.workspace-site-builder`).
  - **TUYỆT ĐỐI KHÔNG DÙNG**: Để sửa đổi, can thiệp hoặc ghi đè lên thư mục `landing/` ở gốc repository của COSA SaaS.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `workspace_id` hợp lệ được cấp quyền truy cập Sandbox.
- Thông tin sản phẩm cơ bản (Tên, Elevator pitch 1-2 câu, phân khúc độc giả, mã màu thương hiệu).
- Bảng màu đã được xác thực qua `PaletteContrastValidator` đạt chuẩn WCAG 2.1 AA.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Tiếp Nhận 4 Câu Hỏi Định Hướng (4-Question Intake)**:
   - *Sản phẩm*: Tên gọi và tuyên bố giá trị duy nhất (1 câu ngắn gọn).
   - *Tệp độc giả*: Kỹ thuật (Technical) / Doanh nghiệp (B2B) / Tiêu dùng (Consumer).
   - *Màu sắc thương hiệu*: Mã màu chính (Primary HEX) ➔ tự động suy luận màu accent và nền qua `PaletteContrastValidator`.
   - *Âm hưởng (Tone)*: Chuyên nghiệp (Professional), Đột phá (Bold), Tối giản (Minimalist).
2. **Soạn Thảo Cấu Trúc 3 Phần Tối Giản (Core 3-Section Wireframe)**:
   - **Hero Section (100vh)**: Tiêu đề H1 lớn, tagline sắc bén, các lớp chiều sâu (depth layers) chuyển động theo chuột, nút CTA với vầng sáng gradient tỏa tròn.
   - **Features Grid**: Lưới 3 cột (responsive: 2 cột ở 900px, 1 cột ở 580px) kèm icon SVG vector và hiệu ứng xuất hiện khi cuộn tới (ScrollTrigger reveal).
   - **Closing CTA Section**: Thông điệp chốt hạ mạnh mẽ, microcopy cam kết, nút hành động chính.
3. **Đóng Gói Single-File HTML Tiêu Chuẩn**:
   - Toàn bộ CSS đặt inline trong thẻ `<style>`.
   - Toàn bộ JavaScript logic đặt inline trong thẻ `<script>`.
   - Tài nguyên bên ngoài DUY NHẤT được phép: Google Fonts CDN và GSAP + ScrollTrigger CDN chính thức. Tuyệt đối không nhúng script tracking lạ.
4. **Kiểm Định & Xuất Bản Vào Sandbox**:
   - Ghi file vào đường dẫn sandbox cô lập:  
     `var/sandboxes/{workspace_id}/sites/{site_id}/out/index.html`
   - Lưu trữ bản snapshot qua capability:  
     `commercial.campaign_asset.write(asset_type="landing_page")`
5. **Kích Hoạt URL Preview Nội Bộ (Sandbox Preview)**:
   - Bật link xem trước an toàn trong sandbox để Founder trải nghiệm tương tác thực tế trước khi quyết định xuất bản lên Subdomain của Workspace.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Mã nguồn HTML được sinh ra và ghi vào thư mục Sandbox của Workspace.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Bản thiết kế phải đảm bảo tỷ lệ tương phản màu sắc chữ / nền $\ge 4.5:1$ (chuẩn WCAG AA) được tính toán bởi `PaletteContrastValidator`.
- Mã nguồn HTML phải có cấu trúc chuẩn W3C, không phát sinh lỗi Flash of Unstyled Content (FOUC).

## 7. Safe Fallback & Ranh Giới Cô Lập Bất Khả Xâm Phạm (Boundary Isolation)
- **Ranh giới cốt tử:**
  - Thư mục `landing/` ở gốc repository là Landing Page của chính nền tảng COSA SaaS.
  - Kỹ năng này và mọi subagent **tuyệt đối không được đọc, sửa, ghi đè hoặc import** tài nguyên từ `landing/`.
  - Mọi thao tác I/O chỉ được phép diễn ra trong thư mục Sandbox được phân bổ cụ thể cho Workspace: `var/sandboxes/{workspace_id}/sites/{site_id}/`.

## 8. Định Dạng Đầu Ra (Output Format)
```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Tên Sản Phẩm] — [Tagline]</title>
  <!-- Google Fonts & GSAP CDN -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
  <style>
    /* Inline CSS đạt chuẩn WCAG AA */
  </style>
</head>
<body>
  <!-- Hero (100vh), Features (3-Col), Closing CTA -->
  <script>
    // GSAP Entrance, Mouse Parallax & ScrollTrigger reveals
  </script>
</body>
</html>
```

## 9. Xử Lý Lỗi & Phòng Vệ Prompt Injection (Security & Edge Cases)
- **Phát hiện đường dẫn nhắm vào thư mục core hoặc `landing/`**: Dừng tiến trình ngay lập tức và ném lỗi an ninh.
- **Mã màu không đạt chuẩn tương phản**: Tự động kích hoạt `PaletteContrastValidator.derive_palette()` để cân chỉnh màu nền và màu chữ đảm bảo khả năng đọc.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: marketing/landing
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Triết lý Visual Premium single-file HTML, hiệu ứng GSAP 3D parallax, 4 câu hỏi định hướng
  changed:
    - Chuyển giao toàn bộ đầu ra vào môi trường Sandbox cô lập (var/sandboxes/...) thay vì ghi file tự do
    - Chuẩn hóa sang 10 mục hợp đồng tĩnh COSA
  added:
    - Ranh giới bất khả xâm phạm tuyệt đối bảo vệ thư mục landing/ gốc của COSA SaaS
    - Kiểm định tương phản WCAG tự động qua PaletteContrastValidator
  excluded:
    - Loại bỏ việc ghi file ra ngoài thư mục sandbox của workspace
```
