---
name: product-continuous-discovery
description: Hướng dẫn duy trì thói quen khám phá khách hàng liên tục theo mô hình Opportunity Solution Tree.
---

# Quy Trình Khám Phá Liên Tục (Continuous Discovery Habits)

## 1. Mục Tiêu (Objective)
Duy trì nhịp tiếp xúc khách hàng định kỳ (tối thiểu 1-2 cuộc phỏng vấn/tuần) để liên tục phát hiện các cơ hội (Opportunities) và kiểm chứng giải pháp (Solutions) trước khi bắt tay vào lập trình.

## 2. Khi Nào Dùng & Khi Nào Không Dùng
- **Khi nào dùng**:
  - Đội ngũ sản phẩm muốn duy trì kết nối thực tế với nhu cầu của người dùng.
  - Cần cập nhật Opportunity Solution Tree dựa trên các câu chuyện thực tế gần nhất.
- **Khi nào KHÔNG dùng**:
  - Khi triển khai chiến dịch bán hàng trực tiếp (Outbound Sales).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `projectId` hợp lệ trong workspace.

## 4. Các Bước Thực Hiện (Deterministic Steps)
1. **Rà soát bằng chứng đã có**: Gọi `strategy.evidence.list` để cập nhật kho tri thức hiện tại.
2. **Khai thác câu chuyện khách hàng (Story-based Interview)**:
   - Tập trung vào hành vi đã xảy ra trong quá khứ gần (*"Hãy kể cho tôi lần gần nhất bạn gặp vấn đề X..."*), không hỏi về mong muốn tương lai.
3. **Cập nhật Opportunity Solution Tree**:
   - Gắn kết quả phỏng vấn vào một cơ hội cụ thể (Pain point, Need, Desire).
4. **Tạo Evidence Candidate**: Gọi `strategy.evidence.create` để đưa bằng chứng vào hệ thống quản trị chiến lược.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `strategy.evidence.list`: Đọc danh sách bằng chứng hiện tại.
- `strategy.evidence.create`: Tạo bản ghi bằng chứng mới.

## 6. Điểm Phê Duyệt (Approval Points)
- Bằng chứng mới luôn được tạo ở trạng thái `candidate` chờ Founder/DRI phê duyệt.

## 7. Định Dạng Đầu Ra (Output Format)
```markdown
### Bản Ghi Nhận Khám Phá Liên Tục (Weekly Discovery Log)
- **Dự Án**: [ID / Title]
- **Khách Hàng Phỏng Vấn**: [Segment / Persona]
- **Câu Chuyện Đã Ghi Nhận**: [Tóm tắt hành vi thực tế]
- **Cơ Hội Được Nhận Diện (Opportunity)**: [Mô tả nhu cầu/nỗi đau]
- **Bằng Chứng Tạo Mới**: `candidate`
```
