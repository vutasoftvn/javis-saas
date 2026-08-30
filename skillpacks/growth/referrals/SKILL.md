---
name: growth-referrals
description: Thiết kế và phân tích hiệu quả chương trình giới thiệu khách hàng (referral program) trong giai đoạn Operate & Growth.
---

# Thiết Kế & Phân Tích Chương Trình Giới Thiệu (Growth Referrals)

## Mục đích & Giới hạn Quyền hạn
Thiết kế cấu trúc chương trình giới thiệu khách hàng (referral program): cơ chế kích hoạt, điều kiện đủ điều kiện (eligibility), cấu trúc phần thưởng đề xuất, và phân tích hiệu quả chương trình hiện có (tỷ lệ tham gia, hệ số viral, chi phí trên mỗi khách hàng giới thiệu) trong giai đoạn P5_OPERATE_GROWTH.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra dự thảo artifact (`referral-program-design`, `referral-performance-analysis`). Skillpack này TUYỆT ĐỐI KHÔNG tự tạo (create), không tự phê duyệt (authorize) và không tự phát hành (issue) bất kỳ phần thưởng, mã giảm giá hay khoản thanh toán nào cho người giới thiệu hoặc người được giới thiệu — mọi đề xuất cấu trúc phần thưởng chỉ dừng ở mức thiết kế/phân tích, việc phát hành phần thưởng hoặc thanh toán thực tế phải qua capability tài chính riêng đã được phê duyệt và do con người thực thi.

## Triggers
- Kích hoạt khi cần thiết kế cấu trúc chương trình giới thiệu mới trong giai đoạn P5_OPERATE_GROWTH.
- Kích hoạt khi cần phân tích hiệu quả chương trình giới thiệu hiện có (tỷ lệ tham gia, hệ số viral, ROI).

## Anti-triggers
- Không kích hoạt khi cần tự động phát hành phần thưởng, mã giảm giá hoặc thanh toán cho người dùng.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `referral_program_data`: Dữ liệu chương trình giới thiệu hiện có (nếu phân tích chương trình đang chạy), bao gồm số lượt giới thiệu, tỷ lệ chuyển đổi, và cấu trúc phần thưởng hiện tại.

## Evidence Rules
- Mọi đề xuất cấu trúc phần thưởng phải dựa trên bằng chứng benchmark ngành, dữ liệu unit economics hiện có (CAC, LTV) hoặc kết quả thử nghiệm A/B trước đó.
- Phân tích hiệu quả chương trình phải trích dẫn dữ liệu nguồn cụ thể (referral_program_data) và ngày trích xuất; không suy diễn hệ số viral hoặc ROI khi thiếu dữ liệu tham gia thực tế — trong trường hợp đó, gắn nhãn giả định (`assumption`).
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi ghi nhận chính thức.

## Quy trình thực hiện (Steps)
1. **Xác định Mục tiêu Chương trình**: Xác định mục tiêu tăng trưởng (số lượng khách hàng mới, giảm CAC) và phân khúc khách hàng mục tiêu cho referral.
2. **Thiết kế Cơ chế**: Đề xuất điều kiện kích hoạt, tiêu chí đủ điều kiện và cấu trúc phần thưởng đề xuất (chỉ ở dạng đề xuất, không phát hành).
3. **Phân tích Hiệu quả (nếu có chương trình đang chạy)**: Tính tỷ lệ tham gia, hệ số viral (k-factor), chi phí trên mỗi khách hàng giới thiệu, so sánh với CAC kênh khác.
4. **Đánh giá Rủi ro Gian lận**: Nêu các rủi ro lạm dụng chương trình (self-referral, gian lận) và đề xuất biện pháp kiểm soát cần con người phê duyệt.
5. **Đóng gói Artifacts**: Tạo bản nháp `referral-program-design` và/hoặc `referral-performance-analysis` để Founder xem xét và phê duyệt trước khi triển khai thực tế.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **referral-program-design**: Cơ chế kích hoạt, tiêu chí đủ điều kiện, cấu trúc phần thưởng đề xuất (không tự phát hành), và rủi ro gian lận cần kiểm soát.
- **referral-performance-analysis**: Tỷ lệ tham gia, hệ số viral, chi phí trên mỗi khách hàng giới thiệu, so sánh hiệu quả với các kênh tăng trưởng khác, và giả định (nếu có).

## Fallback & Handoff
- Khi thiếu dữ liệu tham gia thực tế hoặc dữ liệu unit economics để thiết kế cấu trúc phần thưởng hợp lý, tạo thông báo Handoff đề xuất Founder cung cấp thêm dữ liệu hoặc chạy thử nghiệm nhỏ trước khi mở rộng chương trình.

## Eval Notes
- Suite: `evals/growth/referrals.yaml`
