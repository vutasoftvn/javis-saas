---
name: sales-enablement
description: Xây dựng nội dung hỗ trợ bán hàng (battlecard, xử lý phản đối, one-pager) dựa trên bằng chứng đã xác minh trong giai đoạn Operate & Growth.
---

# Nội Dung Hỗ Trợ Bán Hàng (Sales Enablement)

## Mục đích & Giới hạn Quyền hạn
Soạn thảo nội dung hỗ trợ đội ngũ bán hàng: battlecard đối thủ cạnh tranh, kịch bản xử lý phản đối (objection handling), và one-pager sản phẩm/giải pháp, phục vụ giai đoạn P5_OPERATE_GROWTH khi doanh nghiệp mở rộng đội sales.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra dự thảo artifact (`battlecard`, `objection-handling-script`, `one-pager`). Mọi khẳng định về sản phẩm hoặc đối thủ cạnh tranh (enablement claim) BẮT BUỘC phải trích dẫn một tham chiếu bằng chứng (evidence reference) cụ thể — không được đưa ra bất kỳ khẳng định sản phẩm/cạnh tranh nào không có nguồn (unsourced claim). Không tự ý phát hành nội dung ra kênh công khai hoặc gửi trực tiếp đến khách hàng.

## Triggers
- Kích hoạt khi cần xây dựng hoặc cập nhật battlecard cạnh tranh cho một đối thủ cụ thể.
- Kích hoạt khi cần chuẩn bị kịch bản xử lý phản đối phổ biến của khách hàng.
- Kích hoạt khi cần one-pager tóm tắt giá trị sản phẩm cho một phân khúc/ICP cụ thể.

## Anti-triggers
- Không kích hoạt khi không có bằng chứng nguồn (evidence reference) để trích dẫn cho khẳng định sản phẩm/cạnh tranh.
- Không kích hoạt khi cần gửi nội dung trực tiếp ra ngoài đến khách hàng hoặc publish công khai (dùng skillpack outbound/messaging chuyên biệt có governance riêng).
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `evidence_refs`: Danh sách tham chiếu bằng chứng (competitor profiling, win/loss data, customer interview) cho mỗi khẳng định trong nội dung.

## Evidence Rules
- Mọi khẳng định sản phẩm hoặc cạnh tranh trong battlecard/one-pager phải trích dẫn ít nhất một `evidence_ref` cụ thể (ví dụ: `strategy.competitor-profiling` output, win/loss interview, dữ liệu phân tích thị trường).
- Không được suy diễn hoặc phóng đại tính năng/lợi thế cạnh tranh khi không có bằng chứng hỗ trợ; trong trường hợp này, đánh dấu là giả định (`assumption`) và đề xuất thu thập thêm bằng chứng.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder/Sales Lead trước khi ghi nhận chính thức.

## Quy trình thực hiện (Steps)
1. **Xác định Đối tượng & Mục tiêu**: Xác định đối thủ, phân khúc khách hàng hoặc phản đối cụ thể cần xử lý.
2. **Thu thập Bằng chứng**: Tổng hợp evidence_refs liên quan (competitor profiling, win/loss, customer feedback, positioning).
3. **Soạn Thảo Nội dung**: Xây dựng battlecard/kịch bản xử lý phản đối/one-pager, gắn trích dẫn evidence cho mỗi khẳng định.
4. **Kiểm tra Nguồn**: Rà soát lại toàn bộ khẳng định để đảm bảo không có claim nào thiếu evidence_ref; loại bỏ hoặc gắn nhãn giả định nếu không có nguồn.
5. **Đóng gói Artifacts**: Tạo bản nháp để Founder/Sales Lead xem xét và phê duyệt trước khi phân phối nội bộ.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **battlecard**: So sánh tính năng/giá/vị thế với đối thủ cụ thể, mỗi điểm so sánh kèm evidence_ref.
- **objection-handling-script**: Danh sách phản đối phổ biến kèm cách trả lời được gợi ý, có trích dẫn nguồn khi liên quan đến khẳng định sản phẩm.
- **one-pager**: Tóm tắt giá trị sản phẩm cho phân khúc mục tiêu, có trích dẫn evidence cho mỗi tuyên bố giá trị.

## Fallback & Handoff
- Khi thiếu evidence_ref cho một khẳng định quan trọng, tạo thông báo Handoff đề xuất Founder/Sales Lead thu thập thêm bằng chứng (competitor profiling, win/loss review) trước khi hoàn thiện nội dung.

## Eval Notes
- Suite: `evals/sales/enablement.yaml`
