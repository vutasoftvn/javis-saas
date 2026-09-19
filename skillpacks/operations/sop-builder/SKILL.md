---
name: operations-sop-builder
description: Xây dựng và thẩm định tài liệu Standard Operating Procedure (SOP) và Runbook vận hành theo chuẩn 5W2H, kiểm định 6 tiêu chí an toàn bắt buộc trước khi ban hành.
---

# Quy Trình Xây Dựng & Thẩm Định SOP / Runbook Vận Hành (5W2H Standard)

## 1. Mục Tiêu (Objective)
Chuyển hoá một quy trình vận hành đã lặp lại (repeatable workflow) thành tài liệu SOP / Runbook có cấu trúc chặt chẽ theo chuẩn **5W2H** (*Who, What, Where, When, Why, How, How much*). Bắt buộc thẩm định độ phủ của 6 tiêu chí an toàn trước khi đề xuất ban hành: Người chịu trách nhiệm cụ thể (`named_owner`), Thời lượng dự kiến (`expected_duration`), Tín hiệu thành công quan sát được (`success_signal`), Tín hiệu lỗi (`failure_signal`), Quy trình hoàn tác (`rollback_path`), và Đầu mối liên hệ khẩn cấp (`escalation_contact`).

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Chuẩn hoá một quy trình vận hành thực tế đã chạy lặp lại $\ge 2$ lần thành văn bản SOP chính thức phục vụ bàn giao và đào tạo.
  - Soạn thảo và kiểm tra độ an toàn của Runbook ứng cứu sự cố kỹ thuật hoặc tác vụ bảo trì định kỳ.
  - Chuẩn bị tài liệu vận hành cho stage gate `G6_SCALE_GOVERN` để chứng minh năng lực kiểm soát chất lượng.
