---
name: growth-plg-activation
description: Chiến lược tăng trưởng dựa trên sản phẩm (PLG), phương pháp tìm kiếm Activation Event (Aha Moment), chẩn đoán điểm rơi phễu Onboarding 4 tầng, thiết kế Viral Loop và chuyển đổi Freemium.
---

# Tăng Trưởng Dẫn Dắt Bởi Sản Phẩm (PLG Activation & Onboarding)

## 1. Mục đích & Giới hạn Quyền hạn
Cung cấp khung phương pháp luận chuyển hóa sản phẩm thành cỗ máy tăng trưởng tự thân (Product-Led Growth):
- Đánh giá mức độ sẵn sàng cho mô hình PLG so với Sales-Led Growth (SLG).
- Định danh chính xác **Hành động Kích hoạt (Activation Event / Aha Moment)** có tương quan cao nhất với tỷ lệ giữ chân ngày thứ 30.
- Chẩn đoán điểm nghẽn trong phễu trải nghiệm đầu tiên (Time-to-First-Value).
- Thiết kế vòng lặp lan truyền (Viral Loops) và tối ưu hóa chuyển đổi từ miễn phí sang trả phí (Freemium-to-Paid Conversion).

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đề xuất thiết kế luồng onboarding, bảng chỉ số và giả thuyết thử nghiệm (L1_PROPOSE). Tuyệt đối không tự ý thay đổi chính sách giá trên cổng thanh toán, không tự động gửi email hàng loạt ngoài luồng.

## 2. Triggers
- Kích hoạt khi công ty muốn xây dựng luồng tự phục vụ (Self-serve) hoặc mở gói trải nghiệm miễn phí (Free trial / Freemium).
- Kích hoạt khi tỷ lệ đăng ký tài khoản cao nhưng tỷ lệ người dùng quay lại sau 7 ngày hoặc 30 ngày quá thấp.
- Kích hoạt khi cần thiết kế thử nghiệm tăng trưởng nhằm rút ngắn thời gian đạt giá trị (Time-to-Value).

## 3. Anti-triggers & PLG Anti-Patterns Cần Tránh
- **Chặn PLG Theater:** Mở gói dùng thử nhưng không đo lường được hành động kích hoạt. Bạn chỉ đang có một gói miễn phí gây tốn chi phí hạ tầng, chứ không phải đang làm PLG.
- **Chặn Premature PLG:** Cố gắng triển khai tự phục vụ khi sản phẩm quá phức tạp, bắt buộc phải có chuyên viên cấu hình hoặc di chuyển dữ liệu lớn.
- **Chặn Viral Delusion:** Ảo tưởng mô hình lan truyền tự nhiên đạt K > 1. Hầu hết các sản phẩm SaaS thành công chỉ đạt K từ 0.3 - 0.7 (Viral-assisted giúp giảm chi phí CAC).
- **Chặn Vanity Activation:** Định nghĩa kích hoạt là "hoàn thành wizard giới thiệu" thay vì hành động thực tế mang lại giá trị.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## 4. Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `target_icp`: Chân dung đối tượng sử dụng trực tiếp.

## 5. Evidence Rules
- Mọi chẩn đoán phễu Onboarding phải dựa trên dữ liệu tỷ lệ chuyển đổi thực tế giữa từng bước.
- Thử nghiệm tăng trưởng bắt buộc phải có **Guardrail Metric** (chỉ số chặn: ví dụ tăng tỷ lệ đăng ký nhưng không làm tăng tỷ lệ churn).

## 6. Quy Trình Vận Hành & Phương Pháp Luận

### 6.1. Ma Trận Đánh Giá Fit: PLG vs SLG
- **Phù hợp PLG mạnh:** Người dùng cuối tự quyết định thử nghiệm, giá khởi điểm < $500/tháng, Time-to-Value tính bằng phút đến giờ, cấu hình đơn giản.
- **Phù hợp SLG mạnh:** Cần hội đồng mua hàng phê duyệt, hợp đồng ACV > $50k, triển khai kéo dài nhiều tuần, yêu cầu kiểm duyệt an ninh bảo mật phức tạp.
- **Mô hình Hybrid:** Dùng PLG tạo phễu người dùng và nhận biết, dùng SLG để chốt hợp đồng doanh nghiệp lớn.

