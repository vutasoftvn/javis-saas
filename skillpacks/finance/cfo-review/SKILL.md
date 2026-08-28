---
name: finance-cfo-review
description: Hướng dẫn đánh giá tài chính doanh nghiệp (CFO Review), đối soát dòng tiền, tính toán burn rate, lập kịch bản runway và phát hiện bất thường tài chính.
---

# Quy Trình Đánh Giá Tài Chính & Dự Phóng Dòng Tiền (CFO Review & Runway Planning)

## 1. Mục Tiêu (Objective)
Cung cấp khung đánh giá sức khỏe tài chính định kỳ (CFO Review), hướng dẫn đối soát số dư tiền mặt (Cash Reconciliation), tính toán tốc độ tiêu hao vốn (Net Burn Rate), dự phóng thời gian tồn tại (Runway Scenario Planning), và phát hiện sớm các khoản chi bất thường. Quy trình chi tiết được tài liệu hóa tại `docs/runbooks/cfo-review.md`.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Đánh giá tài chính định kỳ hàng tuần / hàng tháng cho ban lãnh đạo.
  - Lập kịch bản dự phóng dòng tiền (Base case, Best case, Worst case) khi chuẩn bị gọi vốn hoặc tái cơ cấu chi phí.
  - Phân tích biến động chi phí định kỳ và phát hiện các khoản thất thoát, trùng lặp.
