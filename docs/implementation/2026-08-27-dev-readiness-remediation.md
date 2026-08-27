# Kế hoạch điều chỉnh Dev Readiness

**Ngày:** 2026-08-27
**Trạng thái:** Đề xuất đã được duyệt để thực hiện dần
**Phạm vi:** `main` tại thời điểm rà soát; Python Agent Core/COSA API, TypeScript Encore services, Flutter desktop, landing và hạ tầng local.

## 1. Mục tiêu

Đưa repository về một baseline development lặp lại được, fail-closed và có thể tin cậy trước khi mở rộng thêm capability nghiệp vụ. Baseline này phải có ba đặc tính:

1. Không có secret, DSN hoặc token mặc định có thể được dùng khi cấu hình staging/production bị thiếu.
2. Các quality gate khai báo trong CI và Makefile chạy được từ môi trường sạch, không có trạng thái “xanh giả”.
3. Frontend, Company Service, COSA Control Plane và Agent API dùng các hợp đồng API/tenant nhất quán, được kiểm qua một vertical slice thật.

Tài liệu này là kế hoạch remediation sau audit. Nó không tuyên bố production-ready và không thay thế ownership/ADR hiện có.

## 2. Bằng chứng baseline

### Đã xác minh

| Hạng mục | Lệnh/kiểm tra | Kết quả |
| --- | --- | --- |
| Flutter | `flutter analyze` và `flutter test` | Analyzer sạch; 300 test qua. |
| Landing | `npm run build` trong `landing/` | Build production qua. |
| Python không cần DB | `pytest tests/agent_core/workflows tests/desktop_worker -q` | 101 test qua; có một cảnh báo deprecation của dependency test. |
| Company TypeScript | `npm run typecheck` trong `services/company/` | Qua. |
| Skillpacks | `make skillpacks-validate` | Qua. |
| npm production audit | Company, COSA, landing | Không phát hiện vulnerability production tại thời điểm kiểm tra. |

### Đã xác minh là lỗi/gap

| Hạng mục | Bằng chứng | Ảnh hưởng |
| --- | --- | --- |
| COSA TypeScript | `npm run typecheck` trong `services/cosa/` trả 27 lỗi | Job `services[cosa]` trong CI sẽ fail. |
| Control Plane test fixtures | Fixture connector/schedule còn truyền `companyId` vào interface đã workspace-first | Migration contract chưa hoàn tất. |
| Health check COSA | Dùng `db.raw()` không có trong `NodePgDatabase` | Không compile được; readiness endpoint không được bảo vệ bằng static gate. |
| Frontend/API | Nhiều request `/strategy/*`, `/okrs/*`, `/projects/*` đi tới Company gateway nhưng không có mapping/parity với `/operations/*` | Test mock có thể qua trong khi request thật trả 404 hoặc sai DTO. |
| Tenant data access | Nhiều service đọc theo ID trước rồi mới kiểm workspace | Có thể phân biệt resource tồn tại ở workspace khác qua 404/403; không đạt yêu cầu scope ở query layer. |
| Workflow DAG | Cycle hoặc dependency không tồn tại trả `COMPLETED` với `completed_steps=[]` | Trạng thái thành công giả khi declarative workflow được dùng. |
| Dev tooling | `make boundary-check` gọi Python hệ thống; preflight không tự nạp `.env` | Máy dev dễ thất bại dù virtualenv dự án dùng được. |
| Landing lint/CI | `next lint` lỗi với Next 16; landing chưa có job CI | Landing build được nhưng không có lint gate hợp lệ. |
| Tài liệu | README có link chết; một số báo cáo ghi quality gate xanh trái với static check hiện tại | Onboarding và quyết định kỹ thuật dễ dựa vào trạng thái cũ. |

Integration test có khả năng ghi/xoá dữ liệu không được chạy trên database đang dùng của workspace. Các gate đó chỉ được chạy sau khi có database test disposable.

## 3. Nguyên tắc thực hiện

- **Fail closed:** thiếu secret, database URL, service URL hoặc token ở staging/production phải làm process từ chối khởi động.
- **Workspace là scope sản phẩm:** `workspace_id` phải nằm trong truy vấn đọc/ghi tenant-bound, không chỉ được kiểm sau lookup.
- **Không “rewrite để cho chạy”:** chỉ thêm compatibility route khi HTTP method, DTO, quyền và semantics thật sự tương đương.
- **Một nguồn sự thật cho trạng thái:** chỉ báo “xanh” kèm lệnh, commit và môi trường đã chạy.
- **Không mở rộng feature trước baseline:** không broad-activate skillpack runtime, không port thêm domain frontend, không resurrect legacy backend trong phạm vi remediation này.

