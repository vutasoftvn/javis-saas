# Khuyến nghị — phát hiện khi khảo sát & đề xuất điều chỉnh

> Mỗi mục: **Phát hiện** → **Vì sao đáng chú ý** → **Đề xuất hành động** →
> **Mức ưu tiên**. Đây là ĐỀ XUẤT để founder/team quyết định, không phải
> hành động đã thực hiện — không có mục nào trong file này được tự động
> triển khai.

## Nhóm A — Cần quyết định kiến trúc (ADR chưa chốt)

### A1. `ADR-COSA-DELEGATION-002` đang PROPOSED

- **Phát hiện:** ADR đề ngày 2026-09-03 (mới nhất trong repo), đang điều
  tra cơ chế token định danh có phạm vi tenant (tenant-scoped) cho các agent
  run xuyên vùng kiến trúc (cross-plane), phát sinh từ bug B5 trong quá
  trình xây cross-plane E2E harness.
- **Vì sao đáng chú ý:** đây là cơ chế bảo mật cho việc agent chạy xuyên
  Control Plane/Business Plane — nếu tài liệu hoá cơ chế cross-plane run là
  "đã chốt" trước khi ADR này ACCEPTED, người đọc sau sẽ hiểu nhầm mức độ ổn
  định.
- **Đề xuất:** theo dõi tới khi ADR chuyển ACCEPTED; cập nhật file
  [03-agent-va-governance.md](03-agent-va-governance.md) khi có quyết định.
- **Mức ưu tiên:** Cao (ảnh hưởng bảo mật cross-plane).

### A2. `ADR-LOCAL-EVENT-BACKBONE-001` chờ dữ liệu capacity

- **Phát hiện:** PROPOSED, gate bởi dữ liệu capacity Postgres outbox chưa
  đo thực tế; quyết định giữ Postgres hay chuyển Kafka phụ thuộc số đo này.
- **Vì sao đáng chú ý:** đây là backbone sự kiện của toàn hệ thống — thay
  đổi công nghệ nền sau này sẽ tốn kém hơn nếu trì hoãn đo lường.
- **Đề xuất:** ưu tiên đo throughput/latency outbox thực tế trước khi có
  thêm service phụ thuộc nặng vào event backbone.
- **Mức ưu tiên:** Trung bình.

## Nhóm B — Nợ kỹ thuật cần sửa code

### B1. `services/company/academy/` là stub mồ côi

- **Phát hiện:** không có `encore.service.ts`/`db.ts`, dữ liệu lưu tạm
  trong bộ nhớ (in-memory), nhưng đã có migration + schema Drizzle
  (`academy.ts`, ~7 bảng) không được dùng.
- **Vì sao đáng chú ý:** schema tồn tại nhưng không service nào wire vào —
  rủi ro nhầm lẫn khi ai đó tưởng academy đã hoạt động, hoặc migration
  "chết" gây khó hiểu khi audit DB.
- **Đề xuất:** quyết định rõ một trong hai — (a) hoàn thiện wiring
  (`encore.service.ts` + `db.ts` + chuyển từ in-memory sang Drizzle) nếu
  academy là tính năng sắp launch, hoặc (b) gỡ bỏ migration/schema chưa
  dùng nếu chưa có kế hoạch gần.
- **Mức ưu tiên:** Trung bình.

### B2. Vi phạm rule #7 (string-match thay vì structured state)

- **Phát hiện:** `apps/cosa/events/trigger_promotion.py:41-42` —
  `stale = any("stale" in issue.lower() for issue in gate.blocking_issues)`.
- **Vì sao đáng chú ý:** CLAUDE.md nguyên tắc #7 cấm suy diễn trạng thái từ
  văn bản tự nhiên; match theo chuỗi `"stale"` dễ vỡ nếu message đổi câu
  chữ.
- **Đề xuất:** đổi `blocking_issues` (hoặc trường liên quan trong
  `GateResult`) sang reason code có kiểu (enum), loại bỏ so khớp chuỗi.