### 6.2. Bốn Bước Tìm Kiếm Activation Event (Aha Moment)
1. Xác định tập khách hàng còn hoạt động tích cực ở ngày thứ 30.
2. So sánh hành vi trong phiên đầu tiên của nhóm này so với nhóm rời bỏ (churned).
3. Tìm hành động có hệ số tương quan cao nhất với việc giữ chân dài hạn.
4. Chọn hành động đó làm **Activation Event**.
*Ví dụ kinh điển:*
- Slack: Đội ngũ gửi đủ 2.000 tin nhắn.
- Dropbox: Kéo thả 1 tệp tin vào 1 thư mục trên 1 thiết bị.

$$\text{Activation Rate} = \frac{\text{Số user chạm Activation Event}}{\text{Tổng số lượt đăng ký}} \times 100\%$$

*Benchmark:* Free trial: 25-40%; Freemium: 15-30%; Reverse trial: 35-50%.

### 6.3. Chẩn Đoán Điểm Rơi Phễu Onboarding 4 Tầng
| Tầng Phễu | Tín hiệu điểm nghẽn | Bài thuốc xử lý |
|---|---|---|
| **Đăng ký ➔ Thao tác đầu tiên** | Rơi rụng > 60% | Giảm ma sát đăng ký: bỏ bớt trường nhập, hỗ trợ SSO, hoãn điền profile. |
| **Thao tác đầu tiên ➔ Activation** | Rơi rụng > 70% | Rút ngắn đường đến Aha Moment: dữ liệu mẫu sẵn có, templates, mẫu điền sẵn. |
| **Activation ➔ Quay lại Ngày 7** | Rơi rụng > 50% | Kích hoạt lại qua trigger có ngữ cảnh: email thông báo tác vụ dang dở, tóm tắt tuần. |
| **Ngày 7 ➔ Thói quen Ngày 30** | Rơi rụng > 40% | Xây dựng vòng lặp giá trị định kỳ, tính năng cộng tác nhóm, báo cáo tiến độ. |

### 6.4. Thiết Kế Vòng Lặp Lan Truyền & Hệ Số K-Factor
Vòng lặp lan truyền gồm 4 thành phần: `Trigger (Động lực chia sẻ) ➔ Action (Gửi lời mời/nội dung) ➔ Conversion (Người nhận đăng ký) ➔ Value Delivery (Người mới nhận giá trị)`.

$$K = \text{Số lời mời trung bình gửi trên mỗi user} \times \text{Tỷ lệ chuyển đổi của lời mời}$$

Sử dụng trực tiếp analyzer `calculate_viral_k_factor()`.

### 6.5. Bảng Điều Khiển Tăng Trưởng Hàng Tuần (Growth Dashboard 6 Chỉ Số)
1. **Signup ➔ Activation Rate:** Đo lường hiệu quả onboarding.
2. **Activation ➔ Paid Conversion:** Hiệu quả thương mại hóa gói tự phục vụ.
3. **Time-to-Value (TTFV):** Thời gian trung vị từ đăng ký đến khi chạm Aha Moment.
4. **Viral K-factor:** Tiềm năng giảm chi phí CAC nhờ lan truyền tự nhiên.
5. **Expansion Rate:** Tỷ lệ doanh thu mở rộng từ nhóm khách hàng tự phục vụ.
6. **Logo Retention:** Tỷ lệ duy trì tài khoản hàng tháng.

## 7. Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## 8. Output Format
- **plg-strategy-brief**: Bản chiến lược tăng trưởng PLG gồm: Định nghĩa Activation Event, Bản đồ phễu Onboarding và điểm rơi, Thiết kế Viral Loop, Danh mục thử nghiệm tăng trưởng chấm điểm theo ICE (`score_growth_experiment_ice()`).

## 9. Fallback & Handoff
- Khi chưa có dữ liệu hành vi người dùng, fallback sang phỏng vấn 5-10 người dùng mới trong tuần đầu tiên để xác định rào cản thao tác lớn nhất.

## 10. Eval Notes
- Suite: `evals/growth/plg-activation.yaml`
