# Site Architecture & JSON Block Specifications

Tài liệu đặc tả kiến trúc website đa trang và hệ thống khối giao diện (Composable Block-Based Engine) trong Sandbox dành cho **CTO Agent**. Kiến trúc này thay thế cho mô hình Monolith phức tạp của WordPress, mang lại hiệu năng cao (Next.js SSG/SSR), bảo mật cao và dễ dàng tùy biến bằng AI.

---

## 1. Cấu Trúc Tổng Quan Dữ Liệu Website (`site-config.json`)

Mọi website do CTO Agent chỉ đạo sinh ra đều tuân theo mô hình dữ liệu khai báo tập trung (Declarative Schema):

```json
{
  "$schema": "https://cosa.site/schemas/site-v1.json",
  "meta": {
    "siteName": "Acme Solutions",
    "tagline": "Tối ưu hóa chuyển đổi số cho doanh nghiệp vừa và nhỏ",
    "description": "Nền tảng giải pháp tự động hóa thông minh hàng đầu.",
    "favicon": "/favicon.ico",
    "primaryColor": "#2563eb",
    "accentColor": "#f59e0b",
    "fontFamily": "Inter, sans-serif"
  },
  "navigation": {
    "header": [
      { "label": "Trang chủ", "href": "/" },
      { "label": "Tính năng", "href": "/#features" },
      { "label": "Bảng giá", "href": "/pricing" },
      { "label": "Về chúng tôi", "href": "/about" },
      { "label": "Liên hệ", "href": "/contact" }
    ],
    "ctaButton": {
      "label": "Trải nghiệm ngay",
      "href": "/contact",
      "variant": "primary"
    }
  },
  "pages": [
    { "slug": "/", "title": "Trang chủ", "layout": "landing" },
    { "slug": "about", "title": "Về chúng tôi", "layout": "standard" },
    { "slug": "pricing", "title": "Bảng giá dịch vụ", "layout": "standard" },
    { "slug": "contact", "title": "Liên hệ & Tư vấn", "layout": "standard" }
  ]
}
```

---

## 2. Hệ Thống Khối Giao Diện (Block Component Schema)

Mỗi trang bao gồm một mảng danh sách các Block được sắp xếp tuần tự từ trên xuống dưới (`blocks: Block[]`).

### 2.1. Khối Hero (`HeroBlock`)
Khối đầu trang tạo ấn tượng thị giác mạnh mẽ và lời kêu gọi hành động (Call To Action):
```json
{
  "type": "hero",
  "id": "hero-main",
  "props": {
    "badge": "🚀 Phiên bản 2.0 đã ra mắt",
    "headline": "Tăng Tốc Doanh Thu Với Giải Pháp AI Thông Minh",
    "subheadline": "Tiết kiệm 70% thời gian vận hành và nâng cao trải nghiệm khách hàng ngay từ hôm nay.",
    "primaryCta": { "label": "Dùng thử miễn phí", "href": "/contact" },
    "secondaryCta": { "label": "Xem video demo", "href": "#demo" },
    "media": {
      "type": "image",
      "src": "/images/hero-dashboard.webp",
      "alt": "Bảng điều khiển trực quan"
    },
    "socialProof": {
      "rating": 4.9,
      "reviewCount": 1200,
      "note": "Tin dùng bởi hơn 1,000+ doanh nghiệp"
    }
  }
}
```

### 2.2. Khối Lưới Tính Năng (`FeatureGridBlock`)
Trưng bày các điểm mạnh, tính năng cốt lõi theo dạng thẻ (cards):
```json
{
  "type": "feature-grid",
  "id": "features-core",
  "props": {
    "title": "Tính Năng Vượt Trội",
    "subtitle": "Được xây dựng dựa trên công nghệ tiên tiến nhất để phục vụ doanh nghiệp bạn.",
    "columns": 3,
    "items": [
      {
        "icon": "Zap",
        "title": "Triển khai thần tốc",
        "description": "Sẵn sàng hoạt động chỉ trong 5 phút cấu hình mà không cần viết code."
      },
      {
        "icon": "ShieldCheck",
        "title": "Bảo mật đa lớp",
        "description": "Mã hóa dữ liệu đầu cuối, tuân thủ nghiêm ngặt chuẩn an toàn quốc tế."
      },
      {
        "icon": "BarChart3",
        "title": "Báo cáo chuyên sâu",
        "description": "Phân tích dữ liệu thời gian thực giúp ra quyết định kinh doanh chính xác."
      }
    ]
  }
}
```

