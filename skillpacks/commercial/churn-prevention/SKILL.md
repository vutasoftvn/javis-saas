---
name: commercial-churn-prevention
description: Hướng dẫn phân tích tỷ lệ giữ chân khách hàng (Cohort Retention, NRR), phát hiện tín hiệu cảnh báo sớm nguy cơ rời bỏ và cẩm nang can thiệp chủ động.
---

# Quy Trình Phòng Ngừa Rời Bỏ & Tối Ưu Giữ Chân Khách Hàng (Churn Prevention & Retention)

## 1. Mục Tiêu (Objective)
Xây dựng khung phân tích tỷ lệ giữ chân khách hàng (Retention Cohort, Logo Churn, Net Revenue Retention - NRR), thiết lập hệ thống cảnh báo sớm cho các tài khoản có nguy cơ rời bỏ (At-Risk Signals), và triển khai cẩm nang can thiệp chủ động (Intervention Playbook) nhằm bảo vệ doanh thu định kỳ.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi cần phân tích sức khỏe tài khoản khách hàng (Customer Health Score) và tỷ lệ giữ chân theo từng nhóm thuần tập (Cohorts).
  - Khi phát hiện các tài khoản sụt giảm mức độ sử dụng hoặc có tín hiệu cảnh báo nguy cơ hủy dịch vụ.
  - Khi thực hiện phân tích nguyên nhân gốc rễ sau khi khách hàng rời bỏ (Churn Post-Mortem).
