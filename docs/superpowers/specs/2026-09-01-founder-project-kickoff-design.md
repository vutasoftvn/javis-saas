# Founder Project Kickoff — Design Specification

**Status:** Proposed — awaiting review

**Goal:** Sau khi Founder tạo project, đưa họ vào một luồng thiết lập ngắn, rõ ràng và có thể tiếp tục sau; chỉ hiển thị Hub vận hành khi project đã có stage, timebox và cam kết tuần đầu được xác nhận.

## Vấn đề hiện tại

Sau khi tạo project, UI quay ngay về Command Center. Màn hình đó hiển thị `P1`, `0/0 mục tiêu`, mission, Top 3 và nhãn `12-Week Year` dù Founder chưa xác nhận vấn đề, khách hàng mục tiêu, stage, thời lượng hay hành động đầu tiên.

Điều này gây ba hiểu nhầm:

1. Hệ thống trông như đã có kế hoạch, trong khi dữ liệu chỉ mới có title/description.
2. `12-Week Year` bị áp như một trạng thái mặc định, thay vì một nhịp điều hành mà Founder chủ động chọn khi đã sẵn sàng.
3. `P1` được mặc định từ frontend, trái với lifecycle canonical là `P0_DISCOVERY` khi chưa có evidence.

Ngoài ra, dialog hiện phát các stage string không canonical cho P2–P5 (`P2_SOLUTION_FIT`, `P3_MVP_BUILD`, `P4_PMF_GROWTH`, `P5_SCALE_OPERATE`), trong khi contract hiện dùng `P2_SOLUTION_VALIDATION`, `P3_BUILD_VALIDATE`, `P4_GO_TO_MARKET`, `P5_OPERATE_GROWTH`.

## Quyết định trải nghiệm

**Sau khi tạo project, điều hướng tới `Dashboard → Project → Project Kickoff`, không quay về Command Center tổng quát.**

Command Center có ba chế độ:

| Trạng thái project | Màn hình mặc định | Việc Founder thấy |
|---|---|---|
| Chưa hoàn tất setup | Project Kickoff | 3 bước thiết lập, tiến độ và nút tiếp tục. |
| Đã setup, đang ở vòng đầu | Guided Hub theo project | Stage, tuần hiện tại, một kết quả cần đạt và 1–3 việc tuần này. Không hiển thị KPI/mission giả. |
| Đã vận hành | Command Center hiện có | Pulse, Top 3, quyết định, approvals và workforce từ dữ liệu thật. |

Không tạo một dashboard thứ ba. `ProjectKickoffView` hiện có là entry point cần tái cấu trúc cho luồng đơn giản; roadmap nhiều stage, AI proposal và cấu hình chuyên sâu được đưa vào một khu vực `Lộ trình nâng cao` sau khi Founder hoàn tất setup cơ bản.

## Luồng Founder

```text
Tạo project (tên + mô tả ngắn)
  → Project Kickoff / Bước 1: Hiểu dự án
  → Bước 2: Chọn vòng đầu COSA đề xuất
  → Bước 3: Chốt việc tuần đầu
  → Xác nhận
  → Guided Hub theo project
  → Command Center vận hành khi có dữ liệu thực
```

### Tạo project

Dialog tạo project chỉ thu thập:

- Tên project.
- Một mô tả ngắn về vấn đề hoặc cơ hội.

Project luôn được tạo với `lifecycleStage = P0_DISCOVERY`. Không có dropdown P-stage trong dialog cơ bản. Founder đang tiếp quản một project đã có evidence sử dụng entry riêng `Nhập project đang vận hành`; đó không thuộc first-project flow.

Sau POST thành công, app điều hướng ngay tới `ProjectKickoffView(projectId: created.id)` và không gọi Top 3, mission, workforce hoặc 12-week API.

### Bước 1 — Hiểu dự án (khoảng 2 phút)

Giao diện đặt tối đa ba câu hỏi, mỗi câu bằng ngôn ngữ business:

1. **Ai đang gặp vấn đề này?** — khách hàng/nhóm người dùng mục tiêu.
2. **Vấn đề gây ảnh hưởng gì?** — một mô tả ngắn, có thể dùng lại description ban đầu.
3. **Bạn đã có gì để chứng minh?** — chọn một trong bốn mức: `Chưa nói chuyện với khách hàng`, `Đã có 1–4 cuộc trao đổi`, `Có từ 5 cuộc trao đổi`, `Đã có prototype hoặc khách trả tiền`.

