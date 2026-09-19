---
name: operations-loop-lifecycle
description: Phương pháp luận quản trị vòng đời vòng lặp tự hành (Loop Lifecycle), khám phá tác vụ lặp lại từ codebase, kiểm toán sửa chữa điểm yếu vòng lặp (Loop Doctor), và phỏng vấn thiết kế chu trình phản hồi hữu hạn.
---

# Quản Trị Vòng Đời Vòng Lặp Tự Hành (Autonomous Loop Lifecycle & Doctor)

## 1. Mục Tiêu (Objective)
Thiết lập phương pháp luận và quy chuẩn thiết kế các vòng lặp tự hành (AI-Agent Loops) cho hệ thống COSA. Khẳng định nguyên tắc cốt lõi: **Vòng lặp là một hệ thống phản hồi có biên giới và có điểm dừng hữu hạn (Bounded Feedback System with Terminal States), tuyệt đối không phải giấy phép cho sự tự trị vô tận (Endless Autonomy)**. Cung cấp 5 năng lực: Khám phá (Discover), Tra cứu (Find), Kiểm toán sửa chữa (Loop Doctor / Audit), Hiệu chỉnh (Adapt), và Phỏng vấn thiết kế (Design Interview).

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi muốn đào bới mã nguồn dự án, cấu hình CI/CD hoặc nhật ký hội thoại để tìm các tác vụ lặp lại $\ge 2$ lần có thể đóng gói thành vòng lặp (Discover).
  - Khi cần chẩn đoán và khắc phục điểm yếu của một prompt/automation đang chạy (Loop Doctor) như: vòng lặp chạy mãi không dừng, tự chấm điểm bài làm của mình, hoặc đọc dữ liệu cũ trước khi ghi.
  - Khi người dùng muốn thiết kế một quy trình tự động hóa định kỳ mới thông qua phỏng vấn 5 câu hỏi ngắn gọn.
- **Khi nào KHÔNG dùng**:
  - Khi tác vụ chỉ chạy 1 lần không cần phản hồi hay lặp lại (dùng One-shot Workflow thay vì ép thành vòng lặp).
  - Khi cần cấu hình khóa phân tán kỹ thuật (RunLease) hoặc tính lũy đẳng (Idempotency) ở tầng hạ tầng backend (dùng `operations.loop-hardening`).
  - Khi tự ý kích hoạt các hành động phá hủy, chi tiêu tài chính hoặc gửi tin nhắn ra bên ngoài mà không có chốt phê duyệt con người.

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Ngữ cảnh bắt buộc: `workspace_id`, `project_id`.
- Nắm vững 6 trạng thái kết thúc chuẩn `LoopTerminalState` trong `agent.workflows.schema`: `SUCCESS`, `NOOP`, `BLOCKED`, `NEED_APPROVAL`, `EXHAUSTED`, `STAGNATED`.
- Hiểu rõ nguyên tắc phân tách giữa người làm (`ActStep`) và người thẩm định (`VerifyStep`).

## 4. Các Bước Tất Định (Deterministic Steps)
Chu trình phản hồi chuẩn của một vòng lặp tự hành gồm 6 bước bắt buộc:
1. **Quan Sát (Observe)**: Đọc trạng thái mới nhất từ hệ thống (Fresh State) và thu thập bằng chứng đã thống nhất. Tuyệt đối không dựa vào giả định cũ từ vòng lặp trước.
2. **Lựa Chọn (Choose)**: Chọn 1 hành động có giá trị cao nhất trong phạm vi cho phép dựa trên tiêu chí rõ ràng.
3. **Thực Hiện (Act)**: Thực thi một thay đổi có giới hạn, có thể hoàn tác được (Reversible) hoặc tạo ra một bản nháp ứng viên (`candidate`).
4. **Thẩm Định Độc Lập (Verify)**: Chạy chốt kiểm tra nghiệm thu độc lập với người thực hiện. Nghiêm cấm việc Agent tự đánh giá kết quả của chính mình (No Self-Grading).
5. **Ghi Nhận (Record)**: Lưu vết hành động, bằng chứng, kết quả và các công việc còn lại vào nhật ký kiểm toán (Audit Trail).
6. **Lặp Lại Hoặc Dừng (Repeat or Stop)**:
   - Tiếp tục lặp lại nếu có tiến triển đo lường được và chưa chạm trần ngân sách/số lần retry.
   - Nếu không, bắt buộc chuyển sang đúng 1 trong 6 trạng thái kết thúc (`LoopTerminalState`):
     - `SUCCESS`: Mục tiêu đã hoàn thành xuất sắc.
     - `NOOP`: Kiểm tra thấy không có việc cần làm (hệ thống đã sạch).
     - `BLOCKED`: Tắc nghẽn do thiếu tài nguyên hoặc phụ thuộc ngoài.
     - `NEED_APPROVAL`: Đang chờ con người phê duyệt hành động rủi ro.
     - `EXHAUSTED`: Đã chạm trần số lần thử lại hoặc ngân sách chi phí.
     - `STAGNATED`: Không tạo ra tiến triển mới giữa 2 vòng lặp liên tiếp.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Quy trình được thực thi và kiểm thử thông qua các module chuẩn của agent.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Khi khẳng định một tác vụ có cơ hội tạo vòng lặp (Discover), bắt buộc phải trích dẫn ít nhất 2 lần xuất hiện thực tế riêng biệt từ codebase (script, CI, test, runbook) hoặc log thao tác.
