---
name: finance-unit-economics
description: Phân tích CAC, LTV, thời gian hoàn vốn (payback period) và biên lợi nhuận gộp (gross margin) trong giai đoạn Operate & Growth, gắn nhãn giả định cho mọi input chưa xác minh.
---

# Phân Tích Unit Economics (Finance Unit Economics)

## Mục đích & Giới hạn Quyền hạn
Phân tích các chỉ số unit economics cốt lõi: chi phí thu hút khách hàng (CAC), giá trị vòng đời khách hàng (LTV), thời gian hoàn vốn (payback period) và biên lợi nhuận gộp (gross margin) cho giai đoạn P5_OPERATE_GROWTH, phục vụ đánh giá tính bền vững của mô hình tăng trưởng.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra khuyến nghị phân tích và tạo dự thảo artifact (`unit-economics-report`). Mọi input chưa xác minh hoặc không chắc chắn — bao gồm CAC, LTV, tỷ lệ churn — BẮT BUỘC phải được gắn nhãn tường minh là giả định (`assumption`) trong output, không được trình bày như số liệu đã xác minh. Skillpack này TUYỆT ĐỐI KHÔNG ghi nhận bất kỳ giao dịch tài chính nào — việc ghi nhận giao dịch thuộc capability `finance.transaction.record` đã được phê duyệt riêng, nằm ngoài phạm vi skillpack này.

## Triggers
- Kích hoạt khi cần đánh giá tính bền vững của mô hình unit economics trong giai đoạn P5_OPERATE_GROWTH.
- Kích hoạt khi cần chuẩn bị hồ sơ cho stage gate G5 nhằm chứng minh hiệu quả chi phí thu hút khách hàng và khả năng sinh lời trên từng khách hàng.

## Anti-triggers
- Không kích hoạt khi cần ghi nhận giao dịch tài chính hoặc thanh toán thật (dùng `finance.transaction.record`).
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `financial_inputs`: Các input tài chính đầu vào (chi phí sales & marketing, doanh thu trung bình/khách hàng, tỷ lệ churn, chi phí phục vụ) kèm nguồn gốc dữ liệu (đã xác minh hoặc ước tính).

## Evidence Rules
- Mỗi chỉ số (CAC, LTV, payback, gross margin) phải nêu rõ nguồn dữ liệu đầu vào đã dùng để tính toán.
- Bất kỳ input nào chưa được xác minh từ hệ thống tài chính/kế toán chính thức (ví dụ churn rate ước tính, doanh thu trung bình dự phóng) phải được gắn nhãn `assumption` rõ ràng ngay tại chỗ sử dụng trong output, kèm mức độ tin cậy nếu có thể.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder/CFO trước khi ghi nhận chính thức.

## Quy trình thực hiện (Steps)
1. **Thu thập Input Tài chính**: Tổng hợp chi phí sales & marketing, doanh thu trung bình/khách hàng, tỷ lệ churn và chi phí phục vụ; phân loại từng input là `verified` hoặc `assumption`.
2. **Tính CAC**: Tổng chi phí thu hút chia cho số khách hàng mới trong kỳ.
3. **Tính LTV**: Ước tính giá trị vòng đời dựa trên doanh thu trung bình, biên lợi nhuận gộp và tỷ lệ churn — gắn nhãn giả định cho các tham số chưa xác minh.
4. **Tính Payback Period & Gross Margin**: Xác định thời gian hoàn vốn CAC và biên lợi nhuận gộp trên mỗi khách hàng/nhóm khách hàng.
5. **Đóng gói Artifacts**: Tạo bản nháp `unit-economics-report`, liệt kê rõ ràng phần nào là số liệu đã xác minh và phần nào là giả định, để Founder/CFO xem xét.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **unit-economics-report**: Chỉ số CAC/LTV/payback period/gross margin, phương pháp tính, nguồn dữ liệu cho từng input, và danh sách giả định (`assumption`) rõ ràng kèm mức ảnh hưởng đến kết quả nếu giả định sai lệch.

## Fallback & Handoff
- Khi thiếu dữ liệu tài chính đã xác minh để tính một chỉ số cốt lõi, tạo thông báo Handoff đề xuất Founder/CFO xác minh dữ liệu kế toán hoặc cung cấp số liệu chính thức trước khi hoàn thiện báo cáo.

## Eval Notes
- Suite: `evals/finance/unit-economics.yaml`
