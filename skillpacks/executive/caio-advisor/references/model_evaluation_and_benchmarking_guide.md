# Model Evaluation, Benchmarking & Cost Governance Guide

> **Tài liệu tham chiếu chuyên sâu dành cho:** CAIO Advisor & AI Architects  
> **Nguyên tắc cốt lõi:** Đánh giá chất lượng mô hình (Evals), Phân tầng mô hình tối ưu chi phí, Kiểm soát Token Burn Rate theo tuần.

---

## 1. Khung Đánh Giá Năng Lực Mô Hình AI (Model Evals Framework)

CAIO Advisor không bao giờ chọn mô hình dựa trên sự cường điệu (hype) của thị trường. Mỗi mô hình được đưa vào hạm đội Agent phải được benchmark theo 4 trục:

1. **Độ Chính Xác Nhiệm Vụ (Task Accuracy \%):** Tỷ lệ sinh ra kết quả JSON hợp lệ và tuân thủ chặt chẽ schema yêu cầu.
2. **Tỷ Lệ Ảo Giác (Hallucination Rate \%):** Tỷ lệ sinh ra thông tin bịa đặt không có trong context nguồn (Mục tiêu: $< 1.0\%$).
3. **Chi Phí Trên Đơn Vị Công Việc (Cost per Work Unit):**
   $$\text{Cost} = \frac{\text{Total Tokens (Input + Output)}}{1,000,000} \times \text{Đơn Giá Mô Hình / 1M Tokens}$$
4. **Độ Trễ Phản Hồi (Latency p95):** Thời gian phản hồi ở phân vị 95 không được vượt quá 10 giây đối với các luồng tương tác trực tiếp.

---

## 2. Chiến Lược Phân Tầng Mô Hình 3 Cấp Độ (3-Tier Model Routing)

Để tối ưu hóa chi phí mà vẫn đảm bảo độ thông minh vượt trội:

```
┌────────────────────────────────────────────────────────────────────────┐
│ CẤP 1: FRONTIER REASONING MODELS (Claude 3.5 Sonnet / GPT-4o)          │
│ • Dành riêng cho: Phản biện chiến lược HĐQT, CEO/CTO framing,          │
│   tổng hợp bất đồng phức tạp, phân tích kiến trúc hệ thống.            │
├────────────────────────────────────────────────────────────────────────┤
│ CẤP 2: FAST SPECIALIZED SLMs (Claude 3.5 Haiku / Llama-3-8B)           │
│ • Dành cho: Phân loại email, trích xuất thực thể, tóm tắt ticket,      │
│   kiểm tra chính tả, tạo bản nháp ban đầu. (Chi phí = 1/10 Cấp 1)      │
├────────────────────────────────────────────────────────────────────────┤
│ CẤP 3: MÃ NGUỒN XÁC ĐỊNH (Deterministic Python Code / RegEx)           │
│ • Dành cho: Tính toán số học (Runway, CAC, LTV), kiểm tra quyền IAM,   │
│   lọc từ khóa sự kiện. (Chi phí = $0 token, độ trễ = 0ms)             │
└────────────────────────────────────────────────────────────────────────┘
```

> **Quy Tắc Vàng:** Không bao giờ dùng Frontier Model đắt đỏ để làm các phép tính số học mà một hàm Python 3 dòng có thể giải quyết nhanh hơn và chính xác 100%.
