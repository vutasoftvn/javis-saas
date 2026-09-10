---
name: strategy-positioning
description: Xác lập định vị giải pháp chiến lược và thông điệp cạnh tranh cốt lõi
  cho giai đoạn P2.
---

# Strategic Solution Positioning & Messaging

## Mục đích & Giới hạn Quyền hạn
Xác lập định vị giải pháp chiến lược và thông điệp cạnh tranh cốt lõi cho giai đoạn P2.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Không tự thay đổi project lifecycle stage, không tự phê duyệt evidence/gate, không tự gọi external provider. Khi action cần quyền hoặc evidence đủ chuẩn, tạo proposal/handoff với ID evidence/artifact liên quan.

## Triggers
- Kích hoạt khi cần thực hiện nghiệp vụ `strategy.positioning` trong giai đoạn P2_SOLUTION_VALIDATION.

## Anti-triggers
- Không kích hoạt ngoài phạm vi dự án hoặc khi thiếu ngữ cảnh `workspace_id` và `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- Thông tin cơ bản về sản phẩm/dịch vụ, tệp người dùng mục tiêu ban đầu, hoặc kết quả phỏng vấn/nghiên cứu sơ cấp (nếu có).

## Evidence Rules
- Tuân thủ nguyên tắc anti-self-validation: Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder/Admin trước khi gate evaluation ghi nhận.
- **Phân tách rạch ròi Evidence vs Assumption**: mỗi mục trong hồ sơ định vị phải được dán nhãn `[Evidence]` (có dữ liệu định lượng, trích dẫn phỏng vấn thật, hoặc bản ghi giao dịch kiểm chứng được) hoặc `[Assumption]` (giả thuyết nội bộ, cần đưa vào `strategy.assumption-discovery`/`discovery.assumption-mapping` để kiểm chứng).
- **Nghiêm cấm bịa đặt**: tuyệt đối không tự bịa testimonial khách hàng, số liệu thị trường hay trích dẫn giả mạo.

## Quy trình thực hiện (Steps)
1. **Xác định ICP (Ideal Customer Profile) & Persona**: phân khúc mục tiêu (ngành, quy mô doanh nghiệp/vai trò người ra quyết định, ngân sách, môi trường công nghệ) và persona (mục tiêu cá nhân, áp lực công việc, tiêu chí đánh giá thành công).
2. **Phân tích Jobs-To-Be-Done (JTBD) & Nỗi đau**: Core Job (việc quan trọng khách hàng đang cố hoàn thành) và Pains & Frustrations (rào cản, chi phí ngầm, rủi ro trong cách làm hiện tại).
3. **Phân tích giải pháp thay thế & khác biệt hóa**: khách hàng đang giải quyết vấn đề bằng gì (đối thủ trực tiếp, làm thủ công, hoặc "không làm gì"); xác định Unique Value Proposition (UVP).
4. **Phân tích lực chuyển đổi (Switching Forces)**: Push (lực đẩy từ hiện trạng tiêu cực) vs Pull (lực kéo từ giải pháp mới); Anxiety (lo lắng khi thay đổi) vs Habit/Inertia (thói quen và sức ỳ hiện tại).
5. **Tổng hợp Customer Language & Proof Points**: ngôn ngữ khách hàng thực tế (từ phỏng vấn/review, tránh buzzword sáo rỗng) và các dẫn chứng số liệu/case study/cơ chế hoạt động thực tế.
6. **Xác lập Positioning Statement**: theo công thức *"Dành cho [ICP], [Sản phẩm] là giải pháp [Category] giúp [Lợi ích cốt lõi], khác biệt với [Giải pháp thay thế] nhờ [Luận điểm chứng minh]."*

## Allowed Tool Calls
Không có công cụ trực tiếp (Artifact/Proposal only). Mọi phân tích dựa trên dữ liệu ngữ cảnh được cung cấp trong hội thoại hoặc tài liệu dự án.

## Output Format
```markdown
# Hồ Sơ Định Vị Sản Phẩm (Product Positioning Profile)

## 1. Khách Hàng Mục Tiêu (ICP & Persona)
- **ICP**: [Mô tả chi tiết] - `[Evidence / Assumption]`
- **Key Persona**: [Vai trò, trách nhiệm] - `[Evidence / Assumption]`

## 2. Jobs-To-Be-Done & Nỗi Đau
- **Core JTBD**: [Mô tả JTBD] - `[Evidence / Assumption]`
- **Key Pains**: [Liệt kê nỗi đau cụ thể] - `[Evidence / Assumption]`

## 3. Giải Pháp Thay Thế & Khác Biệt Cốt Lõi
- **Primary Alternative**: [Cách khách hàng đang làm]
- **Differentiator**: [Khác biệt độc nhất] - `[Evidence / Assumption]`

## 4. Bốn Lực Chuyển Đổi (Switching Forces)
- **Push**: [Lực đẩy từ hiện trạng] · **Pull**: [Lực kéo từ sản phẩm]
- **Anxiety**: [Lo lắng về rủi ro] · **Inertia**: [Thói quen cũ]

## 5. Tuyên Bố Định Vị (Positioning Statement)
*"Dành cho [ICP], [Sản phẩm] là [Category] giúp [Lợi ích cốt lõi], khác với [Alternative] nhờ [Proof Point]."*

## 6. Backlog Giả Định Cần Kiểm Chứng
- [Danh sách các điểm dán nhãn Assumption cần lên kế hoạch test]
```

## Fallback & Handoff
- Khi sản phẩm phục vụ quá nhiều nhóm khách hàng: yêu cầu chọn 1 nhóm ICP ưu tiên số 1 để xây dựng định vị trước, không tạo định vị chung chung phục vụ "tất cả mọi người".
- Khi không có dữ liệu thực tế: toàn bộ hồ sơ định vị phải được đánh dấu `[Assumption]` và khuyến nghị chạy nghiên cứu thị trường hoặc phỏng vấn sơ cấp trước.
- Khi thiếu dữ liệu hoặc không đủ điều kiện an toàn, tạo thông báo Handoff đề xuất người dùng bổ sung thông tin.

## Eval Notes
- Suite: `evals/strategy/positioning.yaml`

## Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/marketingskills
  commit: b1aaa3619e747f4a836c61e03084c4a531de1262
  skill: product-marketing
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Khung định vị ICP, Persona, JTBD, Lực chuyển đổi (Switching forces), Positioning statement
  changed:
    - Chuẩn hóa theo khung Triggers/Anti-triggers/Evidence Rules của Tranche A lifecycle governance
    - Áp dụng applicability P2_SOLUTION_VALIDATION/G2 và autonomy L1_PROPOSE/A chuẩn COSA
  added:
    - Phân loại bằng chứng rạch ròi Evidence vs Assumption
  excluded:
    - Tự động ghi vào database hoặc xuất bản trang landing page trực tiếp
  history:
    - "2026-08-31: nội dung nghiệp vụ hợp nhất từ skillpacks/marketing/positioning (đã retire) để tránh trùng lặp ID canonical."
```
