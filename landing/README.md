# COSA OS Landing Page (Next.js 16.3+ App Router & Turbopack)

Trang đích (Landing Page) chính thức của **COSA OS (Javis SaaS)** — Hệ Điều Hành Doanh Nghiệp Tự Trị AI Đa Tác Vụ.

## 🚀 Công Nghệ Sử Dụng
- **Next.js 16.3+ (Turbopack, App Router)** với React 19 & TypeScript
- **Tailwind CSS 3.4+** với bảng màu Stark Cyberpunk Dark & Glassmorphism
- **Lucide Icons**
- **Framer Motion** cho các hiệu ứng chuyển động mượt mà
- **Tối ưu SEO**: Đầy đủ OpenGraph, Twitter Cards, Semantic HTML5, Metadata

## 📦 Cấu Trúc Các Phân Hệ (Sections)
1. `Navbar`: Header cố định với hiệu ứng Blur Glassmorphic, trạng thái live của hệ thống và CTA.
2. `HeroSection`: Holographic Terminal mô phỏng luồng AI Worker, RAG memory và điều phối công ty.
3. `SocialProofBar`: Các đối tác công nghệ hạ tầng (LiveKit, PostgreSQL pgvector, MinIO, Hostinger VPS MCP, DeepSeek, OpenRouter, DSPy).
4. `LivePlayground`: Trải nghiệm tương tác đa kịch bản doanh nghiệp (Chiến lược OKR, Tạo Landing CRM, Thẩm định Pháp lý).
5. `BentoFeatures`: 5 trụ cột kiến trúc (Autonomous AI Workforce, LiveKit Realtime Voice, Enterprise Vault RAG, Company Runtime OKRs, Modular Landing & CRM).
6. `VoiceHologramPreview`: Trực quan hóa âm thanh 3D thời gian thực với trợ lý điều hành giọng nói.
7. `RoiCalculator`: Bộ tính toán ROI và số giờ làm việc tiết kiệm theo quy mô nhân sự.
8. `SecurityArchitecture`: Kiến trúc bảo mật On-Premise, Zero Data Retention, Snowflake 64-bit ID.
9. `PricingSection`: Bảng giá minh bạch với toggle thanh toán theo tháng / năm.
10. `TestimonialsSection`: Đánh giá từ các Founder và Giám đốc điều hành.
11. `FaqSection`: Giải đáp câu hỏi thường gặp về kỹ thuật và triển khai.
12. `LeadFormSection` & `LeadCaptureModal`: Thu thập thông tin khách hàng tiềm năng, kết nối trực tiếp với CRM.

## 🛠️ Hướng Dẫn Chạy Cục Bộ (Local Development)

```bash
# Cài đặt thư viện
npm install

# Khởi chạy máy chủ phát triển
npm run dev

# Build bản Production
npm run build

# Chạy bản Production
npm run start
```

## 🌐 Triển Khai (Deployment)
- **Hostinger VPS**: Sử dụng Dockerfile / Docker Compose thông qua MCP Server của COSA.
- **Vercel / Cloudflare Pages**: Triển khai tự động 1-click qua GitHub integration.
