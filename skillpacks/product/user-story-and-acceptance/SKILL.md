---
name: product-user-story-and-acceptance
description: Phân rã tính năng thành các User Story chi tiết theo lát cắt dọc (Vertical Slicing), 8 mẫu phân tách câu chuyện, và tiêu chí nghiệm thu kiểm thử được theo cú pháp Given-When-Then.
---

# User Stories & Tiêu Chí Nghiệm Thu (User Story & Acceptance Criteria)

## 1. Mục đích & Giới hạn Quyền hạn
Chuyển hóa các yêu cầu từ PRD thành các User Stories có thể kiểm thử độc lập (Independent), mang lại giá trị trọn vẹn từ giao diện đến dữ liệu (Vertical Slicing), áp dụng chuẩn cú pháp Mike Cohn và tiêu chuẩn nghiệm thu Given-When-Then chặt chẽ cho đội ngũ kỹ thuật trong P3_BUILD_VALIDATE.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo tài liệu đặc tả User Stories (Artifact/Proposal ở mức L1_PROPOSE). Tuyệt đối không tự ý thao tác tạo/sửa issue trên GitHub/Jira hay sửa đổi mã nguồn.

## 2. Triggers
- Kích hoạt khi cần phân rã tính năng từ PRD thành các đầu việc nhỏ gọn (1-5 ngày công) cho sprint phát triển.
- Kích hoạt khi một câu chuyện người dùng quá lớn, mơ hồ hoặc chứa nhiều kịch bản cần xẻ nhỏ.

## 3. Anti-triggers & Ranh Giới Kỹ Thuật
- **Cấm Phân Tách Ngang (Horizontal Slicing):** Tuyệt đối không chia việc theo tầng kiến trúc ("Viết API backend", "Dựng giao diện frontend", "Thiết kế bảng CSDL"). Mỗi story phải là một lát cắt dọc (Vertical Slice) hoàn chỉnh mang lại giá trị quan sát được cho người dùng.
- **Cấm "As a user" vô danh:** Bắt buộc định danh Persona cụ thể ("As a mid-market ops manager", "As a trial user").
- **Cấm "So that" lặp lại hành động:** Phần "So that" phải nêu rõ động lực/kết quả thực tế, không được lặp lại nội dung của "I want to".
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## 4. Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `prd_reference`: Tài liệu PRD hoặc Epic hypothesis gốc.

## 5. Evidence Rules
- Mỗi User Story phải liên kết trực tiếp với mục tiêu giải quyết nỗi đau của khách hàng trong PRD.
- Các tiêu chí nghiệm thu (Acceptance Criteria) phải khách quan, kiểm thử được bởi QA/kỹ sư, không chứa tính từ cảm tính ("nhanh hơn", "mượt mà hơn").

## 6. Quy trình thực hiện & 8 Kỹ Thuật Xẻ Nhỏ Câu Chuyện (Vertical Slicing)
Áp dụng tuần tự 8 mẫu phân tách (Richard Lawrence / Humanizing Work) khi gặp câu chuyện lớn:
1. **Workflow Steps**: Tách theo chuỗi luồng thao tác người dùng (tạo lát cắt mỏng xuyên suốt end-to-end trước, sau đó bổ sung độ tinh vi).
2. **Business Rules**: Mỗi biến thể quy tắc nghiệp vụ là một story riêng (ví dụ: áp dụng voucher thông thường vs voucher giới hạn giờ).
3. **Data Variations**: Tách theo kiểu dữ liệu hỗ trợ (xử lý định dạng văn bản/CSV đơn giản trước, định dạng phức tạp/PDF sau).
4. **Acceptance Criteria Complexity**: Khi story có nhiều cặp When/Then, tách mỗi cặp thành một story độc lập.
5. **Major Effort vs Simple Additions**: Làm phần lõi khó đầu tiên, sau đó các tiện ích bổ sung tách riêng.
6. **External Dependencies**: Tách theo ranh giới tích hợp API bên ngoài.
7. **DevOps & Operations**: Tách phần triển khai cơ bản trước, phần mở rộng tự động hóa sau.
8. **Tiny Acts of Discovery (Spike)**: Khi mức độ bất định quá cao, đóng khung một đợt thử nghiệm ngắn có giới hạn thời gian (Time-boxed) thay vì phỏng đoán.

### Cấu Trúc Story Chuẩn (Mike Cohn + Gherkin):
```markdown
### US-[ID]: [Tiêu đề hành động ngắn gọn]
**As a** [Persona cụ thể có đặc điểm hành vi],
**I want to** [hành động cụ thể],
**So that** [giá trị nghiệp vụ hoặc cảm xúc được giải phóng].

#### Acceptance Criteria:
Scenario: [Mô tả kịch bản kiểm thử]
Given [Điều kiện tiền đề - có thể có nhiều Given]
When [Sự kiện kích hoạt duy nhất tương ứng với hành động]
Then [Kết quả đầu ra có thể quan sát được tương ứng với giá trị]

#### Edge Cases & Ràng buộc:
- Xử lý khi mất mạng, dữ liệu rỗng, vượt quota hoặc quyền bị từ chối.
```

## 7. Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## 8. Output Format
- **user-stories-document**: Bản danh sách User Stories phân rã theo lát cắt dọc, đánh số thứ tự ưu tiên, kèm ma trận nghiệm thu Given-When-Then chuẩn QA.

## 9. Fallback & Handoff
- Khi các ràng buộc kỹ thuật chưa rõ, tách thành 1 Spike Discovery (1-2 ngày) và handoff cho Tech Lead phản biện trước khi chốt sprint.

## 10. Eval Notes
- Suite: `evals/product/user-story-and-acceptance.yaml`
