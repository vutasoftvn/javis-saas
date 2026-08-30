---
name: discovery-assumption-prioritization
description: Xếp hạng ưu tiên giả định theo mức độ rủi ro tử huyệt (fatal if wrong)
  và mức độ thiếu bằng chứng.
---

# Assumption Risk Matrix Prioritization

## Mục đích & Giới hạn Quyền hạn
Xếp hạng ưu tiên giả định theo mức độ rủi ro tử huyệt (fatal if wrong) và mức độ thiếu bằng chứng.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Không tự thay đổi project lifecycle stage, không tự phê duyệt evidence/gate, không tự gọi external provider. Khi action cần quyền hoặc evidence đủ chuẩn, tạo proposal/handoff với ID evidence/artifact liên quan.

## Triggers
- Kích hoạt khi cần thực hiện nghiệp vụ `discovery.assumption-prioritization` trong giai đoạn P2_SOLUTION_VALIDATION.

## Anti-triggers
- Không kích hoạt ngoài phạm vi dự án hoặc khi thiếu ngữ cảnh `workspace_id` và `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- Danh sách giả định đã phân loại (đầu ra của `discovery.assumption-mapping`, hoặc tương đương do context cung cấp).

## Evidence Rules
- Tuân thủ nguyên tắc anti-self-validation: Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder/Admin trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Chấm điểm mức độ quan trọng (Importance)**: Với mỗi giả định, ước lượng thang 1-10 mức độ nghiêm trọng nếu giả định sai (fatal-if-wrong) — 10 là có thể làm sụp đổ toàn bộ mô hình kinh doanh.
2. **Chấm điểm mức độ chưa chắc chắn (Uncertainty)**: Ước lượng thang 1-10 mức độ thiếu bằng chứng hiện có cho giả định — 10 là hoàn toàn chưa có bằng chứng nào.
3. **Tính điểm rủi ro**: `riskScore = importance × uncertainty` (thang 1-100). Không tự ý gán điểm mà bỏ qua việc giải thích căn cứ ước lượng.
4. **Xếp hạng ma trận rủi ro**: Sắp xếp giả định giảm dần theo `riskScore`; nhóm giả định `riskScore` cao (góc phần tư "quan trọng + chưa chắc chắn") là ưu tiên kiểm chứng trước tiên.
5. **Đề xuất hành động tiếp theo**: Với nhóm ưu tiên cao nhất, khuyến nghị thiết kế thử nghiệm kiểm chứng (dùng `strategy.experiment-design` hoặc tương đương).

## Allowed Tool Calls
Không có công cụ trực tiếp (Artifact/Proposal only). Skill này hiện chưa có capability ghi dữ liệu vào hệ thống — mọi giả định là dự thảo văn bản do con người nhập lại nếu muốn lưu trữ chính thức.

## Output Format
```markdown
### Ma Trận Ưu Tiên Giả Định
- **Dự Án**: [ID / Tên dự án]
- **Xếp Hạng** (giảm dần theo Risk Score):
  1. **[Statement]** — Importance: [1-10], Uncertainty: [1-10], Risk Score: [importance × uncertainty]
- **Nhóm Ưu Tiên Kiểm Chứng Ngay**: [Danh sách giả định risk score cao nhất]
- **Hành Động Khuyến Nghị**: Thiết kế thử nghiệm kiểm chứng cho giả định rủi ro cao nhất trước.
```

## Fallback & Handoff
- Khi thiếu thông tin đủ để ước lượng chính xác: mặc định gán `importance=5`, `uncertainty=5` (mức trung bình) và ghi rõ đây là ước lượng tạm thời.
- Khi thiếu dữ liệu hoặc không đủ điều kiện an toàn, tạo thông báo Handoff đề xuất người dùng bổ sung thông tin.

## Eval Notes
- Suite: `evals/discovery/assumption-prioritization.yaml`
