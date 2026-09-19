---
name: product-research-ops
description: Chuẩn hóa quy trình vận hành nghiên cứu sản phẩm, lập kế hoạch cỡ mẫu bão hòa theo Nielsen và Guest, và chuyển hóa quan sát thực nghiệm thành kho lưu trữ Insight có kiểm chứng.
---

# Vận Hành Nghiên Cứu Sản Phẩm & Kho Lưu Trữ Insight (Product Research Operations & Insight Repository)

## 1. Mục Tiêu (Objective)
Thiết lập quy trình vận hành nghiên cứu sản phẩm (ResearchOps) chuẩn mực cho đội ngũ phát triển sản phẩm. Kỹ năng này cung cấp căn cứ toán học định lượng để xác định số lượng người dùng cần thử nghiệm khả năng sử dụng (định luật Nielsen $1-(1-p)^n$) hoặc phỏng vấn sâu chuyên đề (chuẩn Guest et al.), đồng thời áp dụng quy chế phân cấp nghiêm ngặt: **Quan sát thô (Observations) $\rightarrow$ Hiểu biết sâu sắc (Insights) $\rightarrow$ Đề xuất hành động (Recommendations)**, ngăn chặn tuyệt đối lỗi quy chụp ý kiến của 1 người dùng thành quy luật của cả phân khúc.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi thiết kế kế hoạch phỏng vấn người dùng, kiểm thử khả năng sử dụng (Usability Testing) cho tính năng mới.
  - Khi cần tổng hợp hàng chục bản ghi chép phỏng vấn thành kho tri thức sản phẩm (Research Repository).
  - Khi chuẩn bị tài liệu bằng chứng cho Gate G1 (Problem Validation) hoặc G2 (Solution Validation).