Không bắt Founder điền vision, OKR, roadmap, workforce hay dữ liệu tài chính tại thời điểm này. COSA dùng ba câu trả lời để đề xuất vòng đầu; Founder luôn được sửa nội dung trước khi tiếp tục.

### Bước 2 — Chọn stage và timebox

COSA trình bày **một đề xuất**, không đổ 7 mã stage vào dropdown.

Ví dụ mặc định:

> **COSA đề xuất: Khám phá (P0) trong 2 tuần**
>
> Mục tiêu: nói chuyện với 5 khách hàng mục tiêu để hiểu vấn đề có đủ đau và đủ thường xuyên hay không.

Founder chọn một duration chip, có thể bấm `Đổi đề xuất` để xem lựa chọn khác. Duration là **timebox kỳ vọng**, không phải deadline tự động chuyển stage và không thay thế stage gate/evidence.

| Project stage | Tên hiển thị | Timebox đề xuất | Điều kiện để cân nhắc đi tiếp |
|---|---|---:|---|
| P0 | Khám phá | 1–2 tuần, mặc định 2 | Có các tín hiệu ban đầu từ khách hàng mục tiêu. |
| P1 | Xác thực vấn đề | 2–4 tuần, mặc định 4 | Pain/problem lặp lại, phân khúc và mức ưu tiên rõ hơn. |
| P2 | Xác thực giải pháp | 3–6 tuần, mặc định 4 | Prototype/giải pháp được test với khách hàng phù hợp. |
| P3 | Xây dựng & kiểm chứng | 4–8 tuần, mặc định 6 | MVP đo được hành vi/giá trị thực. |
| P4 | Ra thị trường | 6–12 tuần, mặc định 8 | Kênh, thông điệp và nhóm khách hàng đầu tiên có tín hiệu. |
| P5 | Vận hành & tăng trưởng | 12 tuần, review mỗi quý | Vận hành lặp lại với chỉ số tăng trưởng rõ. |
| P6 | Mở rộng & quản trị | 12 tuần, review mỗi quý | Scale có kiểm soát và governance phù hợp. |

`12-Week Year` là **nhịp điều hành tùy chọn**, không phải tên mặc định của mọi task. Với P0/P1, UI dùng nhãn `Vòng xác thực 2 tuần` hoặc `Vòng xác thực 4 tuần`. Từ P3 trở đi, COSA có thể đề xuất một 12-week cycle; Founder bật/tắt và chọn ngày review tuần trước khi kích hoạt.

Nếu Founder chọn P1 tại setup đầu tiên, COSA phải hiển thị bằng chứng đang có và yêu cầu Founder xác nhận. Backend dùng lifecycle transition canonical `P0_DISCOVERY → P1_PROBLEM_VALIDATION`, tạo audit history; không ghi đè stage trực tiếp. UI basic không cho nhảy thẳng P2–P6.

### Bước 3 — Chốt tuần đầu

COSA hiển thị một outcome và tối đa ba hành động đề xuất từ câu trả lời ở Bước 1–2. Founder có thể sửa, bỏ hoặc tự thêm action.

Ví dụ P0:

- **Kết quả của tuần 1:** hoàn thành 5 cuộc trao đổi với đúng nhóm khách hàng.
- **Việc 1:** chốt danh sách 10 người cần liên hệ.
- **Việc 2:** chọn 5 câu hỏi phỏng vấn.
- **Việc 3:** đặt buổi review vào thứ Sáu.

Founder chỉ cần xác nhận một ngày review tuần; mặc định là thứ Sáu 16:00 theo timezone workspace. Không tự tạo mission hay tự chạy agent. Sau `Xác nhận vòng đầu`, actions đã chọn trở thành dữ liệu persisted và là nguồn duy nhất cho Guided Hub.

## Guided Hub sau setup

Trong vòng đầu, thay hero/pulse hiện tại bằng một project card ngắn:

```text
Project: Nền tảng B2B SaaS
Bạn đang ở: Khám phá (P0) · Tuần 1/2
Kết quả vòng này: xác minh 5 cuộc trao đổi khách hàng
Tiếp theo: lập danh sách 10 người để liên hệ

[Cập nhật tiến độ]  [Trao đổi với COSA]  [Điều chỉnh vòng này]
```

