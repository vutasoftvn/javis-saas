---
name: growth-ab-testing
description: Thiết kế thử nghiệm A/B theo phương pháp thống kê và diễn giải kết quả, yêu cầu tham chiếu metric-contract có sẵn trước khi phân tích.
---

# Thiết Kế & Diễn Giải Thử Nghiệm A/B Theo Thống Kê (A/B Testing)

## Mục đích & Giới hạn Quyền hạn
Thiết kế thử nghiệm A/B theo phương pháp thống kê chặt chẽ (giả thuyết, cỡ mẫu, thời gian chạy, ngưỡng ý nghĩa) và diễn giải kết quả thử nghiệm đã có, phục vụ giai đoạn P5_OPERATE_GROWTH.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra khuyến nghị phân tích và tạo dự thảo artifact. Skillpack này **bắt buộc phải có tham chiếu đến một metric-contract đã tồn tại** (`analytics.metric_contract.get`) trước khi diễn giải hoặc phân tích bất kỳ kết quả thử nghiệm nào — **tuyệt đối không phân tích dựa trên con số không có nguồn tham chiếu hoặc do agent tự bịa ra**. Skillpack không tự ý triển khai biến thể thử nghiệm lên production, và không tự thay đổi lifecycle stage.

## Triggers
- Kích hoạt khi cần thiết kế một thử nghiệm A/B mới với yêu cầu về cỡ mẫu và thời gian chạy theo thống kê.
- Kích hoạt khi cần diễn giải kết quả một thử nghiệm A/B đã hoàn thành, với điều kiện đã có metric-contract tham chiếu.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G5 nhằm chứng minh quyết định tăng trưởng dựa trên thử nghiệm có ý nghĩa thống kê.

## Anti-triggers
- Không kích hoạt để diễn giải một con số kết quả khi không có metric-contract tham chiếu — trong trường hợp này phải dừng lại và yêu cầu bổ sung metric-contract trước.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự động triển khai biến thể thắng cuộc lên production mà chưa có phê duyệt của con người.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `metric_contract_ref`: Tham chiếu đến metric-contract đã đăng ký (qua `analytics.metric_contract.get`), bắt buộc trước khi phân tích bất kỳ kết quả thử nghiệm nào.

## Evidence Rules
- Mọi số liệu đầu vào (baseline conversion rate, minimum detectable effect, dữ liệu kết quả) phải trích dẫn từ metric-contract hoặc nguồn dữ liệu đã đăng ký; không được suy diễn hoặc ước lượng khi thiếu tham chiếu.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Xác nhận Metric-Contract**: Kiểm tra sự tồn tại của metric-contract tham chiếu; nếu không có, dừng lại và tạo Handoff yêu cầu bổ sung thay vì tự suy diễn số liệu.
2. **Thiết kế Thử nghiệm**: Xác định giả thuyết, biến thể, chỉ số chính (primary metric) theo metric-contract, minimum detectable effect và cỡ mẫu cần thiết.
3. **Xác định Thời gian Chạy & Ngưỡng Ý nghĩa**: Tính thời gian chạy tối thiểu dựa trên lưu lượng hiện có và đặt ngưỡng ý nghĩa thống kê (ví dụ p < 0.05).
4. **Diễn giải Kết quả (nếu đã có dữ liệu)**: Đối chiếu kết quả thử nghiệm với chỉ số trong metric-contract, đánh giá ý nghĩa thống kê và độ tin cậy, tránh kết luận sớm khi chưa đủ cỡ mẫu.
5. **Đóng gói Artifacts**: Tạo bản nháp `ab-test-design` và/hoặc `ab-test-result-interpretation` để Founder xem xét trước khi quyết định triển khai biến thể thắng cuộc.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **ab-test-design**: Thiết kế thử nghiệm A/B đầy đủ (giả thuyết, biến thể, cỡ mẫu, thời gian chạy, ngưỡng ý nghĩa), tham chiếu metric-contract.
- **ab-test-result-interpretation**: Diễn giải kết quả thử nghiệm đối chiếu với metric-contract, kèm khuyến nghị (tiếp tục/dừng/mở rộng) — không tự động triển khai.

## Fallback & Handoff
- Khi không có metric-contract tham chiếu, tạo thông báo Handoff yêu cầu Founder hoặc đội phân tích đăng ký metric-contract qua `analytics.metric_contract.get` trước khi skillpack tiếp tục phân tích.

## Eval Notes
- Suite: `evals/growth/ab-testing.yaml`
