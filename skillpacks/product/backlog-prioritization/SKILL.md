---
name: product-backlog-prioritization
description: Ưu tiên hóa danh mục sản phẩm và tính năng theo giai đoạn vòng đời (Pre-PMF, Early PMF, Scale), ma trận RICE/ICE, và phân tích đánh đổi rõ ràng.
---

# Ưu Tiên Hóa Backlog Sản Phẩm (Product Backlog Prioritization)

## 1. Mục đích & Giới hạn Quyền hạn
Thiết lập phương pháp luận ưu tiên hóa khoa học, minh bạch và phù hợp với từng giai đoạn phát triển của doanh nghiệp. Loại bỏ cảm tính chủ quan ("ai nói to nhất thì làm"), định lượng các ván cược tính năng và đảm bảo nguồn lực kỹ thuật được đầu tư vào những ván cược có tỷ suất hoàn vốn cao nhất.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ cung cấp ma trận đánh giá, bảng điểm ưu tiên và đề xuất thứ tự (L1_PROPOSE). Quyết định cuối cùng về việc đưa tính năng vào lộ trình hay loại bỏ thuộc thẩm quyền của Founder / Product Lead.

## 2. Triggers
- Kích hoạt khi bắt đầu lập kế hoạch cho chu kỳ sản phẩm mới (Sprint, Tháng, Quý hoặc chu kỳ 12-Week Year).
- Kích hoạt khi danh sách yêu cầu tính năng (Backlog) quá tải, các bên liên quan bất đồng về việc nên làm gì trước.
- Kích hoạt khi cần đánh giá một đề xuất tính năng mới chen ngang vào lộ trình.

## 3. Anti-triggers & Anti-patterns Cần Tránh
- **Chặn HiPPO Prioritization:** Từ chối ưu tiên chỉ dựa trên ý kiến của người có chức vụ cao nhất (Highest Paid Person's Opinion) mà không có dữ liệu bằng chứng hoặc lý giải đánh đổi.
- **Chặn Framework Whiplash:** Cấm đổi khung ưu tiên liên tục giữa các tuần. Một khung ưu tiên phải duy trì ổn định từ 6 - 12 tháng.
- **Chặn Coi Điểm Số Là Chân Lý Tuyệt Đối (Scores as Gospel):** Điểm số là đầu vào tham khảo, không tự động hóa quyết định. Quyết định chiến lược của lãnh đạo có thể ghi đè (strategic override) nhưng bắt buộc phải giải thích lý do đánh đổi.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## 4. Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `company_stage`: Giai đoạn công ty (`Pre-PMF`, `Early PMF`, `Growth`, `Mature`).

## 5. Evidence Rules
- Điểm Tác động (Impact) và Độ tin cậy (Confidence) bắt buộc phải dựa trên bằng chứng dữ liệu thực tế (kết quả phỏng vấn, dữ liệu analytics, số lượng khách hàng yêu cầu).
- Mọi khuyến nghị ưu tiên bắt buộc phải nêu rõ **Đánh Đổi (Trade-offs)**: "Chọn làm tính năng A (mang lại ARR nhanh) đồng nghĩa với việc hoãn tính năng B (tối ưu trải nghiệm cho nhóm free) thêm 4 tuần."

## 6. Ma Trận Lựa Chọn Khung Ưu Tiên Thích Ứng (Framework Selection Matrix)

| Bối cảnh & Giai đoạn sản phẩm | Khung ưu tiên đề xuất | Lý do & Cách vận hành |
|---|---|---|
| **Pre-PMF, Dữ liệu ít, Đội ngũ nhỏ** | **ICE** hoặc **Value/Effort Matrix** | Nhẹ nhàng, phản xạ nhanh, chấm điểm theo trực giác và bằng chứng sơ cấp. |
| **Early PMF, Đã có dữ liệu, Đội ngũ đồng thuận** | **RICE** | Cân bằng giữa tầm ảnh hưởng (Reach), tác động (Impact), độ tin cậy (Confidence) và tuần công (Effort). |
| **Sản phẩm trưởng thành, Dữ liệu dồi dào** | **Kano** hoặc **Opportunity Scoring** | Khai thác sâu phản hồi người dùng định lượng, phân loại tính năng bắt buộc vs tính năng tạo sự phấn khích. |
| **Nhiều bên liên quan, Xung đột ưu tiên** | **Weighted Scoring** / **Buy-a-Feature** | Minh bạch trọng số, tạo sự đồng thuận tập thể qua ngân sách tượng trưng. |
| **Doanh nghiệp quy mô lớn, Đa phụ thuộc** | **Cost of Delay (CD3)** | Đo lường chi phí thiệt hại khi chậm trễ phát hành trên mỗi đơn vị thời gian. |

### Quy Tắc Chấm Điểm RICE Chuẩn Hóa Theo Tuần Công:
$$RICE = \frac{Reach \times Impact \times Confidence}{Effort}$$
- **Reach:** Số lượng người dùng bị ảnh hưởng trong chu kỳ (tuần/tháng).
- **Impact:** 3 (Rất lớn), 2 (Cao), 1 (Trung bình), 0.5 (Nhỏ).
- **Confidence:** 1.0 (Dữ liệu xác thực cao), 0.8 (Dữ liệu định tính tốt), 0.5 (Giả định sơ khởi).
- **Effort:** Tuần công kỹ sư (Engineer-weeks). Sử dụng trực tiếp analyzer `score_product_bets_rice()`.

## 7. Allowed Tool Calls
- `strategy.project.get`: Đọc thông tin và mục tiêu chiến lược của dự án hiện tại.
- `operations.task.list`: Đọc danh sách nhiệm vụ và tồn đọng backlog cần xếp hạng ưu tiên.

## 8. Output Format
- **prioritization-scorecard**: Bảng ma trận xếp hạng tính năng có điểm số, xếp loại theo nhóm (P0/P1/P2 hoặc Now/Next/Later), ghi rõ các giả định [assumption] và tuyên bố đánh đổi cụ thể.

## 9. Fallback & Handoff
- Khi các bên chưa thống nhất về trọng số, tổ chức phiên thảo luận với Founder / CPO để chốt mục tiêu tối cao của chu kỳ (ví dụ: Retention > Acquisition).

## 10. Eval Notes
- Suite: `evals/product/backlog-prioritization.yaml`