- **Khi nào KHÔNG dùng**:
  - Khi viết bản mô tả tính năng chi tiết cho lập trình viên (dùng `product.prd` hoặc `product.user-story-and-acceptance`).
  - Khi chỉ cần chuẩn bị kịch bản câu hỏi phỏng vấn cơ bản (dùng `discovery.interview-script`).
  - Khi phân tích chỉ số kinh doanh vĩ mô hoặc quy mô thị trường (dùng `research.market-sizing`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Mục tiêu nghiên cứu sản phẩm cụ thể (Khám phá vấn đề hay Đánh giá giải pháp/khả năng sử dụng).
- Định nghĩa phân khúc người dùng mục tiêu (Homogeneous vs Heterogeneous).
- Bối cảnh dự án (`workspace_id`, `project_id`).

## 4. Các Bước Tất Định (Deterministic Steps)

```
┌────────────────────────────────────────────────────────┐
│ 1. LẬP KẾ HOẠCH CỠ MẪU BÃO HÒA (SATURATION PLANNING)   │
│    • Usability (Nielsen): 5 users -> ~85% lỗi          │
│    • Thematic (Guest et al.): 12 users / phân khúc     │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. THU THẬP & PHÂN RÃ QUAN SÁT (RAW OBSERVATIONS)      │
│    • Trích xuất sự kiện hành vi và câu nói nguyên văn  │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. KIỂM DUYỆT LINTER CHỐNG QUY CHỤP (INSIGHT LINTER)   │
│    • 1 Người dùng = ANECDOTE (Giai thoại)              │
│    • >= 3 Người dùng hội tụ = INSIGHT (Quy luật)       │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. TỔNG HỢP VÀO KHO LƯU TRỮ (RESEARCH REPOSITORY)      │
│    • Observation -> Insight -> Product Recommendation  │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 5. ĐỀ XUẤT HÀNH ĐỘNG SẢN PHẨM & BÀN GIAO CHO PRD       │
└────────────────────────────────────────────────────────┘
```

1. **Lập Kế Hoạch Cỡ Mẫu Bão Hòa (Saturation Modeling)**:
   - Sử dụng `ResearchSaturationModeler` (`packages/agent/research/analyzers/research_saturation_modeler.py`).
   - *Kiểm thử khả năng sử dụng (Usability Study)*: Với tỷ lệ phát hiện lỗi điển hình $p=0.31$, cần 5 người dùng cho mỗi phân khúc để phát hiện $\sim 85\%$ vấn đề nghiêm trọng:
     $n = \lceil \frac{\ln(1 - 0.85)}{\ln(1 - 0.31)} \rceil = 5\text{ người/phân khúc}$.
   - *Phỏng vấn chuyên đề sâu (Thematic Discovery)*: Cần tối thiểu 12 cuộc phỏng vấn cho nhóm đồng nhất (15 người nếu mức độ phân hóa hoặc rủi ro nghiệp vụ cao) để đạt điểm bão hòa chủ đề.
2. **Thu Thập Dữ Liệu Quan Sát Thực Nghiệm (Raw Observations)**:
   - Ghi nhận hành vi cụ thể: người dùng thao tác ở đâu, ngập ngừng tại bước nào, hoặc phát biểu nguyên văn điều gì.
   - Gắn mã định danh người tham gia (`P01`, `P02`,...).
3. **Kiểm Duyệt Bằng Insight Linter (Chống Quy Chụp)**:
   - Áp dụng nguyên tắc vàng của ResearchOps: **Không bao giờ bịa đặt hoặc tổng quát hóa insight từ một cá nhân đơn lẻ**.
   - Nếu một hành vi hoặc ý kiến chỉ xuất hiện ở 1 người tham gia: **Bắt buộc gắn nhãn `ANECDOTE` (Giai thoại cá nhân)**.
   - Chỉ khi một mẫu hình lặp lại ở từ 3 người tham gia trở lên độc lập, mới được tổng hợp thành **`INSIGHT`**.
4. **Cấu Trúc Kho Lưu Trữ Insight (Research Repository Schema)**:
   - Mỗi đơn vị tri thức trong kho gồm 3 tầng liên kết chặt chẽ:
     - `Observation` (Dữ liệu quan sát): "3/5 người dùng ấn nhầm vào nút Hủy khi cố gắng lưu biểu mẫu."
     - `Insight` (Hiểu biết sâu sắc): "Vị trí nút Hủy có màu sắc tương phản quá nổi bật, gây nhầm lẫn với nút CTA chính."
     - `Recommendation` (Đề xuất hành động): "Đổi nút Hủy thành dạng ghost button/secondary, đặt nút Lưu biểu mẫu ở góc phải trên cùng."
5. **Bàn Giao & Liên Kết Với PRD**:
   - Trích xuất các đề xuất có độ tin cậy cao để làm đầu vào trực tiếp cho `product.prd` hoặc `product.backlog-prioritization`.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- Kỹ năng phân tích thuần túy, không yêu cầu công cụ ngoài có side-effect. Dữ liệu đầu vào đọc từ workspace context.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- **Minh chứng về số lượng người tham gia**: Mọi insight được tuyên bố phải nêu rõ số lượng và mã định danh người tham gia xác nhận ($k/n$ users).
- **Ranh giới Anecdote vs Insight**: Nghiêm cấm đưa vào PRD các giả định gắn mác "Người dùng phản ánh..." nếu dữ liệu chỉ xuất phát từ 1 người duy nhất mà không có nhãn Anecdote.

## 7. Safe Fallback
- Khi số lượng phỏng vấn chưa đạt ngưỡng bão hòa ($n < 5$ đối với usability, $n < 12$ đối với thematic):
  - Agent vẫn tổng hợp dữ liệu nhưng gắn nhãn cảnh báo: `[EARLY SIGNALS - PRE-SATURATION]`.
  - Khuyến nghị bổ sung số người dùng còn thiếu trước khi chốt quyết định kiến trúc lớn.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Vận Hành Nghiên Cứu Sản Phẩm (Product Research Synthesis Brief)

## 1. Thông Số Nghiên Cứu & Điểm Bão Hòa (Study Methodology)
- **Phương pháp**: [Usability Testing / Thematic Interview]
- **Số phân khúc**: X phân khúc | **Số người tham gia thực tế**: XX người
- **Độ bao phủ lỗi kỳ vọng**: XX% (Chuẩn Nielsen / Guest)
- **Trạng thái bão hòa**: [BÃO HÒA ĐẠT CHUẨN / TÍN HIỆU SƠ KHỞI (PRE-SATURATION)]

## 2. Kho Lưu Trữ Phát Hiện (Insight Repository)

### 2.1 [Chủ đề 1: Điều hướng và Trải nghiệm biểu mẫu]
| ID | Dữ liệu Quan Sát (Observation) | Mã người tham gia | Phân loại | Hiểu biết sâu sắc (Insight) | Đề xuất hành động (Recommendation) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| INS-01 | 4/5 người dùng ngập ngừng > 10s tại bước chọn gói cước | P01, P03, P04, P05 | **INSIGHT** | Khách hàng không hiểu sự khác biệt giữa gói Team và Pro | Bổ sung bảng so sánh tính năng rút gọn ngay dưới card |
| ANC-01 | 1 người dùng đề xuất thêm đăng nhập bằng ví Web3 | P02 | **ANECDOTE** | Nhu cầu cá biệt của nhóm người dùng crypto | Tạm lưu trữ vào backlog khám phá, chưa ưu tiên MVP |

## 3. Bản Đồ Trọng Số Ảnh Hưởng (Impact vs Effort Matrix)
- **Ưu tiên P0 (Khắc phục ngay)**: [INS-01: Tinh gọn bảng giá]
- **Ưu tiên P1 (Đưa vào sprint tới)**: [Các insight có độ hội tụ cao]

## 4. Khuyến Nghị Chuyển Giao Cho Đội Ngũ Sản Phẩm
- Đề xuất cập nhật tài liệu PRD tại: `docs/features/...`
- Đề xuất tạo task backlog cho kỹ thuật.
```

## 9. Xử Lý Lỗi & Phòng Vệ An Toàn (Security & Edge Cases)
- **Thiên lệch chọn mẫu (Selection Bias)**: Nếu toàn bộ người tham gia phỏng vấn đều là bạn bè của Founder hoặc người dùng thân thiết, agent gắn cờ `[High Selection Bias - Expand to Cold Users]`.
- **Bảo vệ quyền riêng tư người dùng (PII)**: Không ghi tên thật, số điện thoại hoặc email người dùng vào báo cáo; bắt buộc mã hóa thành `P01`, `P02`...

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: research-ops/skills/product-research
  upstream_version: 2.9.0
  license: MIT
adaptation:
  kept:
    - Định luật Nielsen 5 người dùng cho kiểm thử khả năng sử dụng
    - Chuẩn Guest et al. 12 cuộc phỏng vấn cho điểm bão hòa chủ đề
    - Phân cấp nghiêm ngặt Observation -> Insight -> Recommendation
    - Quy tắc nghiêm cấm coi 1 người tham gia là Insight
  changed:
    - Bản địa hóa sang tiếng Việt và cấu trúc 10 mục chuẩn COSA
    - Đóng gói thành skillpack product.research-ops
    - Tích hợp ResearchSaturationModeler thuần Python stdlib
  added:
    - Bảng ma trận Insight Repository tích hợp trong Markdown
    - Bảo vệ thông tin định danh cá nhân PII
  excluded:
    - Các script khảo sát bên thứ ba không tương thích
```
