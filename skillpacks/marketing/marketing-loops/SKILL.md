---
name: marketing-marketing-loops
description: Hướng dẫn thiết lập và vận hành các vòng lặp tiếp thị định kỳ tự hành (SEO decay scan, ad fatigue refresh, churn watch) theo cấu trúc 9 thành phần giải phẫu và kiểm soát bởi LoopDoctor.
---

# Thiết Lập Vòng Lặp Tiếp Thị Định Kỳ (Recurring Marketing Loops)

## 1. Mục Tiêu (Objective)
Chuyển hóa các nhiệm vụ tiếp thị rời rạc, dễ bị quên lãng thành các **Vòng lặp tiếp thị có nhịp điệu (Marketing Loops)** tự động rà soát theo chu kỳ (hàng ngày, mỗi 3 ngày, hàng tuần), có cơ chế tự kiểm chứng (Self-Check), ghi nhớ trạng thái (Idempotency State) và điều kiện dừng tường minh (Stop / Bail-out Condition) tương thích với hệ thống `operations.loop-lifecycle`.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi cần theo dõi biến động thứ hạng từ khóa và sụt giảm truy cập định kỳ hàng tuần.
  - Khi cần kiểm tra mức độ hao mòn của mẫu quảng cáo trả phí (Ad Fatigue) mỗi 2-3 ngày.
  - Khi cần theo dõi các tín hiệu cảnh báo khách hàng có nguy cơ rời bỏ (Churn Watch) hàng ngày.
- **Khi nào KHÔNG dùng**:
  - Cho các ý tưởng tiếp thị dùng 1 lần duy nhất (One-off campaign, dùng `marketing.campaign-review`).
  - Khi chưa có hệ thống theo dõi dữ liệu hoặc lưu lượng truy cập quá nhỏ để tạo tín hiệu thống kê.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Kênh tiếp thị đã hoạt động và có nguồn phát tín hiệu (Google Search Console, Meta Ads, PostHog, Stripe Billing).
- Thẩm định qua công cụ thanh tra vòng lặp `LoopDoctor` để ngăn ngừa anti-patterns.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Chuẩn Hóa 9 Thành Phần Giải Phẫu Vòng Lặp (9-Part Anatomy)**:
   - *1. Check Cadence (Nhịp rà soát)*: Tần suất quét (Weekly / 3-Day / Daily) khớp với tốc độ thay đổi của tín hiệu.
   - *2. Acts When (Điều kiện kích hoạt)*: Điều kiện cần để thực sự hành động thay vì chỉ quét và bỏ qua.
   - *3. Purpose (Mục tiêu duy nhất)*: Một chỉ số hoặc kết quả kinh doanh duy nhất cần bảo vệ hoặc tăng trưởng.
   - *4. Skills Used (Kỹ năng phối hợp)*: Danh sách các skillpack được điều phối trong thân vòng lặp.
   - *5. Loop Body (Các bước thực thi)*: Chuỗi hành động tuần tự khi điều kiện kích hoạt thỏa mãn.
   - *6. Self-Check (Tự kiểm chứng)*: Xác minh độc lập trước khi hành động (tránh phản ứng quá đà với nhiễu dữ liệu).
   - *7. State / Idempotency (Trạng thái & Khử trùng lặp)*: Ghi nhớ lần chạy trước, cooldown window để không gửi cảnh báo lặp lại.
   - *8. Stop / Bail-out (Điều kiện dừng)*: Ngưỡng dừng khẩn cấp, bàn giao cho con người khi gặp lỗi bất thường.
   - *9. Output (Đầu ra)*: Artifact hoặc báo cáo được đẩy vào hộp thư phê duyệt.
2. **Khớp Nối Với 6 Trạng Thái Kết Thúc (6 Terminal States)**:
   - `SUCCESS`: Hoàn thành trọn vẹn và tạo artifact kết quả mới.
   - `NOOP`: Đã rà soát tín hiệu, mọi thứ bình thường, không cần hành động.
   - `BLOCKED`: Thiếu dữ liệu đầu vào hoặc mất quyền truy cập kết nối.
   - `NEED_APPROVAL`: Đã soạn xong đề xuất (vd: thay mẫu quảng cáo mới) chờ Founder phê duyệt.
   - `EXHAUSTED`: Vượt quá số lần thử lại tối đa.
   - `STAGNATED`: Tín hiệu không có tiến triển sau nhiều chu kỳ liên tiếp.