- **Mức ưu tiên:** Thấp (không gây lỗi ngay, nhưng dễ vỡ âm thầm).

### B3. `services/cosa` company RPC đang bị dọn dần (LEGACY_TENANCY)

- **Phát hiện:** `company.service.ts`/`company.handler.ts` trong
  `services/cosa` đứng đầu danh sách `LEGACY_TENANCY` (dự kiến xoá ở M2)
  trong `docs/architecture/generated/company-usage-inventory.md`.
- **Vì sao đáng chú ý:** đây chính là phần "Company RPC" mô tả trong
  [01-bon-vung-kien-truc.md](01-bon-vung-kien-truc.md) — nếu không theo dõi
  milestone dọn dẹp, tài liệu sẽ nhanh chóng lỗi thời.
- **Đề xuất:** khi milestone M2 hoàn tất, cập nhật lại file 01 (mục Control
  Plane) và inventory liên quan.
- **Mức ưu tiên:** Trung bình (theo dõi tiến độ, không cần hành động ngay).

### B4. Frontend `features/` vs `modules/` trùng tên, di trú dở dang

- **Phát hiện:** 5 thư mục trùng tên giữa `frontend/lib/features/` và
  `frontend/lib/modules/`: `settings`, `strategy`, `vault`, `workforce`,
  `workspace_runtime`.
- **Vì sao đáng chú ý:** engineer mới dễ sửa nhầm thư mục cũ, hoặc tạo trùng
  logic ở cả hai nơi.
- **Đề xuất:** lập kế hoạch hợp nhất rõ ràng (một hướng: `features/` là đích
  đến của di trú, `modules/` dần rút gọn — hoặc ngược lại), ghi rõ trạng
  thái trong `frontend/README.md` cho tới khi hoàn tất.
- **Mức ưu tiên:** Trung bình.

## Nhóm C — Tài liệu/nhận thức bị lệch (doc-drift, không cần sửa code)

### C1. `services/realtime_agent/README.md` lệch so với `docker-compose.yml` thật

- **Phát hiện:** README mô tả tool bridge gọi `backend/app`/`brain-api`
  (đường dẫn không còn tồn tại — nghiệp vụ nay nằm ở `apps/cosa/api`), và
  ghi "LiveKit (Cloud today; Local later)" — trong khi `docker-compose.yml`
  đã chạy thật cả LiveKit local lẫn 2 worker (`realtime-agent` local +
  `realtime-agent-cloud`) từ trước đó. Đã xác minh: **`docker-compose.yml`
  đúng, README cũ hơn thực tế** (xem
  [04-trai-nghiem-nguoi-dung.md](04-trai-nghiem-nguoi-dung.md) để biết kiến
  trúc voice dual-worker thật).
- **Vì sao đáng chú ý:** một engineer chỉ đọc README (không đối chiếu
  `docker-compose.yml`) sẽ kết luận sai rằng voice local chưa tồn tại — đúng
  bẫy mà chính khảo sát này từng mắc phải trước khi đối chiếu docker-compose.
- **Đề xuất:** cập nhật README để phản ánh đúng `apps/cosa` và trạng thái
  dual-worker (local + cloud) đã chạy thật.
- **Mức ưu tiên:** Thấp (không ảnh hưởng runtime, chỉ gây hiểu nhầm khi đọc).

### C2. `COMPANY_SCHEMA_INVENTORY.json` là snapshot đóng băng, không thể regenerate

- **Phát hiện:** file tự ghi trong `_meta.purpose` rằng nó được sinh bởi
  "a temporary, non-committed static-analysis script" đọc từ
  `legacy/backend/alembic/versions/*.py` — `legacy/` đã bị xoá hẳn
  2026-08-25 và không có script generator nào còn tồn tại trong repo (đã
  grep xác nhận). Đề xuất "regenerate" ban đầu (phiên trước) là sai — không
  thể thực hiện.
