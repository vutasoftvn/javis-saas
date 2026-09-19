---
name: people-internal-comms
description: Xây dựng thông điệp truyền thông nội bộ và kế hoạch triển khai thay đổi (Change Management) theo mô hình ADKAR và Kotter 8-step cho các đợt tái cấu trúc, đổi chính sách hoặc ra mắt quy trình mới.
---

# Truyền Thông Thay Đổi Nội Bộ & Quản Trị Chuyển Đổi (Internal Change Communications)

## 1. Mục Tiêu (Objective)
Cung cấp phương pháp xây dựng thông điệp và kế hoạch truyền thông nội bộ có hệ thống khi doanh nghiệp tiến hành các thay đổi lớn: tái cơ cấu phòng ban (Re-org), áp dụng chính sách làm việc/đãi ngộ mới, thay đổi công cụ phần mềm làm việc, hoặc chuyển dịch quy trình. Áp dụng khung chuyển đổi **ADKAR** (*Awareness, Desire, Knowledge, Ability, Reinforcement*) và mô hình **Kotter 8-step** để hạn chế tối đa sự kháng cự và hoang mang trong nội bộ.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi chuẩn bị công bố một quyết định thay đổi quan trọng ảnh hưởng đến thói quen làm việc hoặc quyền lợi của đội ngũ nhân sự.
  - Khi cần lập lịch trình truyền thông phân tầng (Leadership $\rightarrow$ Managers $\rightarrow$ Toàn thể nhân viên).
  - Khi soạn thảo kịch bản hỏi đáp (Q&A / FAQ) trước các câu hỏi khó của nhân viên.
- **Khi nào KHÔNG dùng**:
  - Khi soạn thông điệp quảng cáo, marketing ra bên ngoài hoặc thông cáo báo chí (dùng `marketing.*`).
  - Khi xử lý văn bản thỏa thuận chấm dứt hợp đồng lao động cá nhân riêng biệt (dùng `people.hiring-copilot` hoặc `chro-advisor`).
  - Khi tự ý bắn thông báo hàng loạt qua email hoặc Slack mà không có sự phê duyệt của Founder / CHRO.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Ngữ cảnh: `workspace_id`, `project_id`.
- Dữ liệu đầu vào: Bản chất của sự thay đổi, lý do tại sao phải thay đổi (Why now), thời điểm có hiệu lực, đối tượng chịu tác động trực tiếp, và các kênh hỗ trợ.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Xác Định Bản Chất Thay Đổi & Nhóm Bị Tác Động**:
   - Phân loại mức độ nhạy cảm của thông tin: Cao (tái cấu trúc, thay đổi lãnh đạo, cắt giảm chi phí), Trung bình (đổi công cụ, cập nhật quy trình), Thấp (thay đổi hành chính nhỏ).
   - Liệt kê các nhóm nhân sự chịu ảnh hưởng trực tiếp và gián tiếp.
2. **Cấu Trúc Thông Điệp Theo Khung ADKAR**:
   - **Awareness (Nhận thức)**: Tại sao thay đổi này là bắt buộc đối với sự sống còn/tăng trưởng của công ty? Nếu không thay đổi thì hậu quả là gì?
   - **Desire (Mong muốn)**: Lợi ích của thay đổi này đối với tương lai và đối với từng cá nhân ("What's in it for me?").
   - **Knowledge (Kiến thức)**: Nhân sự cần học kỹ năng gì mới hoặc làm việc theo quy trình mới nào?
   - **Ability (Năng lực)**: Các buổi đào tạo, tài liệu hướng dẫn, và ai là người hỗ trợ khi gặp khó khăn?
   - **Reinforcement (Củng cố)**: Cơ chế ghi nhận và các mốc đánh giá hiệu quả sau 30-60-90 ngày.
3. **Thiết Lập Lịch Trình Truyền Thông Phân Tầng (Cascade Calendar)**:
   - *T-7 ngày*: Họp kín với cấp quản lý trực tiếp (Managers) để họ hiểu rõ lý do và chuẩn bị giải đáp cho cấp dưới.
   - *T-0*: Công bố toàn thể (All-hands meeting hoặc thông báo chính thức).
   - *T+1 đến T+14*: Mở phiên hỏi đáp mở (Office Hours / AMA) và kênh tiếp nhận phản hồi ẩn danh.