3. **Danh Mục 3 Vòng Lặp Tiếp Thị Điển Hình (Core Loop Catalog)**:
   - **Loop 1: Weekly SEO Decay Scan**: Quét hàng tuần các bài viết bị giảm vị trí $\ge 3$ bậc để kích hoạt quy trình làm mới nội dung.
   - **Loop 2: 3-Day Ad Fatigue Refresh**: Quét 3 ngày/lần CTR của các mẫu quảng cáo; nếu CTR giảm $> 25\%$ so với trung bình 7 ngày thì đề xuất biến thể copy mới.
   - **Loop 3: Daily Churn Signal Watch**: Quét hàng ngày các tài khoản giảm tần suất đăng nhập $> 50\%$ để đề xuất chuỗi email re-engagement.
4. **Kiểm Tra Qua LoopDoctor**:
   - Đảm bảo vòng lặp có bước Thẩm định độc lập (Independent Verifier) tách rời khỏi bước sinh nội dung.
   - Cấm các vòng lặp có nguy cơ chạy tự do vô hạn (Unbounded loop).

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Quy trình được thực thi thông qua hệ thống lập lịch và điều phối workflows của COSA.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Quyết định kích hoạt hành động phải dựa trên dữ liệu đo lường có ý nghĩa thống kê, không dựa trên biến động ngẫu nhiên trong ngày.
- Mọi vòng lặp phải lưu trữ `idempotency_key` và timestamp lần chạy gần nhất.

## 7. Safe Fallback & Giới Hạn Tự Trị (L1_PROPOSE Boundary)
- **Giới hạn tự trị**: Vòng lặp chỉ tự động thu thập tín hiệu và soạn thảo bản nháp đề xuất cải thiện.
- **Tuyệt đối KHÔNG**: Tự động tắt/bật chiến dịch quảng cáo thật, không tự ý trừ tiền tài khoản hoặc tự động gửi email hàng loạt cho khách hàng mà chưa qua cổng `NEED_APPROVAL`.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Nhật Ký Thực Thi Vòng Lặp Tiếp Thị (Marketing Loop Execution Log)

## 1. Thông Tin Vòng Lặp
- **Tên vòng lặp**: [Weekly SEO Decay / Ad Fatigue / Churn Watch]
- **Trạng thái kết thúc (Terminal State)**: [SUCCESS / NOOP / NEED_APPROVAL / BLOCKED]
- **Thời điểm rà soát**: [ISO Timestamp]

## 2. Kết Quả Tự Kiểm Chứng (Self-Check Findings)
- **Tín hiệu phát hiện**: [Mô tả tín hiệu số liệu]
- **Ngưỡng kích hoạt**: [Vượt ngưỡng / Chưa vượt ngưỡng]
- **Khử trùng lặp (Cooldown)**: [Hợp lệ / Đang trong thời gian chờ]

## 3. Đề Xuất Hành Động Chờ Duyệt (Pending Proposals)
- **Đề xuất**: [Mô tả hành động tiếp thị cụ thể]
- **Tài sản đính kèm**: [Đường dẫn artifact trong Sandbox hoặc kho tài nguyên]
```

## 9. Xử Lý Lỗi & Phòng Vệ Prompt Injection (Security & Edge Cases)
- **Phát hiện dữ liệu bất thường đột biến (Spike Anomaly)**: Nếu số liệu nhảy vọt $> 300\%$ trong 24h, tự động chuyển sang trạng thái `BLOCKED` để con người kiểm tra lỗi tracking trước khi hành động.
- **Ngăn chặn vòng lặp chạy liên tục không nghỉ**: Áp dụng thời gian chờ cưỡng bức (Cooldown Minimum 24h).

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/marketingskills
  commit: b1aaa3619e747f4a836c61e03084c4a531de1262
  skill: marketing-loops
  upstream_version: 1.2.0
  license: MIT
adaptation:
  kept:
    - Cấu trúc 9 thành phần giải phẫu vòng lặp và quy tắc khớp nhịp tín hiệu
  changed:
    - Tích hợp trực tiếp với 6 Terminal States của COSA Workflow Engine
    - Ráp nối với bộ thanh tra LoopDoctor
  added:
    - Danh mục 3 vòng lặp mẫu cho SEO, Ads và Churn Prevention
    - Cổng kiểm soát NEED_APPROVAL trước khi có bất kỳ tác động tài chính nào
  excluded:
    - Loại bỏ việc tự động chạy cron local hoặc tự đánh thức trong prompt
```
