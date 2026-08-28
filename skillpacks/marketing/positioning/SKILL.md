---
name: marketing-positioning
description: Hướng dẫn xây dựng định vị sản phẩm, chân dung khách hàng mục tiêu (ICP/Persona), Jobs-To-Be-Done, lực đẩy/kéo chuyển đổi và khung thông điệp tiếp thị dựa trên bằng chứng.
---

# Quy Trình Xác Định Vị Trí Sản Phẩm & Khung Thông Điệp (Product Positioning)

## 1. Mục Tiêu (Objective)
Xây dựng tài liệu định vị sản phẩm hoàn chỉnh, phân biệt rõ giữa giả định (assumptions) và dữ liệu thực tế (evidence) về khách hàng mục tiêu, bài toán cần giải (JTBD), giải pháp thay thế, và luận điểm chứng minh giá trị vượt trội.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi khởi tạo sản phẩm mới hoặc bước vào thị trường mới.
  - Khi cần chuẩn hóa chân dung khách hàng mục tiêu (ICP) và khung thông điệp trước khi viết copy hoặc chạy chiến dịch tiếp thị.
  - Khi phát hiện chuyển đổi thấp do thông điệp mơ hồ hoặc nhắm sai đối tượng.
- **Khi nào KHÔNG dùng**:
  - Khi chỉ cần tối ưu câu chữ của một bài viết cụ thể (dùng `marketing.copywriting`).
  - Khi cần lập kế hoạch từ khóa cho công cụ tìm kiếm (dùng `marketing.seo-plan`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Thông tin cơ bản về sản phẩm/dịch vụ, tệp người dùng mục tiêu ban đầu, hoặc kết quả phỏng vấn/nghiên cứu sơ cấp (nếu có).

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Xác định ICP (Ideal Customer Profile) & Persona**:
   - Phân khúc mục tiêu: Ngành, quy mô doanh nghiệp / vai trò người ra quyết định, ngân sách, môi trường công nghệ.
   - Persona: Mục tiêu cá nhân, áp lực công việc, tiêu chí đánh giá thành công.
2. **Phân tích Jobs-To-Be-Done (JTBD) & Nỗi đau (Pain Points)**:
   - Core Job: Việc quan trọng khách hàng đang cố gắng hoàn thành.
   - Pains & Frustrations: Các rào cản, chi phí ngầm, rủi ro trong cách làm hiện tại.
3. **Phân tích giải pháp thay thế (Alternatives) & Khác biệt hóa**:
   - Khách hàng đang giải quyết vấn đề bằng gì (đối thủ trực tiếp, Excel, làm thủ công, hoặc "không làm gì")?
   - Unique Value Proposition (UVP): Lợi ích cốt lõi độc nhất và lý do vượt trội.
4. **Phân tích lực chuyển đổi (Switching Forces)**:
   - Push (Lực đẩy từ hiện trạng tiêu cực) vs Pull (Lực kéo từ giải pháp mới).
   - Anxiety (Sự lo lắng khi thay đổi) vs Habit/Inertia (Thói quen và sức ỳ hiện tại).
5. **Tổng hợp Customer Language & Proof Points**:
   - Ngôn ngữ khách hàng dùng (từ ngữ thực tế trích từ phỏng vấn/review, tránh buzzword sáo rỗng).
   - Proof Points: Dẫn chứng số liệu, case study, chứng chỉ, hoặc cơ chế hoạt động thực tế.
6. **Xác lập Brand Voice & Positioning Statement**:
   - Công thức: *"Dành cho [ICP], [Sản phẩm] là giải pháp [Category] giúp [Lợi ích cốt lõi], khác biệt với [Giải pháp thay thế] nhờ [Luận điểm chứng minh]."*

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Mọi phân tích dựa trên dữ liệu ngữ cảnh được cung cấp trong hội thoại hoặc tài liệu dự án.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- **Phân tách rạch ròi Evidence vs Assumption**: Mỗi mục trong hồ sơ định vị phải được dán nhãn trạng thái:
  - `[Evidence]`: Có dữ liệu định lượng, trích dẫn phỏng vấn thật hoặc bản ghi giao dịch kiểm chứng được.
  - `[Assumption]`: Giả thuyết nội bộ của team, cần đưa vào `strategy.assumption-discovery` hoặc `strategy.experiment-design` để kiểm chứng.
- **Nghiêm cấm bịa đặt**: Tuyệt đối không tự bịa testimonial khách hàng, số liệu thị trường hay trích dẫn giả mạo.

## 7. Safe Fallback
Khi người dùng yêu cầu tự động cập nhật cơ sở dữ liệu định vị hoặc phát hành ra bên ngoài, agent nêu rõ: "Năng lực ghi tự động vào database chưa khả dụng trong giai đoạn này" và xuất toàn bộ nội dung dưới dạng bản thảo hoàn chỉnh để người dùng duyệt thủ công.

## 8. Định Dạng Đầu Ra (Output Format)
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
- **Push**: [Lực đẩy từ hiện trạng]
- **Pull**: [Lực kéo từ sản phẩm]
- **Anxiety**: [Lo lắng về rủi ro]
- **Inertia**: [Thói quen cũ]

## 5. Tuyên Bố Định Vị (Positioning Statement)
*"Dành cho [ICP], [Sản phẩm] là [Category] giúp [Lợi ích cốt lõi], khác với [Alternative] nhờ [Proof Point]."*

## 6. Backlog Giả Định Cần Kiểm Chứng
- [Danh sách các điểm dán nhãn Assumption cần lên kế hoạch test]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Sản phẩm phục vụ quá nhiều nhóm khách hàng**: Yêu cầu chọn 1 nhóm ICP ưu tiên số 1 (Primary ICP) để xây dựng định vị trước, không tạo định vị chung chung phục vụ "tất cả mọi người".
- **Không có dữ liệu thực tế**: Toàn bộ hồ sơ định vị phải được đánh dấu `[Assumption]` và khuyến nghị chạy `marketing.market-research` hoặc phỏng vấn sơ cấp.

## 10. Nguồn (Review Record)
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
    - Chuẩn hóa thuật ngữ COSA
    - Thêm cấu trúc 10 mục bắt buộc và định dạng markdown tiếng Việt
  added:
    - Phân loại bằng chứng rạch ròi Evidence vs Assumption
    - Safe fallback cơ chế tĩnh
    - Liên kết tới backlog kiểm chứng giả thuyết
  excluded:
    - Tự động ghi vào database hoặc xuất bản trang landing page trực tiếp
```