### 2.3. Khối Bảng Giá Dịch Vụ (`PricingTableBlock`)
Bảng giá minh bạch hỗ trợ chọn chu kỳ thanh toán (Tháng/Năm) và nút mua hàng liên kết thẳng với Module E-Commerce:
```json
{
  "type": "pricing-table",
  "id": "pricing-section",
  "props": {
    "title": "Gói Dịch Vụ Linh Hoạt",
    "subtitle": "Chọn gói phù hợp với quy mô và mục tiêu phát triển của bạn.",
    "tiers": [
      {
        "id": "tier-starter",
        "name": "Khởi Nghiệp",
        "priceMonthly": 490000,
        "priceAnnually": 4900000,
        "description": "Dành cho cá nhân và nhóm nhỏ mới bắt đầu.",
        "features": ["3 Dự án hoạt động", "1,000 Leads/tháng", "Hỗ trợ email tiêu chuẩn"],
        "isPopular": false,
        "cta": { "label": "Bắt đầu ngay", "productId": "prod-starter" }
      },
      {
        "id": "tier-pro",
        "name": "Chuyên Nghiệp",
        "priceMonthly": 990000,
        "priceAnnually": 9900000,
        "description": "Dành cho doanh nghiệp đang tăng trưởng nhanh.",
        "features": ["Không giới hạn dự án", "10,000 Leads/tháng", "Hỗ trợ ưu tiên 24/7", "Tích hợp API riêng"],
        "isPopular": true,
        "cta": { "label": "Nâng cấp Pro", "productId": "prod-pro" }
      }
    ]
  }
}
```

### 2.4. Khối Đánh Giá Của Khách Hàng (`TestimonialBlock`)
Gia tăng niềm tin (Social Proof) cho khách hàng tiềm năng:
```json
{
  "type": "testimonials",
  "id": "testimonials-section",
  "props": {
    "title": "Khách Hàng Nói Gì Về Chúng Tôi",
    "items": [
      {
        "quote": "Sản phẩm đã giúp chúng tôi tiết kiệm hơn 30 giờ làm việc thủ công mỗi tuần.",
        "author": "Nguyễn Văn A",
        "role": "CEO, TechViet JSC",
        "avatar": "/images/avatar-1.webp"
      }
    ]
  }
}
```

### 2.5. Khối Câu Hỏi Thường Gặp (`FAQBlock`)
Accordion mở rộng câu hỏi đáp giúp giảm tải hỗ trợ kỹ thuật:
```json
{
  "type": "faq",
  "id": "faq-section",
  "props": {
    "title": "Câu Hỏi Thường Gặp",
    "items": [
      {
        "question": "Tôi có thể hủy gói dịch vụ bất kỳ lúc nào không?",
        "answer": "Hoàn toàn có thể. Bạn có thể hủy gói dịch vụ ngay trong trang quản lý tài khoản mà không phát sinh thêm bất kỳ chi phí nào."
      }
    ]
  }
}
```

---

## 3. Quy Chuẩn Tối Ưu SEO & Hiệu Năng (SEO & Core Web Vitals)

Để đảm bảo trang web đạt điểm Lighthouse 95+ và chuẩn SEO Google:

1. **Heading Hierarchy Chuẩn:**
   - Mỗi trang bắt buộc duy nhất 1 thẻ `<h1>` (nằm trong Hero Block).
   - Các khối con sử dụng tuần tự `<h2>`, `<h3>`.
2. **Metadata & OpenGraph Đầy Đủ:**
   - Khai báo thẻ Canonical URL, OpenGraph Image (`1200x630px`), Twitter Card.
   - Tự động sinh `sitemap.xml` và `robots.txt` lúc build.
3. **Structured Data (JSON-LD):**
   - Tự động chèn thẻ `schema.org` kiểu `Organization`, `WebSite`, `Product`, `FAQPage`.
4. **Hình ảnh Tối Ưu:**
   - Toàn bộ hình ảnh chuyển đổi sang định dạng `.webp` hoặc `.avif`, chỉ định rõ `width`, `height` và `loading="lazy"`.