`0/0 mục tiêu`, `Missions đang chạy`, `Quyết định`, `Rủi ro` và `Top 3 hôm nay` chỉ xuất hiện khi dữ liệu tương ứng tồn tại. Nếu chưa có dữ liệu, Guided Hub hiển thị checklist tiến độ setup/tuần thay vì số 0 có vẻ là KPI.

Top 3 vận hành chỉ được mở khi có `projectOperatingSetup.status = ACTIVE` và ít nhất một persisted first-week action. Mỗi số liệu Pulse phải lấy từ entity đúng loại; đặc biệt `activeMissions` không được suy diễn bằng độ dài danh sách Next Best Actions.

## Dữ liệu và ownership

Business truth nằm trong `services/company`, không nằm ở Flutter hoặc Agent runtime.

Thêm một record một-một `project_operating_setup` (tên có thể điều chỉnh theo schema convention) cho project:

```ts
interface ProjectOperatingSetup {
  projectId: string;
  workspaceId: string;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'ACTIVE';
  targetCustomer: string | null;
  problemStatement: string | null;
  evidenceLevel: 'NONE' | 'ONE_TO_FOUR_INTERVIEWS' | 'FIVE_PLUS_INTERVIEWS' | 'PROTOTYPE_OR_REVENUE' | null;
  recommendedStage: ProjectLifecycleStage | null;
  selectedStage: ProjectLifecycleStage | null;
  stageDurationWeeks: number | null;
  stageTargetDate: string | null;
  weeklyReviewWeekday: 1 | 2 | 3 | 4 | 5 | 6 | 7 | null;
  weeklyReviewTime: string | null;
  firstWeekOutcome: string | null;
  firstWeekActions: readonly ProjectAction[];
  updatedAt: string;
}
```

`stageDurationWeeks` là forecast/timebox riêng; không tái sử dụng `projects.endDate` vì đó là ngày kết thúc toàn project. Lifecycle stage canonical vẫn thuộc bảng project với `stageEnteredAt`, version và history hiện có.

API đề xuất:

```text
GET  /operations/projects/:projectId/operating-setup
PUT  /operations/projects/:projectId/operating-setup
POST /operations/projects/:projectId/operating-setup/activate
```

`activate` chạy transaction: validate access/workspace, validate input, thực hiện P0→P1 qua lifecycle service khi Founder đã chọn P1, persist setup/action/review cadence, và emit audit/outbox event. Không được tạo inferred goals, missions, metrics hay approvals.

## Điều hướng và resume

- `createFirstProject` nhận `createdProject.id`, sau đó route đến Project Kickoff.
- Mở project có `NOT_STARTED`/`IN_PROGRESS` luôn resume đúng step, không quay vào Hub tổng quát.
- Chọn project có setup `ACTIVE` mở Guided Hub; chọn project mature mở Command Center.
- App bar phải ghi rõ scope: `Project: <tên>` và `Khám phá (P0) · tuần 1/2`. Workspace lifecycle `W0…W5` không dùng badge `P1`; P-stage và W-stage không bị lẫn.

## Không thuộc phạm vi

- Tự động tạo lịch/calendar event hoặc gửi message ra ngoài.
- Tự động dispatch agent/mission khi Founder chưa xác nhận.
- Thay thế M3/M5/M7, full roadmap nhiều stage hoặc quy trình nhập project đã vận hành.
- Dùng AI để tự quyết stage transition. AI chỉ đưa đề xuất; lifecycle/evidence gate vẫn là code xác định.

## Tiêu chí nghiệm thu

1. Tạo project mới luôn mở Project Kickoff, không mở generic Hub.
2. Project mới bắt đầu ở canonical `P0_DISCOVERY`; UI không phát stage string legacy/non-canonical.
3. Founder hoàn tất 3 bước trong một luồng, rời đi giữa chừng và vào lại đúng nơi.
4. Founder nhìn thấy timebox stage bằng tuần, ngày review và outcome tuần đầu trước khi kích hoạt.
5. `12-Week Year` không xuất hiện như prerequisite của P0/P1.
6. Guided Hub không hiển thị metric/mission/Top 3 giả hoặc suy diễn.
7. Mọi update setup và stage transition bind workspace, role, audit và survive reload.
8. Test cover: create→redirect, resume, P0 default, P0→P1 confirmation, tenant isolation, invalid duration, absence of inferred metrics, và UI copy cho P0/P1.
