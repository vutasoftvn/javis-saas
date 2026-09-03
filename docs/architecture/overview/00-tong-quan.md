# COSA — Tổng quan chức năng & workflow

> Bộ tài liệu này mô tả **COSA làm gì và vận hành như thế nào**, dành cho
> founder/người không chuyên kỹ thuật đọc trước, engineer đọc sâu hơn ở các
> phần kỹ thuật. Đây là tài liệu tham chiếu sống — khi kiến trúc thay đổi,
> cập nhật lại phần tương ứng thay vì viết tài liệu mới.
>
> Trạng thái viết: 2026-09-03, dựa trên khảo sát trực tiếp mã nguồn (không
> dựa vào tài liệu cũ chưa xác minh).

## COSA là gì

COSA là **Founder / Company Operating System với Agent Platform composable**.
Đây **không phải** một tập hợp các AI agent độc lập, mà là một hệ điều hành
cho công ty: nghiệp vụ (chiến lược, thương mại, tài chính-pháp lý, vận hành)
được mô hình hoá thành dữ liệu và quy trình có cấu trúc trong các service
nghiệp vụ, còn Agent Platform là lớp thực thi — nơi cả **con người và AI**
cùng đứng trong một mô hình nhân sự duy nhất (`WorkforceMember`) để thực hiện
công việc trên nền nghiệp vụ đó, có kiểm soát (governance) và có thể kiểm
toán lại (audit).

## Bốn vùng kiến trúc

```text
Experience Plane      Flutter (chat, voice, API)              → xem 04, 02
COSA Control Plane    services/cosa      (Encore/TS)          → xem 01
Company Business      services/company   (Encore/TS)          → xem 01, 02
Agent Platform        packages/agent (Python, dùng lại được)  → xem 01, 03
                       + apps/cosa (Python, ghép nối 2 phía)
```

Nguyên tắc phân lớp:

- **Business truth** (sự thật nghiệp vụ) nằm ở `services/company` và
  `services/cosa` (TypeScript/Encore) — không nằm ở LLM runtime. Agent
  Platform không tự quyết định authorization hay ghi thẳng vào DB nghiệp vụ;
  mọi tác động phải qua Capability Layer + Governance + Audit (xem file 03).
- `packages/agent/` là framework Python **tái dùng được**, không được import
  bất cứ gì từ `services/company/*`.
- `apps/cosa/` (Python) là lớp **ghép nối** — nơi duy nhất được compose cả
  Agent Platform lẫn Company Business, gọi HTTP/RPC sang `services/company`
  và `services/cosa`.
- `legacy/` đã bị xoá hẳn từ 2026-08-25; mọi runtime hiện hoạt nằm ở
  `packages/agent/` và `apps/cosa/`.

## Chú giải thuật ngữ quan trọng — 3 nghĩa của "cosa"

Tên "cosa" xuất hiện với **3 nghĩa khác nhau** trong repo, dễ gây nhầm lẫn
khi đọc tài liệu hoặc ADR:

| Tên gặp trong repo | Là gì | Vai trò |
|---|---|---|
| `services/cosa` | Service TypeScript/Encore, 1 service phẳng | **COSA Control Plane**: identity nền tảng, license/plan, workspace membership, runtime leasing, scheduler, mission/task/worker |
| `apps/cosa` | Package Python | **Agent Plane composition**: nơi Agent Platform (`packages/agent`) được ghép với nghiệp vụ — chạy FastAPI server, worker process, agent specs của COSA |
| "COSA" (không có đường dẫn) | Tên thương hiệu/toàn bộ hệ thống | Toàn bộ dự án nói chung |

Nhiều ADR đang mô tả hành vi của **`apps/cosa`** (Python, Agent Plane) chứ
không phải `services/cosa` (TS, Control Plane) — ví dụ `ADR-CONV-001`,
`ADR-DEPLOY-001`, `ADR-AGENT-REG-001`. Khi đọc một ADR nhắc tới "cosa", cần
xác định rõ đang nói tới vùng nào bằng cách kiểm tra file/đường dẫn được
trích trong ADR đó.

## Cách đọc bộ tài liệu này

| File | Nội dung | Đọc khi nào |
|---|---|---|
| [01-bon-vung-kien-truc.md](01-bon-vung-kien-truc.md) | Kiến trúc kỹ thuật của từng vùng (service, module, endpoint chính) | Muốn biết "cái gì nằm ở đâu" |
| [02-workflow-nghiep-vu.md](02-workflow-nghiep-vu.md) | Luồng nghiệp vụ từ góc nhìn founder — không cần đọc code | Muốn hiểu COSA giúp vận hành công ty ra sao |
| [03-agent-va-governance.md](03-agent-va-governance.md) | Agent Platform đi sâu: AgentSpec, capability, governance/approval | Engineer làm việc với agent runtime |
| [04-trai-nghiem-nguoi-dung.md](04-trai-nghiem-nguoi-dung.md) | Ứng dụng Flutter, các module, kiến trúc voice thực tế | Muốn biết người dùng cuối thấy gì |
| [05-khuyen-nghi.md](05-khuyen-nghi.md) | Phát hiện khi khảo sát + đề xuất điều chỉnh, phân loại mức ưu tiên | Lên kế hoạch dọn nợ kỹ thuật/tài liệu |

## Nguồn khác — không lặp lại ở đây

Bộ tài liệu này **không thay thế** các nguồn sau, chỉ trỏ tới khi cần chi
tiết:

- `docs/architecture/adr/` — các quyết định kiến trúc đã/đang chốt (ACCEPTED
  không đồng nghĩa đã triển khai xong — xem Nhóm D trong file 05).
- `docs/architecture/generated/route-inventory.md` — danh sách đầy đủ mọi
  route HTTP của `services/company` + `services/cosa` (sinh tự động).
- `docs/architecture/generated/company-usage-inventory.md` — phân loại
  LEGACY_TENANCY / VALID_KEEP / REVIEW cho quá trình dọn dẹp đang diễn ra.
- `shared/contracts/mvp-surface.json` — nguồn sự thật duy nhất nối
  frontend ↔ backend ↔ 3 tầng test cho từng capability.
- `README.md`, `DEPLOYMENT.md`, `db.md` (root) — hướng dẫn cài đặt, triển
  khai, và mô hình sở hữu dữ liệu 3 mặt phẳng.
- `docs/superpowers/specs/` và `plans/` — spec/plan đã duyệt cho các sáng
  kiến đang triển khai (ví dụ: cross-plane E2E harness, frontend trust/UX).
