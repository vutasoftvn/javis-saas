# Release Gate Recovery — Design

## Mục tiêu

Khôi phục các release gate hiện đang đỏ mà không nới tenant authorization, không dùng allowlist để che route mới, và không làm thay đổi dữ liệu hay chính sách vận hành bên ngoài.

## Phạm vi

- Sửa Strategy Copilot để tái sử dụng `TenantContext` đã xác thực khi tạo Initiative.
- Khai báo các Strategy endpoint đang được frontend gọi trong `shared/contracts/mvp-surface.json`, sinh lại contract artifacts, và cập nhật route inventory được sinh tự động.
- Loại dependency `WorkspaceScopedService` khỏi `StrategyWorkflowService`; giữ transport hiện tại trong đợt này vì các endpoint Strategy cũ chưa trả envelope `data`/`meta` mà `MvpRequestClient` yêu cầu.
- Loại explicit `any` trong transaction Strategy.
- Giữ giá trị thập phân của Key Result trên Flutter.
- Làm cho ba quality gate phản ánh đúng ý nghĩa: fixture scanner chỉ bắt runtime import/load, purity checker chỉ quét cross-plane harness thật, và link tài liệu không còn gắn đường dẫn tuyệt đối theo máy.
- Làm test target COSA phát hiện migration còn thiếu trước khi chạy suite, không tự động chạy migration vào database của lập trình viên.

## Ngoài phạm vi

- Không bật CAS polling production, không đưa token vào vault, không thay đổi secret hoặc cấu hình deploy.
- Không đổi chính sách xác thực contact hay SLA ngày lễ.
- Không chuẩn hóa toàn bộ response của Company thành envelope `data`/`meta`; việc đó là một migration API riêng.
- Không thêm exception vào allowlist route hoặc legacy frontend boundary.

## Quyết định thiết kế

### 1. Authorization nội bộ giữ nguyên fail-closed

`createInitiativeService(params, authorization)` vẫn là public entrypoint: nó resolve token bằng `requireWorkspaceAccess` rồi gọi một hàm nội bộ nhận `TenantContext`. Hàm nội bộ xác nhận `ctx.workspaceId === params.workspaceId` trước khi thực hiện validation và ghi dữ liệu.

`proposeInitiativesService` gọi trực tiếp hàm nội bộ với `ctx` của chính nó. Vì vậy public request vẫn cần token, trong khi một command đã được xác thực không bị yêu cầu xác thực lần hai bằng một header không còn tồn tại. Test phải chứng minh tạo proposal thành công trong workspace của caller và bị từ chối khi `params.workspaceId` khác context.

### 2. Contract là nguồn sự thật, generated file không sửa tay

Mỗi method/path Strategy đang có handler thật và đang được frontend gọi sẽ có capability enabled, owner, bằng chứng backend/Flutter/E2E trong manifest. Sau đó chạy generator để cập nhật TypeScript, Python và Dart artifacts, rồi sinh lại route inventory. Các endpoint không có handler thật sẽ không được khai báo.

`StrategyWorkflowService` chuyển sang `StrategyServiceBase`, vì class này chỉ cung cấp helper local và không giữ dependency legacy workspace service. Đợt này vẫn dùng `ApiClient`: `MvpRequestClient` buộc response envelope mà nhiều handler Strategy hiện trả response thô. Chuyển transport trước khi chuẩn hóa envelope sẽ là breaking change, nên bị loại khỏi release-recovery scope.

### 3. Chất lượng và tính đúng đắn dữ liệu

`recordTowsDecision` nhận transaction type suy ra từ `db.transaction`, đồng nhất các Strategy service khác. Flutter gửi `double` cho baseline và target KR; test dùng giá trị phân số để ngăn regression ép integer.

Widget test BSC xác nhận semantic key và thông điệp read-only đang hiển thị. Module switcher inject/mock transport tại biên test để không gọi HTTP thật hay phụ thuộc animation timing.

### 4. Checker chỉ kiểm tra đúng đối tượng

Fixture checker thay regex chuỗi `fixtures/` tổng quát bằng nhận diện import hoặc API load fixture. Metadata mô tả fixture vẫn hợp lệ. Purity checker tiếp tục quét `scenarios`, `stack` và `seed` của cross-plane harness, nhưng unit test runner được chuyển ra ngoài cây đó. Tài liệu thay prefix `/Volumes/SSD/javis-saas/` bằng convention link root-relative của repository (`/...`) để checker và checkout khác cùng hiểu.

Migration script COSA có mode kiểm tra read-only liệt kê các file `.up.sql` chưa có trong `public.schema_migrations`; target `services-test-cosa` chạy preflight này trước `encore test`. Preflight báo đúng migration thiếu và lệnh migration an toàn, không tạo/sửa bảng.

## Kiểm thử và tiêu chí chấp nhận

- Regression test Strategy Copilot xanh với context hợp lệ; mismatch workspace bị từ chối.
- `make frontend-boundary-check`, `make frontend-api-contract-check`, `make encore-type-safety-check`, `make contract-freeze-check`, `make mvp-surface-check`, `make mvp-e2e-purity-check` và `make check-docs` xanh.
- Service typecheck và focused Strategy tests xanh; Flutter test các file đã sửa và `flutter analyze` xanh.
- COSA preflight báo migration thiếu trước suite trên database cũ; sau khi database đã được migrate, suite được phép chạy. Không chạy migration thật trong quá trình sửa này.

## Thứ tự triển khai

1. Viết test đỏ cho authorization context, precision KR và checker boundaries.
2. Sửa Company authorization/type, rồi chạy focused service test/typecheck.
3. Khai báo contract, sinh artifacts/inventory, và bỏ legacy frontend base; chạy gate contract/boundary.
4. Sửa Flutter regression/flakiness; chạy focused test và analyzer.
5. Sửa checker, di chuyển unit test runner, chuẩn hóa doc links, rồi chạy toàn bộ gate hẹp.
6. Thêm COSA migration preflight và test script bằng database disposable hoặc mock process không ghi database dev.
