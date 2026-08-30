---
name: marketing-gtm-funnel
description: Thiết kế và chẩn đoán funnel go-to-market (awareness → activation → revenue), phát hiện điểm nghẽn chuyển đổi dựa trên bằng chứng.
---

# Thiết Kế & Chẩn Đoán Funnel Go-To-Market (GTM Funnel)

## Mục đích & Giới hạn Quyền hạn
Xây dựng bản đồ funnel go-to-market đầy đủ các tầng (awareness → acquisition → activation → retention → revenue), gắn từng tầng với chỉ số chuyển đổi thực tế, và chẩn đoán điểm nghẽn (bottleneck) dựa trên dữ liệu phân tích và bằng chứng khách hàng trong giai đoạn P5_OPERATE_GROWTH.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra khuyến nghị phân tích và tạo dự thảo artifact. Tuyệt đối không tự ý khởi chạy chiến dịch quảng cáo, không tự ý thay đổi cấu hình tracking/phân tích sản xuất, và không tự thay đổi lifecycle stage.

## Triggers
- Kích hoạt khi cần xây dựng hoặc cập nhật bản đồ funnel GTM cho giai đoạn P5_OPERATE_GROWTH.
- Kích hoạt khi cần chẩn đoán vì sao tỷ lệ chuyển đổi giữa hai tầng funnel sụt giảm hoặc trì trệ.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G5 nhằm chứng minh funnel đã được đo lường và tối ưu có căn cứ.

## Anti-triggers
- Không kích hoạt khi cần thực thi thay đổi kỹ thuật lên hệ thống tracking/analytics (đây là việc của kỹ thuật, không phải phân tích chiến lược).
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự quyết định phân bổ ngân sách marketing.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Mọi con số chuyển đổi (conversion rate) trình bày trong funnel phải trích dẫn nguồn dữ liệu cụ thể (analytics dashboard, tracking plan, báo cáo phỏng vấn khách hàng); không được suy diễn hoặc tự ước lượng khi không có nguồn.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Ánh xạ các tầng Funnel**: Liệt kê đầy đủ các tầng awareness → activation → revenue phù hợp với mô hình kinh doanh hiện tại.
2. **Gắn chỉ số & nguồn dữ liệu**: Với mỗi tầng, gắn conversion rate thực tế và nguồn dữ liệu tương ứng.
3. **Chẩn đoán điểm nghẽn**: So sánh tỷ lệ chuyển đổi giữa các tầng với benchmark ngành hoặc dữ liệu lịch sử để xác định tầng yếu nhất.
4. **Đề xuất giả thuyết cải thiện**: Với mỗi điểm nghẽn, đề xuất 1-2 giả thuyết cải thiện có thể kiểm chứng.
5. **Đóng gói Artifacts**: Tạo bản nháp `gtm-funnel-map` và `funnel-diagnostic-brief` để Founder xem xét.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **gtm-funnel-map**: Bản đồ funnel đầy đủ các tầng, chỉ số chuyển đổi và nguồn dữ liệu tương ứng.
- **funnel-diagnostic-brief**: Bản chẩn đoán điểm nghẽn kèm giả thuyết cải thiện được xếp hạng theo mức độ tác động ước tính.

## Fallback & Handoff
- Khi thiếu dữ liệu analytics cho một hoặc nhiều tầng funnel, tạo thông báo Handoff đề xuất Founder bổ sung tracking hoặc thực hiện khảo sát bổ sung trước khi hoàn tất chẩn đoán.

## Eval Notes
- Suite: `evals/marketing/gtm-funnel.yaml`