- Báo cáo chẩn đoán Loop Doctor phải nêu rõ lỗi anti-pattern cụ thể cùng nguyên nhân gốc rễ.

## 7. Safe Fallback & Nghiêm Cấm Anti-Patterns (Loop Doctor Rules)
- **CẤM TỰ CHẤM ĐIỂM (Zero Self-Grading):** Agent thực hiện thay đổi không được phép tự quyết định nghiệm thu thay đổi đó. Phải có bước Verify độc lập.
- **CẤM OVERFITTING TRÊN CÙNG TÍN HIỆU:** Không được tối ưu hóa và nghiệm thu trên cùng một tập dữ liệu/tiêu chí đánh giá.
- **CẤM RETRY VÔ TẬN (No Infinite Loops):** Luôn có điều kiện dừng khi không có tiến triển (No-progress stop / Stagnation threshold).
- **CẤM ĐỌC DỮ LIỆU CŨ (Zero Stale State Reads):** Bắt buộc phải đọc lại fresh state trước các hành động ghi có ảnh hưởng lớn.

## 8. Định Dạng Đầu Ra (Output Format)
Khi người dùng yêu cầu kiểm toán hoặc thiết kế vòng lặp mới, kết xuất định dạng cô đọng:

```markdown
## [Tên Vòng Lặp]

[Một câu giải thích rõ vòng lặp làm gì và điều kiện nào nó sẽ dừng.]

Prompt:
> [Một đoạn văn ngắn gọn, độc lập dưới 80 từ: Làm tác vụ gì, kiểm tra bằng chốt nào, dừng khi nào, và xin phép con người trước khi làm gì.]

### Báo Cáo Kiểm Toán Vòng Lặp (Nếu là chế độ Loop Doctor)
- **Chu trình phản hồi 6 bước**: [Hợp lệ / Cần khắc phục]
- **Trạng thái kết thúc chuẩn**: [Liệt kê các terminal state được xử lý]
- **Chốt thẩm định độc lập**: [Có / Không]
- **Các lỗi vi phạm đã sửa**: [Danh sách lỗi anti-pattern]
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Vòng lặp bị đình trệ (Stagnation)**: Khi 2 chu kỳ liên tiếp không tạo ra sự cải thiện nào về chỉ số, lập tức chuyển sang trạng thái `STAGNATED` và tạo thông báo Handoff cho con người thay vì tiếp tục thử lại mù quáng.
- **Mất ngữ cảnh giữa các chu kỳ**: Ghi checkpoint đầy đủ vào cơ sở dữ liệu để chu kỳ tiếp theo có thể khôi phục chính xác trạng thái dở dang.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: loop-library
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - 5 chế độ làm việc: Discover, Find, Audit (Loop Doctor), Adapt, Design
    - Chu trình phản hồi 6 bước (Observe, Choose, Act, Verify, Record, Repeat/Stop)
    - 6 trạng thái kết thúc tường minh và nguyên tắc thẩm định độc lập
  changed:
    - Chuyển đổi sang quy chuẩn 10 mục COSA tiếng Việt
    - Tích hợp với hệ thống trạng thái enum LoopTerminalState trong packages/agent/workflows/schema.py
  added:
    - Phân định rõ 3 tầng: Vòng lặp chiến lược 12WY, Vòng lặp phản hồi Agent, và Hạ tầng khóa phân tán loop-hardening
    - Cơ chế tự động phát hiện đình trệ (Stagnated state detection)
  excluded:
    - Bỏ việc phụ thuộc vào catalog trực tuyến bên thứ ba khi chạy offline
```