- **Đề xuất:** đã thêm `docs/architecture/generated/COMPANY_SCHEMA_INVENTORY.md`
  ghi rõ trạng thái đóng băng, tránh người đọc sau tưởng nhầm có thể chạy
  lại.
- **Mức ưu tiên:** Thấp — đã xử lý xong (xem file ghi chú kèm theo).

### C3. `docs/architecture/cookbook/` mới hoàn thành 1/6 recipe

- **Phát hiện:** chỉ có `ADD_NATIVE_TOOL.md`; 5 recipe khác (Skill, Workflow
  Node/UI Renderer, MCP Connector, Executor Provider, Event Projection) còn
  ghi "coming soon".
- **Đề xuất:** khi trỏ người đọc mới tới cookbook, ghi rõ đây là tài liệu
  đang xây dựng, tránh kỳ vọng sai.
- **Mức ưu tiên:** Thấp.

### C4. `desktop_worker/` dễ bị nhầm là "voice worker local"

- **Phát hiện:** tên gọi và vị trí (`desktop_worker/`, chạy trên máy người
  dùng) khiến người đọc mới dễ nhầm đây là worker voice cục bộ. Thực tế nó
  là daemon capability khác hẳn (git/fs/shell sandboxed) — worker voice cục
  bộ thật là container `realtime-agent` trong `docker-compose.yml`. Chi
  tiết xem [04-trai-nghiem-nguoi-dung.md](04-trai-nghiem-nguoi-dung.md).
- **Đề xuất:** khi viết tài liệu/onboarding, luôn phân biệt rõ 2 khái niệm
  cùng nằm "phía desktop" nhưng không liên quan nhau: `desktop_worker/`
  (capability daemon) và `realtime-agent` (voice worker local, chạy trong
  docker-compose chứ không phải trên máy người dùng).
- **Mức ưu tiên:** Thấp (chỉ ảnh hưởng nhận thức khi đọc/onboarding).

### C5. Memory dự án về AgentSpec/registry cần cập nhật

- **Phát hiện:** ghi chú cũ nói "AgentSpec vẫn hard-code, chưa qua
  registry" — đúng một phần. Thực tế là trạng thái hybrid: authoring vẫn
  hardcode (`apps/cosa/agents/specs.py`) nhưng resolution lúc chạy đã qua
  registry (seed → publish → resolve theo hash). Chi tiết xem
  [03-agent-va-governance.md](03-agent-va-governance.md).
- **Đề xuất:** cập nhật ghi chú để phản ánh đúng mức độ tiến triển thực tế.
- **Mức ưu tiên:** Thấp.

## Nhóm D — Chỉ cần lưu ý khi đọc (không cần hành động)

### D1. "ACCEPTED" trong ADR không đồng nghĩa đã hoàn tất

Nhắc lại nguyên tắc đã có sẵn trong `CLAUDE.md`: ACCEPTED / IMPLEMENTED /
WIRED / VERIFIED / PRODUCTION là **5 trục khác nhau**. Ví dụ cụ thể quan sát
được khi khảo sát: `ADR-ID-MODEL-001` đã ACCEPTED nhưng tự ghi chú (2026-09-01)
là chỉ mới triển khai một phần (Snowflake spine ID có, LeafId/UUIDv7 thì
chưa, theo YAGNI). Khi đọc bất kỳ ADR nào trong `docs/architecture/adr/`,
luôn kiểm tra trạng thái triển khai thực tế bằng cách grep code, không suy
diễn từ trạng thái ADR.

### D2. `docs/architecture/reports/*` là ảnh chụp lịch sử, không phải tài liệu sống

Các báo cáo audit trong thư mục này (22-31/08/2026) phản ánh trạng thái tại
thời điểm viết — hữu ích làm bằng chứng lịch sử, nhưng không nên trích dẫn
như hiện trạng hôm nay. Dùng bộ tài liệu `overview/` này (00-04) làm nguồn
hiện trạng, tham chiếu `reports/` chỉ khi cần bối cảnh vì sao một quyết định
được đưa ra.