## 4. P0 — Bảo mật cấu hình trước staging

### Điều chỉnh

1. Xóa fallback secret/DSN khỏi runtime production:
   - `services/company/identity/services/token.service.ts`
   - `services/company/identity/services/platform.client.ts`
   - `services/cosa/storage/client.ts`
   - mọi client/service tương đương trong realtime worker.
2. Giữ default chỉ trong fixture test có tên rõ ràng; test phải inject env riêng thay vì phụ thuộc default runtime.
3. Deployment compose không được có credential thực thi mặc định. Chỉ dùng biến bắt buộc hoặc secret manager; tài liệu mẫu dùng placeholder không thể đăng nhập.
4. Nếu bất kỳ mật khẩu/token đã tracked từng được sử dụng ngoài local, phải rotate trước lần deploy kế tiếp.

### Tiêu chí nghiệm thu

- Process ở `production`, `staging` hoặc `prod` fail ngay khi thiếu/nhận giá trị secret mẫu.
- Không còn DSN có username/password runtime trong source tracked.
- Test xác minh token chỉ hợp lệ với secret do fixture cấp.
- Compose/preflight báo thiếu cấu hình theo tên biến, tuyệt đối không log giá trị secret.

## 5. P1 — Khôi phục static gate Control Plane

### Điều chỉnh

1. Đổi health check COSA sang API Drizzle chuẩn (`sql\`SELECT 1\``), theo cùng pattern của Company Service.
2. Hoàn tất workspace-first cho fixture connector và schedule: bỏ `companyId` khỏi input/insert chỉ thuộc workspace scope; giữ `companyId` ở những test contract platform thực sự còn sở hữu company.
3. Chạy typecheck trước migration/test trong mọi luồng local và CI.
4. Dùng một database test riêng cho COSA service test; test không được trỏ database development đang chạy.

### Tiêu chí nghiệm thu

```text
cd services/cosa && npm run typecheck
cd services/company && npm run typecheck
make services-test
```

Tất cả lệnh trên phải exit `0` trên environment mới có Postgres disposable và Encore CLI phù hợp.

## 6. P1 — Chốt hợp đồng Frontend ↔ Backend theo vertical slice

### Quyết định

Company Service là owner của business API. Flutter chỉ gọi route đã có owner, DTO và authorization contract rõ ràng; không giữ normalizer legacy như một proxy vĩnh viễn.

### Trình tự

1. Lập inventory có version cho mọi endpoint Flutter: method, path, request DTO, response DTO, auth, workspace header, owner và trạng thái parity.
2. Chọn slice đầu tiên: **Task list/get/create/update**. Đồng bộ frontend với `/operations/tasks` và schema Company Service.
3. Thêm contract test gọi một Company Service thật trên database disposable, thay vì chỉ dùng `MockClient`.
4. Chỉ sau khi slice Task xanh, thực hiện Project/OKR. Strategy, validation, AI và portfolio chỉ được map sau khi backend có parity rõ ràng.
5. Bỏ route legacy khi không còn consumer; ghi migration note cho mỗi route đổi tên/DTO.

### Tiêu chí nghiệm thu slice Task

- Flutter gửi `Authorization` và `X-Workspace-Id` cho mọi request tenant-bound.
- Cùng một test chứng minh user A không đọc/ghi được dữ liệu workspace B.
- Test contract phát hiện route thiếu, header thiếu, status code hoặc DTO lệch.
- Không thêm mapping `/strategy/*` hoặc `/okrs/*` chỉ để biến 404 thành một route có semantics khác.

## 7. P1 — Tenant scope ở query layer

### Điều chỉnh

1. Đổi API service đọc theo ID từ `get(id, authorization)` sang nhận `TenantContext` hoặc `workspaceId` đã xác thực.
2. Với resource tenant-bound, dùng truy vấn dạng:

```sql
WHERE id = :id
  AND workspace_id = :workspace_id
```

3. Với resource không thuộc workspace của caller, trả cùng một `404` như resource không tồn tại.
4. Audit và áp dụng pattern cho Operations, Commercial, Finance-Legal; bắt đầu từ Task, Customer, Contact, Account, Lead, Opportunity, transaction và legal records.
5. Giữ platform `company_id` giới hạn ở Control Plane/đồng bộ identity, không làm product tenancy fallback.