- **Khi nào KHÔNG dùng**:
  - Khi quy trình chưa từng được thực thi trên thực tế (dùng `operations.automation-design` để thiết kế thử nghiệm).
  - Khi chưa xác định được cá nhân hoặc chức danh chịu trách nhiệm sở hữu quy trình (`process_owner`).
  - Khi muốn tự động ban hành chính thức mà không qua phê duyệt của con người (vi phạm nguyên tắc `L1_PROPOSE`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Yêu cầu ngữ cảnh: `workspace_id`, `project_id` hợp lệ.
- Yêu cầu người phụ trách: `process_owner` được chỉ định rõ danh tính hoặc chức danh, tuyệt đối không gán chung chung ("the team", "ops", "ai").
- Hiểu rõ bộ quy tắc kiểm định của `Runbook5W2HValidator` (`agent.operations.analyzers.runbook_5w2h_validator`).

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Xác định Phạm Vi & Process Owner**: Thu thập tên quy trình, phạm vi áp dụng, tần suất thực thi và Process Owner chịu trách nhiệm duy trì tài liệu.
2. **Liệt Kê Các Bước Theo Dòng Chảy Thực Tế**: Ghi nhận tuần tự từng bước kèm thời lượng ước tính (`expected_duration_minutes`).
3. **Thiết Lập Bộ Đôi Tín Hiệu Thẩm Định (Dual Signals)**: Với mỗi bước, bắt buộc định nghĩa:
   - *Observable Success Signal*: Dấu hiệu xác nhận bước đã thành công (log, metric, trạng thái UI).
   - *Observable Failure Signal*: Dấu hiệu nhận biết bước đã thất bại để lập tức dừng lại.
4. **Xác Định Đường Hoàn Tác & Đầu Mối Khẩn Cấp**:
   - Ghi rõ lệnh/thao tác rollback về trạng thái an toàn. Nếu bước không thể rollback, phải ghi rõ lý do và hành động giảm thiểu thiệt hại.
   - Chỉ định rõ tên/kênh liên hệ khẩn cấp (`escalation_contact`).
5. **Thẩm Định Tự Động Qua Runbook5W2HValidator**:
   - Chạy hàm kiểm định vệ sinh tài liệu. Chỉ chấp nhận các SOP đạt mức `SAFE-TO-USE` (Điểm vệ sinh $\ge 80/100$ và không còn lỗi nghiêm trọng).
6. **Đóng Gói Bản Thảo Artifact**: Kết xuất tài liệu `sop-draft` kèm báo cáo thẩm định vệ sinh để Process Owner phê duyệt.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Quy trình được thực thi và kiểm thử thông qua các module chuẩn của agent.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Bản nháp SOP phải dẫn xuất từ bằng chứng vận hành: nhật ký thực thi (log), biên bản họp, phỏng vấn nhân sự hoặc tài liệu runbook cũ.
- Mọi bản nháp phải đính kèm bảng điểm vệ sinh 5W2H với đầy đủ 6 tiêu chí.

## 7. Safe Fallback & Nghiêm Cấm Anti-Patterns
- **CẤM TÊN PHỤ TRÁCH MƠ HỒ (Zero Vague Owners):** Cấm ghi "team", "ops", "mọi người" hay "AI" làm owner của bước.
- **CẤM RUNBOOK CHỈ CÓ HAPPY-PATH:** Runbook không có tín hiệu lỗi hoặc không có phương án hoàn tác sẽ bị gắn nhãn NOT-SAFE và từ chối đề xuất.
- **CẤM TỰ ĐỘNG BAN HÀNH:** Mọi tài liệu sinh ra chỉ ở trạng thái sop-draft hoặc candidate, bắt buộc phải có chữ ký duyệt của con người.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# [Tên SOP / Runbook]

## 1. Thông Tin Chung
- **Process Owner**: [Tên / Chức danh cụ thể]
- **Mục Tiêu**: [Mô tả mục tiêu 5W2H]
- **Phạm Vi**: [Hệ thống / Đội ngũ áp dụng]
- **Điểm Vệ Sinh (5W2H Score)**: [XX/100] — [SAFE-TO-USE | USE-WITH-CAUTION]

## 2. Bảng Các Bước Thực Thi Chuẩn
| Bước | Hành Động | Người Thực Hiện | Thời Lượng | Tín Hiệu Thành Công | Tín Hiệu Thất Bại | Phương Án Hoàn Tác | Đầu Mối Khẩn Cấp |
|---|---|---|---|---|---|---|---|
| 1 | [Tên bước] | [Named Owner] | [X phút] | [Observable signal] | [Error signal] | [Rollback path] | [Escalation contact] |

## 3. Báo Cáo Thẩm Định An Toàn (Validation Report)
- **Trạng thái**: [SAFE-TO-USE]
- **Số bước hợp lệ**: [N/N]
- **Khuyến nghị cải tiến**: [Ghi chú nếu có]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Quy trình không thể rollback (Non-reversible action)**: Bắt buộc chèn một bước kiểm tra điều kiện tiên quyết (Pre-flight Confirmation) và yêu cầu phê duyệt 2 người (Two-person rule) trước khi thực hiện.
- **Không tìm được Process Owner**: Tạm dừng quy trình, chuyển sang trạng thái Handoff để Founder chỉ định nhân sự sở hữu trước khi tiếp tục.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: knowledge-ops
  upstream_version: 2.8.0
  license: MIT
adaptation:
  kept:
    - 6 tiêu chuẩn vệ sinh runbook (Named owner, Expected duration, Success signal, Failure signal, Rollback path, Escalation contact)
    - Nguyên tắc thẩm định 5W2H và chống tài liệu rác mồ côi (KB hygiene)
  changed:
    - Chuyển đổi sang quy chuẩn 10 mục COSA tiếng Việt
    - Liên kết chặt chẽ với trần tự trị L1_PROPOSE và giai đoạn P6_SCALE_GOVERN
  added:
    - Tích hợp trực tiếp với Runbook5W2HValidator trong packages/agent/operations/analyzers
    - Quy chuẩn hai người duyệt cho các bước không thể rollback
  excluded:
    - Loại bỏ các lệnh shell tùy tiện; tích hợp vào pipeline kiểm thử tĩnh của COSA
```