4. **Chuẩn Bị Bộ Câu Hỏi Khó & Giải Đáp (Anticipated Q&A)**:
   - Liệt kê ít nhất 5 câu hỏi nhạy cảm nhất mà nhân viên chắc chắn sẽ đặt ra và chuẩn bị câu trả lời chân thành, minh bạch, không né tránh.
5. **Đóng Gói Kế Hoạch Truyền Thông Artifact**: Kết xuất tài liệu `internal-comms-brief` trình Founder và CHRO duyệt trước khi phát lệnh.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Quy trình được thực thi và kiểm thử thông qua các module chuẩn của agent.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mọi thông báo thay đổi phải gắn với mục tiêu chiến lược của chu kỳ 12-Week Year hiện tại.
- Kế hoạch phải chỉ định rõ người đại diện phát ngôn chính thức.

## 7. Safe Fallback & Nghiêm Cấm Anti-Patterns
- **CẤM THÔNG BÁO ĐỘT NGỘT KHÔNG NÊU LÝ DO (No "Why" Anti-Pattern):** Ra thông báo thay đổi quy trình hoặc chính sách mà chỉ đưa ra mệnh lệnh thực thi mà không giải thích bối cảnh "Tại sao".
- **CẤM BỎ QUA CẤP QUẢN LÝ TRỰC TIẾP:** Bắn thông báo đến toàn thể nhân viên trước khi đội ngũ Managers được thông tin và đào tạo kịch bản xử lý phản ứng.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Kế Hoạch Truyền Thông Thay Đổi Nội Bộ (Internal Change Comms Brief)

## 1. Tổng Quan Sự Thay Đổi
- **Tiêu đề thông báo**: [Tiêu đề thông điệp]
- **Người phát ngôn đại diện**: [Founder / CHRO / Head of Ops]
- **Mức độ tác động**: [Cao / Trung bình / Thấp]
- **Ngày công bố chính thức**: [YYYY-MM-DD]

## 2. Bản Thảo Thông Điệp Chính (ADKAR Message)
- **Lý do thay đổi (Awareness)**: [Bối cảnh và tính cấp bách]
- **Lợi ích mang lại (Desire)**: [Giá trị lâu dài cho công ty và nhân sự]
- **Hành động cụ thể (Knowledge & Ability)**: [Các bước cần thực hiện và tài liệu đi kèm]
- **Kênh hỗ trợ (Reinforcement)**: [Đầu mối hỗ trợ, Office Hours]

## 3. Lịch Trình Truyền Thông Phân Tầng (Rollout Cascade)
| Thời Điểm | Kênh Truyền Thông | Đối Tượng Nhận | Mục Tiêu |
|---|---|---|---|
| T-3 ngày | Họp Managers Sync | Quản lý cấp trung | Đồng thuận kịch bản và chuẩn bị Q&A |
| T-0 | All-hands + Email | Toàn thể công ty | Công bố chính thức |
| T+7 ngày | AMA Session | Toàn thể công ty | Giải đáp thắc mắc phát sinh |

## 4. Kịch Bản Q&A Trả Lời Các Câu Hỏi Nhạy Cảm
- **Q1**: [Câu hỏi hóc búa 1]?
  - *Trả lời*: [Câu trả lời minh bạch, thẳng thắn]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Rò rỉ thông tin trước ngày công bố chính thức (Leak)**: Kích hoạt kế hoạch phản ứng nhanh, đẩy sớm lịch công bố All-hands trong vòng 24 giờ để tránh tin đồn thất thiệt.
- **Phản ứng tiêu cực gay gắt từ một nhóm nhân sự**: Tổ chức gặp mặt riêng 1-on-1 với đại diện nhóm để lắng nghe và điều chỉnh lộ trình chuyển đổi linh hoạt.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: internal-comms
  upstream_version: 2.8.0
  license: MIT
adaptation:
  kept:
    - Mô hình quản trị chuyển đổi ADKAR và Kotter 8-step
    - Cơ chế truyền thông phân tầng (Manager cascade) và chuẩn bị kịch bản câu hỏi khó
  changed:
    - Chuyển đổi sang quy chuẩn 10 mục COSA tiếng Việt
    - Liên kết với mục tiêu văn hóa và con người của CHRO Advisor
  added:
    - Quy trình phản ứng khẩn cấp khi bị rò rỉ thông tin trước giờ G
  excluded:
    - Bỏ các script shell gửi thông báo trực tiếp qua webhook
```