- **Khi nào KHÔNG dùng**:
  - Khi cần thiết kế lại toàn bộ mô hình bảng giá hoặc gói dịch vụ (dùng `commercial.pricing`).
  - Khi quản lý quy trình đón tiếp và hướng dẫn người dùng mới (Onboarding trong `marketing.copywriting`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Dữ liệu sử dụng sản phẩm (tần suất đăng nhập, tính năng kích hoạt, số người dùng hoạt động).
- Lịch sử thanh toán, gia hạn hợp đồng và các phản hồi/khiếu nại từ bộ phận chăm sóc khách hàng (CS/Support).

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Phân Tích Chỉ Số Giữ Chân Khách Hàng (Retention Metrics Framework)**:
   - *Logo Retention*: Tỷ lệ số lượng khách hàng/tài khoản tiếp tục duy trì đăng ký sau chu kỳ (Tháng/Quý/Năm).
   - *Gross Revenue Retention (GRR)*: Tỷ lệ doanh thu giữ lại từ tập khách hàng hiện tại (loại trừ doanh thu mở rộng/expansion), tối ưu >= 85-90%.
   - *Net Revenue Retention (NRR)*: Tỷ lệ doanh thu ròng tính cả mở rộng, nâng cấp và sụt giảm, mục tiêu chuẩn SaaS B2B >= 105-120%.
   - *Cohort Analysis*: Theo dõi đường cong giữ chân theo từng tháng gia nhập để phát hiện điểm gãy sản phẩm.
2. **Nhận Diện Tín Hiệu Cảnh Báo Sớm Nguy Cơ Rời Bỏ (At-Risk Early Warning Signals)**:
   - *Tín hiệu hành vi sản phẩm*: Mức sử dụng giảm > 40% trong 30 ngày, người dùng quản trị chính (Admin/Champion) ngừng đăng nhập > 14 ngày, không kích hoạt tính năng cốt lõi.
   - *Tín hiệu hỗ trợ & dịch vụ*: Xuất hiện vé hỗ trợ nghiêm trọng chưa xử lý thỏa đáng, điểm đánh giá CSAT/NPS thấp (<= 6/10), liên hệ hỏi về cách xuất dữ liệu hoặc hủy tài khoản.
   - *Tín hiệu tổ chức & tài chính*: Người bảo trợ sản phẩm (Champion) rời công ty, thanh toán thẻ tín dụng thất bại nhiều lần (Involuntary Churn), doanh nghiệp tái cơ cấu/cắt giảm nhân sự.
3. **Triển Khai Cẩm Nang Can Thiệp Chủ Động (Intervention Playbook)**:
   - *Mức độ 1 (Vàng - Mức dùng giảm nhẹ)*: Tự động gửi email gợi ý tính năng hữu ích, chia sẻ mẹo tối ưu hóa quy trình làm việc.
   - *Mức độ 2 (Cam - Champion ngừng hoạt động / Vé khiếu nại)*: Chuyên viên CS chủ động liên hệ 1-1 để rà soát mục tiêu ban đầu (Executive Business Review) và hỗ trợ đào tạo lại người dùng mới.
   - *Mức độ 3 (Đỏ - Yêu cầu hủy / Thanh toán thất bại)*: Đưa ra phương án tạm dừng gói (Pause account), hỗ trợ chuyển đổi sang gói thấp hơn (Downgrade option), hoặc kích hoạt ưu đãi giữ chân có điều kiện từ cấp quản lý.
4. **Phân Tích Hậu Rời Bỏ (Churn Post-Mortem & Feedback Loop)**:
   - Thực hiện phỏng vấn ngắn hoặc khảo sát lý do hủy (Price, Missing Feature, Competitor, Champion Left, Business Closed).
   - Phân loại rõ: Churn có thể cứu vãn (Preventable Churn) vs Churn bất khả kháng (Non-preventable Churn).
   - Chuyển giao phản hồi tính năng thiếu hụt sang lộ trình sản phẩm.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Đầu ra là tài liệu phân tích sức khỏe khách hàng và cẩm nang can thiệp.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mọi đánh giá nguy cơ rời bỏ phải dẫn chứng dữ liệu hành vi thực tế (số ngày không hoạt động, số vé hỗ trợ mở, số lần thất bại thanh toán), không suy đoán cảm tính.
- Các lý do rời bỏ phải được trích dẫn trực tiếp từ trao đổi với khách hàng.

## 7. Safe Fallback & Giới Hạn Nghiêm Ngặt (Non-Mutating Policy)
- **Giới hạn nghiêm ngặt**: Skillpack này CHỈ đưa ra phân tích, cảnh báo nguy cơ và kịch bản can thiệp.
- **Tuyệt đối KHÔNG**: Tự ý hủy hợp đồng, xóa tài khoản người dùng khỏi database, hoàn tiền (refund) hay thay đổi gói dịch vụ mà không có sự phê duyệt của con người.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Kế Hoạch Phòng Ngừa Rời Bỏ & Đánh Giá Sức Khỏe Khách Hàng (Retention Playbook)

## 1. Tổng Quan Chỉ Số Giữ Chân (Retention Overview)
- **Net Revenue Retention (NRR)**: [Tỷ lệ %] - `[Healthy / Warning]`
- **Gross Revenue Retention (GRR)**: [Tỷ lệ %] - `[Healthy / Warning]`
- **Điểm gãy chính trên biểu đồ Cohort**: [Tháng 1 / Tháng 3 / Kỳ gia hạn]

## 2. Danh Sách Tài Khoản Có Nguy Cơ (At-Risk Accounts)
| Tên Tài Khoản | Mức Độ Rủi Ro (Đỏ/Cam/Vàng) | Tín Hiệu Cảnh Báo Chính | Giá Trị Hợp Đồng (ARR/MRR) |
| --- | --- | --- | --- |
| [Công ty A] | Đỏ | Mức dùng giảm 60%, Champion rời đi | [$X,000] |
| [Công ty B] | Cam | 3 vé khiếu nại chưa xử lý dứt điểm | [$Y,000] |

## 3. Kịch Bản Can Thiệp Đề Xuất (Actionable Intervention)
- **Hành động khẩn cấp cho Tài khoản Đỏ**: [Đặt lịch họp trực tiếp 1-1, đề xuất giải pháp tháo gỡ]
- **Hành động cho Tài khoản Cam**: [Gửi tài liệu đào tạo lại, kiểm tra tiến độ xử lý khiếu nại]

## 4. Bài Học Rút Ra Từ Churn Post-Mortem
- [Các khoảng trống tính năng hoặc trải nghiệm cần khắc phục]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Khách hàng cương quyết muốn hủy**: Tôn trọng quyết định của khách hàng, đảm bảo quy trình xuất dữ liệu mượt mà để giữ mối quan hệ tốt đẹp cho cơ hội tái hợp tác trong tương lai.
- **Rời bỏ do lỗi thanh toán tự động (Involuntary Churn)**: Kích hoạt chuỗi email nhắc nhở cập nhật thẻ thông minh (Dunning Email Sequence) thay vì khóa tài khoản ngay lập tức.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/marketingskills
  commit: b1aaa3619e747f4a836c61e03084c4a531de1262
  skill: churn-prevention
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Khung phân tích Retention Cohorts, Phân loại tín hiệu At-risk, Kịch bản can thiệp CS
  changed:
    - Chuẩn hóa thuật ngữ COSA
    - Thêm cấu trúc 10 mục bắt buộc và định dạng markdown tiếng Việt
  added:
    - Hệ thống phân loại 3 mức độ rủi ro (Vàng/Cam/Đỏ)
    - Quy trình phân tích Churn Post-Mortem và phân tách Preventable vs Non-preventable
    - Giới hạn nghiêm ngặt không tự ý hủy gói hoặc hoàn tiền
  excluded:
    - Tự động gọi API hủy gói trên cổng thanh toán
```
