---
name: product-prd
description: Xây dựng tài liệu yêu cầu sản phẩm (PRD) 10 mục chuẩn hoá gồm bài toán người dùng, bối cảnh chiến lược, giải pháp, số liệu thành công đo lường được, phạm vi ngoài (out-of-scope) và tiêu chí nghiệm thu.
---

# Tài Liệu Yêu Cầu Sản Phẩm (Product Requirements Document - PRD)

## 1. Mục đích & Giới hạn Quyền hạn
Xây dựng tài liệu đặc tả yêu cầu sản phẩm (PRD) có tính hành động cao cho giai đoạn P3_BUILD_VALIDATE theo chuẩn 10 mục thực chiến. Định hình rõ nét ranh giới bài toán, đối tượng sử dụng, các chỉ số thành công kiểm chứng được, giải pháp luồng người dùng và cam kết những gì KHÔNG làm (Out of Scope).

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo tài liệu đặc tả (Artifact/Proposal ở mức L1_PROPOSE). Tuyệt đối không tự ý sửa đổi cơ sở dữ liệu production, không kích hoạt CI/CD deploy mã nguồn hay tự ý chỉnh sửa mã sản phẩm.

## 2. Triggers
- Kích hoạt khi chuẩn bị phát triển tính năng hoặc phân hệ giải pháp mới trong giai đoạn P3_BUILD_VALIDATE.
- Kích hoạt khi Founder hoặc Tech Lead yêu cầu chuyển giao đặc tả kỹ thuật rõ ràng cho đội ngũ kỹ sư.
- Kích hoạt khi cần rà soát lại phạm vi của một Product Bet trong chu kỳ 12-Week Year.

## 3. Anti-triggers & Framing Gate
Bộ lọc chất lượng tư duy sản phẩm (Framing Gate - Always On):
- **Chặn Solution Smuggling:** Từ chối hoặc yêu cầu định nghĩa lại nếu bài toán bắt đầu bằng giải pháp áp đặt ("Cần một dashboard phân tích" -> Phải chuyển thành: "Người quản lý không nhìn thấy tốc độ hoàn thành công việc của đội ngũ").
- **Chặn Thiếu Thước Đo Thành Công:** Từ chối nếu không có chỉ số đo lường hiệu quả cụ thể (phải có cấu trúc: Baseline -> Target -> Timeframe).
- **Chặn Phình Phạm Vi (Scope Creep):** Từ chối gom 3+ tính năng độc lập, không liên quan vào một tài liệu PRD duy nhất.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## 4. Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `problem_evidence`: Các bằng chứng vấn đề và giả định giải pháp đã được ghi nhận ở P1/P2.

## 5. Evidence Rules
- PRD phải trích dẫn trực tiếp nguồn bằng chứng thực nghiệm (trích dẫn phỏng vấn khách hàng, dữ liệu vé hỗ trợ, chỉ số analytics).
- Giả định chưa kiểm chứng bắt buộc phải gắn nhãn `[assumption]`.
- Luôn chỉ rõ sự đánh đổi (trade-offs): Chọn phương án này đồng nghĩa với việc chấp nhận đánh đổi điều gì (tốc độ vs chất lượng ban đầu, phạm vi vs độ phức tạp vận hành).

## 6. Quy trình thực hiện (Steps & Cấu trúc PRD 10 Mục)
1. **Executive Summary**: Tóm tắt 1 đoạn văn: "Chúng tôi xây dựng [giải pháp] cho [đối tượng persona] nhằm giải quyết [bài toán], mang lại [tác động kinh doanh/người dùng cụ thể]."
2. **Problem Statement**: Ai gặp vấn đề? Vấn đề cụ thể là gì? Tại sao gây đau đớn? Bằng chứng dữ liệu thực tế kèm trích dẫn nguyên văn.
3. **Target Users & Personas**: Chân dung người dùng mục tiêu cụ thể (Primary/Secondary) và công việc cần hoàn thành (Jobs-To-Be-Done - JTBD).
4. **Strategic Context**: Đóng góp vào mục tiêu chiến lược của công ty (OKRs), cơ hội thị trường và lý do "Tại sao phải làm ngay bây giờ? (Why now?)".
5. **Solution Overview & User Flows**: Mô tả giải pháp ở mức luồng trải nghiệm người dùng (user flows), không can thiệp sâu vào chi tiết pixel giao diện.
6. **Success Metrics**: 
   - Primary Metric (Chỉ số tối ưu chính).
   - Secondary Metrics (Chỉ số theo dõi phụ).
   - Guardrail Metrics (Chỉ số chặn: không được phép suy giảm, ví dụ tăng chuyển đổi nhưng không làm tăng churn).
   - Định dạng bắt buộc: `Hiện tại X -> Mục tiêu Y, đo lường sau Z ngày ra mắt`.
7. **User Stories & Requirements**: Giả định Epic và các User Stories phân rã theo lát cắt dọc kèm tiêu chí nghiệm thu Given-When-Then.
8. **Out of Scope**: Liệt kê rõ ràng những gì tính năng này KHÔNG làm trong phiên bản này và lý do tại sao hoãn lại.
9. **Dependencies & Risks**: Phụ thuộc kỹ thuật, API bên thứ ba, rủi ro tiềm ẩn và phương án giảm thiểu.
10. **Open Questions**: Những câu hỏi chưa có lời giải đáp cần tiếp tục khám phá hoặc kiểm chứng thêm.

## 7. Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## 8. Output Format
- **prd-document**: Tài liệu PRD chuẩn Markdown 10 mục hoàn chỉnh, gắn nhãn giả định và kết thúc bằng phán quyết hành động kế tiếp.

## 9. Fallback & Handoff
- Khi thiếu dữ liệu định lượng, fallback sang chế độ Best Guess có gắn nhãn `[assumption]` và lập danh sách các câu hỏi mở chuyển giao cho Founder / Product Lead xác nhận.

## 10. Eval Notes
- Suite: `evals/product/prd.yaml`
