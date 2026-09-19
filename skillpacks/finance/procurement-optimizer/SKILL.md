---
name: finance-procurement-optimizer
description: Tối ưu hóa chi tiêu mua sắm và kiểm toán SaaS, phân loại chi tiêu theo chuẩn quốc tế UNSPSC, xác định 20% danh mục chiếm 80% chi phí (Pareto 80/20) và đề xuất gom nhà cung cấp an toàn.
---

# Tối Ưu Hóa Chi Tiêu Mua Sắm & Kiểm Toán SaaS (Procurement & Spend Optimization)

## 1. Mục Tiêu (Objective)
Cung cấp phương pháp phân tích và kiểm toán định kỳ toàn bộ chi tiêu phần mềm dịch vụ (SaaS) và hạ tầng điện toán đám mây cho doanh nghiệp. Giúp Founder và CFO trả lời dứt khoát câu hỏi: *"Khoản chi tiêu nào đang tăng trưởng phi mã và đâu là các công cụ đang bị mua trùng lặp chức năng?"*. Áp dụng bảng phân loại chuẩn **UNSPSC**, định vị nhóm danh mục trọng yếu theo nguyên lý **Pareto 80/20**, và xây dựng kế hoạch gom gọn nhà cung cấp (Supplier Consolidation) có kiểm soát rủi ro.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Rà soát ngân sách định kỳ mỗi chu kỳ 12-Week Year (12WY) cùng CFO Advisor nhằm kéo dài số tuần sinh tồn (Weeks of Runway).
  - Khi phát hiện chi phí phần mềm tăng đột biến mà không rõ danh mục nào là nguyên nhân chính.
  - Khi các phòng ban tự ý mua sắm công cụ riêng lẻ dẫn đến tình trạng chồng chéo (Tool sprawl / Duplicate software).
  - Trước khi đàm phán hợp đồng gia hạn hàng năm (Annual renewals).
- **Khi nào KHÔNG dùng**:
  - Khi cần đánh giá chi tiết chất lượng phục vụ hoặc vi phạm SLA của một nhà cung cấp cụ thể (dùng `operations.vendor-management`).
  - Khi thiết lập hạn mức chi tiêu thẻ tín dụng cho nhân viên (dùng `finance.budget-guardrails`).
  - Khi tự ý đơn phương hủy hợp đồng dịch vụ mà không có sự phê duyệt của Founder / CFO.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Ngữ cảnh: `workspace_id`, `project_id`.
- Dữ liệu chi tiêu: Danh sách các khoản thanh toán phần mềm, tên nhà cung cấp, chi phí hàng năm, thời hạn gia hạn.
- Nắm vững các hàm tính toán của `ProcurementSpendAnalyzer` (`agent.operations.analyzers.procurement_spend_analyzer`).

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Thu Thập Danh Mục Chi Tiêu Thực Tế**: Trích xuất dữ liệu hóa đơn, bảng kê chi tiêu thẻ hoặc hợp đồng SaaS hiện hành.
2. **Phân Loại Danh Mục Theo Bảng Mã UNSPSC**:
   - Gán mã danh mục chuẩn quốc tế (ví dụ: `43231500` cho CRM/ERP, `43232800` cho Observability/Monitoring, `43233500` cho Email/Messaging, `81112000` cho Cloud Hosting).
3. **Phân Tích Pareto 80/20 & Xếp Hạng Danh Mục**:
   - Sử dụng `ProcurementSpendAnalyzer.analyze_spend` để tính tổng chi tiêu và tỷ trọng của từng danh mục.
   - Định vị nhóm $20\%$ danh mục cốt lõi chiếm tới $80\%$ tổng ngân sách để tập trung đàm phán.
4. **Phát Hiện Chồng Chéo Công Cụ (Duplicate Tool Detection)**:
   - Quét các danh mục có từ $\ge 2$ nhà cung cấp cùng cung cấp chức năng tương đương (ví dụ: vừa dùng Datadog vừa dùng New Relic, hoặc dùng nhiều nền tảng email marketing).
5. **Đánh Giá Rủi Ro Gom Nhà Cung Cấp (Consolidation & Single-Source Guardrail)**:
   - Lập phương án gom về nhà cung cấp tốt nhất.
   - **Ràng buộc an toàn tuyệt đối:** Nghiêm cấm khuyến nghị cắt giảm xuống nhà cung cấp duy nhất (Single-Source) đối với các dịch vụ cấp 1 (Tier-1 Critical) nếu chưa có phương án dự phòng chuyển mạch khẩn cấp (**Break-glass plan**).
