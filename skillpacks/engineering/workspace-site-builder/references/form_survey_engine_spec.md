# Interactive Form & Survey Engine Specification

Tài liệu đặc tả kiến trúc Module Form Thu Thập Thông Tin và Khảo Sát Tương Tác (Lead Qualification Wizard) dành cho **CTO Agent** khi triển khai trong Sandbox.

---

## 1. Mục Tiêu & Năng Lực Cốt Lõi

Module Form & Survey được thiết kế để thay thế các giải pháp bên thứ ba cồng kềnh (Typeform, Google Forms, WPForms), mang lại trải nghiệm mượt mà, tải nhanh và tích hợp trực tiếp vào hệ thống dữ liệu của Workspace:
1. **Thu thập thông tin khách hàng:** Tên, Email, Số điện thoại, Tên công ty, Nhu cầu.
2. **Khảo sát phân loại tiềm năng (Lead Qualification):** Trắc nghiệm đa bước, tự động tính điểm (Lead Score).
3. **Bảo mật tuyệt đối:** Ngăn chặn spam bot bằng Honeypot và Cloudflare Turnstile.
4. **Đồng bộ thời gian thực:** Lưu trữ kết quả và gửi thông báo tức thời qua Webhook/Email.

---

## 2. Cấu Trúc Khai Báo Khảo Sát (`survey-schema.json`)

Mỗi Form/Khảo sát được định nghĩa bằng cấu trúc JSON chuẩn hóa:

```json
{
  "id": "survey-lead-qualification",
  "title": "Khảo Sát Nhu Cầu Tự Động Hóa Doanh Nghiệp",
  "description": "Giúp chúng tôi hiểu rõ thách thức của bạn để tư vấn lộ trình phù hợp nhất.",
  "settings": {
    "showProgressBar": true,
    "allowBackNavigation": true,
    "submitButtonText": "Hoàn tất & Nhận Báo Cáo Miễn Phí",
    "security": {
      "enableHoneypot": true,
      "enableTurnstile": true
    }
  },
  "steps": [
    {
      "stepIndex": 1,
      "title": "Thông Tin Cơ Bản",
      "fields": [
        {
          "name": "fullName",
          "label": "Họ và tên của bạn",
          "type": "text",
          "placeholder": "Nguyễn Văn A",
          "required": true,
          "validation": { "minLength": 2 }
        },
        {
          "name": "email",
          "label": "Email công việc",
          "type": "email",
          "placeholder": "name@company.com",
          "required": true,
          "validation": { "format": "email" }
        },
        {
          "name": "phone",
          "label": "Số điện thoại liên hệ",
          "type": "tel",
          "placeholder": "0912 345 678",
          "required": true,
          "validation": { "pattern": "^(0|\\+84)[0-9]{9}$" }
        }
      ]
    },
    {
      "stepIndex": 2,
      "title": "Quy Mô Doanh Nghiệp",
      "fields": [
        {
          "name": "companySize",
          "label": "Quy mô nhân sự hiện tại của công ty bạn?",
          "type": "single-choice",
          "layout": "cards",
          "required": true,
          "options": [
            { "label": "Dưới 10 người", "value": "1-10", "score": 10 },
            { "label": "Từ 10 - 50 người", "value": "10-50", "score": 30 },
            { "label": "Từ 50 - 200 người", "value": "50-200", "score": 50 },
            { "label": "Trên 200 người", "value": "200+", "score": 80 }
          ]
        }
      ]
    },
    {
      "stepIndex": 3,
      "title": "Thách Thức Hiện Tại",
      "fields": [
        {
          "name": "painPoints",
          "label": "Những điểm nghẽn lớn nhất trong vận hành (chọn tối đa 3)?",
          "type": "multiple-choice",
          "maxSelections": 3,
          "required": true,
          "options": [
            { "label": "Xử lý đơn hàng chậm trễ", "value": "slow-order-processing" },
            { "label": "Tỷ lệ khách hàng rời bỏ cao", "value": "high-churn" },
            { "label": "Thiếu báo cáo dữ liệu tập trung", "value": "data-silo" },
            { "label": "Chi phí nhân sự phình to", "value": "high-overhead" }
          ]
        },
        {
          "name": "budget",
          "label": "Ngân sách dự kiến cho việc nâng cấp công nghệ?",
          "type": "single-choice",
          "required": true,
          "options": [
            { "label": "Dưới 20 triệu VNĐ", "value": "tier-1", "score": 10 },
            { "label": "20 - 50 triệu VNĐ", "value": "tier-2", "score": 30 },
            { "label": "Trên 50 triệu VNĐ", "value": "tier-3", "score": 60 }
          ]
        },
        {
          "name": "additionalNotes",
          "label": "Ghi chú thêm về nhu cầu của bạn (nếu có)",
          "type": "textarea",
          "required": false,
          "placeholder": "Chia sẻ chi tiết hơn..."
        }
      ]
    }
  ]
}
```

---

## 3. Các Loại Trường Dữ Liệu Hỗ Trợ (Supported Field Types)

| Loại trường | Mã loại | Mô tả hiển thị | Ràng buộc kiểm tra |
| :--- | :--- | :--- | :--- |
| **Văn bản đơn** | `text` | Ô nhập chuẩn | min/max length, regex |
| **Email** | `email` | Bàn phím email, kiểm tra cú pháp chuẩn RFC | Email format |
| **Điện thoại** | `tel` | Bàn phím số | Regex kiểm tra đầu số VN |
| **Chọn một** | `single-choice` | Dạng Radio buttons hoặc Thẻ bấm (Interactive Cards) | Bắt buộc chọn 1 |
| **Chọn nhiều** | `multiple-choice` | Dạng Checkbox hoặc Chips bấm | min/max lựa chọn |
| **Thang điểm** | `rating` / `nps` | Thang 5 sao hoặc NPS từ 0 đến 10 | Giá trị nguyên trong dải |
| **Văn bản dài** | `textarea` | Ô nhập nhiều dòng | max length (thường 1000 ký tự) |

---

## 4. Chấm Điểm Phân Loại Khách Hàng (Lead Scoring & Qualification)

Hệ thống tính điểm tự động tại backend khi nhận payload submit:
- **Công thức:** `Total Score = Sum(field_option.score)`.
- **Phân loại Tier khách hàng:**
  - **Hot Lead (Score >= 100):** Tự động gửi thông báo khẩn cấp qua Telegram/SMS cho đội ngũ Sales, gắn tag `HOT_PROSPECT`.
  - **Warm Lead (50 <= Score < 100):** Đưa vào chuỗi email chăm sóc tự động (Email Nurturing Sequence).
  - **Cold/Informational Lead (Score < 50):** Gửi tài liệu cẩm nang/ebook qua email tự động.

---

## 5. Cơ Chế Bảo Mật & Phòng Chống Spam (Anti-Spam Shield)

1. **Honeypot Field:**
   - Tạo một trường ẩn trong form: `<input type="text" name="_hp_company_website" style="display:none" tabIndex={-1} autoComplete="off" />`.
   - Nếu trường này có giá trị khi gửi lên server ➔ Xác định là spam bot tự động điền ➔ Loại bỏ payload và trả về phản hồi giả lập thành công (HTTP 200) để đánh lừa bot.
2. **Cloudflare Turnstile Captcha:**
   - Tích hợp widget Turnstile vô hình (Invisible Captcha) ở bước cuối.
   - Server kiểm tra token hợp lệ với Cloudflare API trước khi ghi nhận bản ghi.
3. **Rate Limiting:**
   - Giới hạn tối đa 5 lượt gửi/IP trong 10 phút.