### Tiêu chí nghiệm thu

- Mỗi family có test cross-workspace cho get/update/delete.
- SQL/repository test khẳng định predicate `workspace_id` có mặt ngay trong lookup.
- Không test nào xác minh tenant bằng cách đọc unscoped record rồi so sánh tại application layer.

## 8. P2 — Workflow integrity

### Điều chỉnh

`WorkflowSpec` phải reject trước execution nếu có:

- step ID trùng;
- dependency không tồn tại;
- dependency cycle;
- `on_failure` hoặc compensation target không tồn tại;
- compensation target vô tình chạy như forward step.

`WorkflowEngine` vẫn phải fail an toàn khi nhận spec đã bị bypass validation; không được chuyển sang `COMPLETED` nếu còn step chưa thể thực thi.

### Tiêu chí nghiệm thu

- Test cycle và dangling dependency fail ở validation/execution với lỗi tường minh.
- Test DAG hợp lệ song song, approval và compensation hiện hữu vẫn qua.
- Có assertion rằng workflow `COMPLETED` đã hoàn tất tất cả forward step.

## 9. P2 — Development experience, CI và tài liệu

### Điều chỉnh

1. Chuẩn hóa Python qua `.venv/bin/python` hoặc một bootstrap `uv` duy nhất; Makefile, script và README phải gọi cùng runtime.
2. Tạo bootstrap nạp `.env` có chủ đích cho local. Biến export bên ngoài phải được ưu tiên; CI tiếp tục cấp env trực tiếp.
3. Sửa `landing` lint script sang checker hỗ trợ Next 16 và thêm job lint/build landing vào CI.
4. Thêm CI link-check cho README/docs canonical; thay link chết bằng tài liệu còn tồn tại hoặc archive đúng vị trí.
5. Mỗi báo cáo readiness ghi rõ phạm vi, lệnh kiểm tra, ngày và commit; không sử dụng “done/green” chung chung.
6. Pin tag hoặc digest cho image đang dùng `latest`, trước hết là MinIO, LiveKit và OpenSandbox.
7. Thêm coverage report/threshold ban đầu cho auth, tenant scope, workflow engine và API contract. Ngưỡng tăng dần theo baseline thực, không đặt số tùy ý để xanh giả.

### Tiêu chí nghiệm thu

- Clone mới + bootstrap documented có thể chạy static gates mà không cài nhầm Python hệ thống.
- `make boundary-check`, skillpack validation, Company/COSA typecheck, Flutter test/analyze và landing lint/build có entry CI tương ứng.
- `docker compose config` hợp lệ khi cấu hình local được nạp; production compose fail nếu biến bắt buộc thiếu.
- Không còn link canonical chết trong README.

## 10. Thứ tự giao hàng đề xuất

1. **P0 configuration/security** — prerequisite cho mọi môi trường dùng chung.
2. **COSA static gate** — khôi phục CI về trạng thái có tín hiệu tin cậy.
3. **Tenant-query scope** — xử lý Task trước, rồi audit các family còn lại.
4. **Task frontend contract slice** — chạy end-to-end trên database disposable.
5. **Workflow validation** — chặn success giả trước khi mở rộng declarative workflow.
6. **Tooling/docs/landing/Compose** — hợp nhất thành một dev baseline có thể tái tạo.
7. **Các feature mới** — chỉ bắt đầu sau khi gate của bước 1–6 xanh trong CI.

## 11. Non-goals

- Không khôi phục legacy backend.
- Không tự động biến local skillpack thành runtime capability.
- Không rewrite đồng loạt frontend hoặc thêm route giả để “giữ màn hình chạy”.
- Không chạy destructive integration test trên database development/shared.
- Không deploy hoặc thay secret production trong tài liệu này; đó là thay đổi vận hành có phê duyệt riêng.

## 12. Definition of Ready cho vòng feature kế tiếp

Chỉ bắt đầu feature business mới khi tất cả điều kiện dưới đây đúng:

1. Không còn fallback secret/DSN ở staging/production.
2. COSA và Company typecheck xanh.
3. Ít nhất một frontend-to-Company vertical slice có contract test thật và tenant isolation pass.
4. Workflow invalid DAG bị reject, không trả trạng thái hoàn tất giả.
5. Local bootstrap và CI dùng cùng quality commands; landing đã có gate.
6. Các tài liệu canonical có link sống và trạng thái kiểm chứng được.