- **Khi nào KHÔNG dùng**:
  - Khi cần thực thi lệnh chi trả (payout) tự động (cần capability `finance.payout.execute` có sự phê duyệt qua cổng approval).
  - Khi cần ghi nhận giao dịch sổ cái chi tiết (dùng `finance.transaction.record`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Số dư tiền mặt thực tế tại các tài khoản ngân hàng và cổng thanh toán (được cung cấp ở mức số liệu tổng hợp).
- Báo cáo doanh thu thu về (Cash Inflow) và tổng chi phí vận hành (Cash Outflow) theo tháng.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Đối Soát Số Dư Tiền Mặt (Cash Reconciliation)**:
   - Tổng hợp số dư tiền mặt khả dụng (Available Cash Balance) từ tất cả các tài khoản doanh nghiệp.
   - Đối chiếu số dư đầu kỳ + Dòng tiền vào - Dòng tiền ra = Số dư cuối kỳ.
2. **Tính Toán Tốc Độ Tiêu Hao Vốn (Gross & Net Burn Rate)**:
   - *Gross Burn*: Tổng chi phí tiền mặt thực tế chi ra trong tháng (Lương, Server, Marketing, Văn phòng, Thuế, Phí dịch vụ).
   - *Net Burn*: Gross Burn - Doanh thu tiền mặt thực thu vào trong tháng.
3. **Lập Kịch Bản Dự Phóng Thời Gian Tồn Tại (Runway Scenario Planning)**:
   - *Runway (tháng)* = Số dư tiền mặt khả dụng / Net Burn trung bình 3 tháng gần nhất.
   - Xây dựng 3 kịch bản:
     - **Base Case (Kịch bản cơ sở)**: Giữ nguyên tốc độ tăng trưởng doanh thu và chi phí hiện tại.
     - **Worst Case (Kịch bản xấu nhất - Zero Growth)**: Doanh thu đi ngang hoặc giảm 20%, chi phí giữ nguyên.
     - **Best Case (Kịch bản tối ưu)**: Tăng trưởng doanh thu đạt kế hoạch đề ra.
4. **Kiểm Tra Các Điểm Bất Thường Tài Chính (Financial Anomaly Checklist)**:
   - Kiểm tra các khoản chi phí SaaS/Server tăng đột biến (> 25% so với tháng trước).
   - Phát hiện các khoản đăng ký dịch vụ bị trùng lặp hoặc không còn sử dụng.
   - Kiểm tra các khoản công nợ phải thu quá hạn (Accounts Receivable Aging > 60 ngày).
5. **Đề Xuất Hành Động Can Thiệp Kịp Thời (Corrective Actions)**:
   - Nếu Runway < 6 tháng: Bắt buộc kích hoạt chế độ thắt chặt chi tiêu (Cost Containment Playbook) và lập kế hoạch gọi vốn khẩn cấp hoặc cắt giảm chi phí không thiết yếu.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Mọi phân tích được thực hiện dựa trên dữ liệu báo cáo tài chính tổng hợp được cung cấp.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mọi con số trong báo cáo CFO Review phải dựa trên số liệu thực tế của các báo cáo ngân hàng và hệ thống kế toán đã chốt sổ.
- Phải nêu rõ giả định về tốc độ tăng trưởng và chi phí trong các kịch bản dự phóng Runway.

## 7. Safe Fallback & Bảo Mật Dữ Liệu Nghiêm Ngặt (Zero Raw Banking Data in Prompts)
- **Quy tắc bảo mật tối thượng (Security Gate)**:
  - **TUYỆT ĐỐI KHÔNG**: Nhập thông tin đăng nhập ngân hàng, mật khẩu, mã OTP, số tài khoản chi tiết kèm mã định danh cá nhân (PII), hoặc sao kê thô chưa ẩn danh vào prompt của LLM.
  - Chỉ làm việc với các bảng số liệu đã được tổng hợp ở mức danh mục (Aggregated Category Totals).
- **Safe Fallback**: Khi không có dữ liệu chi tiết, agent xuất bảng mẫu tính toán Runway và danh mục kiểm tra để ban lãnh đạo tự điền số liệu nội bộ.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Tổng Hợp Tài Chính & Dự Phóng Runway (CFO Review Brief)

## 1. Tình Hình Dòng Tiền & Tốc Độ Tiêu Hao Vốn (Cash & Burn)
- **Số dư tiền mặt khả dụng**: [$X,000,000] (Tính đến ngày YYYY-MM-DD)
- **Gross Burn trung bình**: [$A,000 / tháng]
- **Doanh thu thực thu**: [$B,000 / tháng]
- **Net Burn trung bình**: [$C,000 / tháng]

## 2. Dự Phóng Thời Gian Tồn Tại (Runway Scenarios)
| Kịch Bản (Scenario) | Giả Định Tăng Trưởng | Net Burn Dự Kiến | Thời Gian Tồn Tại (Runway) | Trạng Thái Rủi Ro |
| --- | --- | --- | --- | --- |
| **Base Case** | Tăng trưởng 10%/tháng | [$X/tháng] | **14 Tháng** | An toàn (> 12 tháng) |
| **Worst Case** | Tăng trưởng 0% | [$Y/tháng] | **9 Tháng** | Cảnh báo (6-12 tháng) |
| **Emergency Case** | Doanh thu giảm 20% | [$Z/tháng] | **6 Tháng** | Nguy hiểm (<= 6 tháng) |

## 3. Danh Mục Phát Hiện Bất Thường (Anomalies)
- [Liệt kê các khoản chi phí tăng bất thường hoặc dịch vụ trùng lặp]

## 4. Khuyến Nghị Hành Động (Action Items)
1. [Kế hoạch cắt giảm chi phí / Tối ưu dòng tiền]
2. [Thời điểm cần khởi động vòng gọi vốn tiếp theo]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Runway dưới mức an toàn (< 6 tháng)**: Đưa ra cảnh báo đỏ (CRITICAL ALERT) và đề xuất danh sách các chi phí có thể cắt giảm ngay lập tức trong 24 giờ.
- **Dòng tiền vào có độ trễ lớn (High Accounts Receivable)**: Đề xuất giải pháp chiết khấu thanh toán sớm hoặc chuyển sang mô hình thanh toán trả trước (Upfront annual payment).

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/makerskills
  commit: 33cb3870685a34522d91287869aef62170bdbcf7
  skill: company-cfo
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Quy trình CFO Review, Tính toán Burn Rate và Runway, Phân tích kịch bản dòng tiền
  changed:
    - Chuẩn hóa thuật ngữ COSA
    - Thêm cấu trúc 10 mục bắt buộc và định dạng markdown tiếng Việt
  added:
    - Quy định nghiêm ngặt cấm đưa raw banking/PII data vào prompt LLM
    - Liên kết tới runbook chi tiết docs/runbooks/cfo-review.md
    - Phân loại 3 kịch bản rủi ro Runway (Base, Worst, Emergency)
  excluded:
    - Tự động thực thi chuyển tiền hoặc liên kết trực tiếp với open banking API
```