6. **Đóng Gói Báo Cáo Tối Ưu Hóa Chi Tiêu**: Kết xuất tài liệu `procurement-spend-audit` trình CFO và Founder duyệt.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Quy trình được thực thi và kiểm thử thông qua các module chuẩn của agent.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Số liệu chi tiêu phải có nguồn đối chiếu từ sao kê tài chính hoặc hồ sơ thanh toán hợp lệ.
- Báo cáo phân tích Pareto phải có bảng tỷ lệ phần trăm lũy kế minh bạch.

## 7. Safe Fallback & Nghiêm Cấm Anti-Patterns
- **CẤM SINGLE-SOURCE CẢM TÍNH (Single-Source Anti-Pattern):** Gom tất cả dịch vụ vào một đối tác để lấy chiết khấu nhưng lại tạo ra điểm chết chí mạng (Single Point of Failure) cho toàn bộ hệ thống production.
- **CẤM CẮT GIẢM TIỆN ÍCH CỐT LÕI KHÔNG BÁO TRƯỚC:** Mọi đề xuất loại bỏ công cụ phải kèm kế hoạch chuyển đổi dữ liệu và thời hạn thông báo cho đội ngũ sử dụng.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Kiểm Toán & Tối Ưu Hóa Chi Tiêu SaaS (Procurement Spend Audit)

## 1. Tổng Quan Ngân Sách Phần Mềm
- **Tổng chi tiêu hàng năm**: [$XXX,XXX USD]
- **Số lượng nhà cung cấp**: [NN đối tác]
- **Số danh mục chi phối 80% ngân sách (Pareto 80/20)**: [K danh mục]

## 2. Bảng Phân Tích Pareto Theo Danh Mục UNSPSC
| Mã UNSPSC | Tên Danh Mục | Chi Tiêu / Năm | Tỷ Trọng | Lũy Kế | Trọng Yếu (Top 80%) |
|---|---|---|---|---|---|
| 43231500 | CRM / ERP | $XX,XXX | YY.Y% | ZZ.Z% | Cốt lõi (Pareto 20) |
| 43232800 | Monitoring / Observability | $XX,XXX | YY.Y% | ZZ.Z% | Cốt lõi (Pareto 20) |

## 3. Cảnh Báo Công Cụ Chồng Chéo & Đề Xuất Gom Gọn
- ⚠️ **[Tên danh mục có công cụ trùng lặp]**: Đang chi trả cho [Vendor A, Vendor B]
  - *Khuyến nghị*: Gom về [Vendor được chọn] — Ước tính tiết kiệm: [$XX,XXX USD / năm]

## 4. Kiểm Soát Rủi Ro Chuỗi Cung Ứng Cấp 1
- 🔴 **Cảnh báo Single-Source**: [Liệt kê các đối tác Tier-1 chưa có kế hoạch Break-glass]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Hợp đồng dài hạn có điều khoản phạt hủy ngang (Early Termination Penalty)**: Khi đề xuất gom nhà cung cấp, phải tính toán chi phí phạt so với số tiền tiết kiệm được trước khi khuyến nghị thời điểm chuyển đổi.
- **Chi tiêu không có mã danh mục rõ ràng**: Tạm xếp vào danh mục `81112000` (Dịch vụ CNTT chung) và yêu cầu Finance Lead xác nhận tính chất sử dụng.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: procurement-optimizer
  upstream_version: 2.8.0
  license: MIT
adaptation:
  kept:
    - Bảng phân loại danh mục quốc tế UNSPSC
    - Phân tích Pareto 80/20 và nguyên tắc chống Single-Source rủi ro cao cho Tier-1
  changed:
    - Chuyển đổi sang quy chuẩn 10 mục COSA tiếng Việt
    - Đồng bộ với chỉ số Runway theo tuần trong 12WY
  added:
    - Tích hợp trực tiếp với ProcurementSpendAnalyzer trong packages/agent/operations/analyzers
    - Quy tắc đánh giá chi phí phạt hủy hợp đồng sớm
  excluded:
    - Bỏ các script shell đọc file CSV cục bộ
```
