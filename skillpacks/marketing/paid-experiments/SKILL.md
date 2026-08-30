---
name: marketing-paid-experiments
description: Thiết kế thử nghiệm quảng cáo trả phí (hypothesis, targeting, creative) mà không tự chọn/thay đổi ngân sách hay khởi chạy chiến dịch.
---

# Thiết Kế Thử Nghiệm Quảng Cáo Trả Phí (Paid Experiments)

## Mục đích & Giới hạn Quyền hạn
Thiết kế đề xuất thử nghiệm quảng cáo trả phí (paid ad) gồm giả thuyết, phân khúc mục tiêu (targeting), hướng creative, và chỉ số thành công, phục vụ giai đoạn P5_OPERATE_GROWTH.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra khuyến nghị phân tích và tạo dự thảo artifact. Skillpack này **tuyệt đối không tự ý chọn hoặc thay đổi ngân sách (budget)** ở bất kỳ mức nào, **tuyệt đối không tự ý khởi chạy hoặc kích hoạt chiến dịch quảng cáo** trên bất kỳ nền tảng nào, và không tự thay đổi lifecycle stage. Mọi con số ngân sách trong artifact chỉ là **đề xuất khoảng tham khảo** (range) để Founder quyết định — không phải lệnh chi tiêu.

## Triggers
- Kích hoạt khi cần thiết kế một thử nghiệm quảng cáo trả phí mới để kiểm chứng kênh hoặc thông điệp.
- Kích hoạt khi cần đánh giá và đề xuất cải tiến cho một concept quảng cáo đã có trước khi trình Founder phê duyệt.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G5 nhằm chứng minh thử nghiệm quảng cáo có thiết kế khoa học.

## Anti-triggers
- Không kích hoạt khi cần thực sự tạo, sửa ngân sách, hoặc khởi chạy chiến dịch trên nền tảng quảng cáo (Google Ads, Meta Ads, v.v.) — đây là hành động tài chính rủi ro cao, bắt buộc con người thực hiện qua nền tảng gốc sau khi phê duyệt.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự động phân bổ hoặc tối ưu chi tiêu quảng cáo đang chạy.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Mọi giả thuyết targeting và creative phải gắn với bằng chứng ICP, dữ liệu hiệu suất kênh trả phí trước đó, hoặc benchmark ngành có trích dẫn nguồn.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Xác định Giả thuyết Thử nghiệm**: Nêu rõ giả thuyết cần kiểm chứng (kênh, thông điệp, hoặc phân khúc mục tiêu nào sẽ hiệu quả hơn).
2. **Thiết kế Targeting & Creative**: Đề xuất phân khúc mục tiêu và hướng creative phù hợp với giả thuyết, có căn cứ từ ICP.
3. **Xác định Chỉ số Thành công**: Đặt chỉ số đo lường (CTR, CPA, ROAS mục tiêu) và ngưỡng quyết định thắng/thua.
4. **Đề xuất Khoảng Ngân sách Tham khảo**: Đưa ra khoảng ngân sách tham khảo (không phải số chốt) dựa trên quy mô thử nghiệm tối thiểu cần thiết để có kết quả có ý nghĩa thống kê.
5. **Đóng gói Artifacts**: Tạo bản nháp `paid-experiment-design` để Founder xem xét, chỉnh sửa ngân sách thật và tự tay khởi chạy chiến dịch trên nền tảng gốc.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **paid-experiment-design**: Bản thiết kế thử nghiệm quảng cáo gồm giả thuyết, targeting, creative brief, chỉ số thành công và khoảng ngân sách tham khảo — không bao gồm hành động chi tiêu hay khởi chạy thật.

## Fallback & Handoff
- Khi thiếu dữ liệu hiệu suất kênh trả phí lịch sử, tạo thông báo Handoff đề xuất Founder cung cấp dữ liệu chiến dịch trước đó hoặc chấp nhận rủi ro thử nghiệm thăm dò (exploratory) với khoảng ngân sách nhỏ hơn.

## Eval Notes
- Suite: `evals/marketing/paid-experiments.yaml`
