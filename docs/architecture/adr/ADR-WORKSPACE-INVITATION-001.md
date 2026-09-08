# ADR-WORKSPACE-INVITATION-001: Authority contract cho việc gia nhập workspace

## Status

**ACCEPTED — 2026-09-08.** ADR này chốt contract (interface + rule bảo mật)
cho luồng gia nhập workspace bằng invitation, làm nền tảng trước khi thực hiện
mọi thay đổi schema/migration ở các task tiếp theo trong
`docs/superpowers/sdd/2026-09-08-platform-authority-durability-hardening/`.
Bản thân ADR **không thay đổi code implementation** — `services/cosa/services/
company.service.ts::joinExistingCompany` và handler
`services/cosa/handlers/company.handler.ts::joinCompany` vẫn giữ nguyên hành
vi hiện tại (join bằng `company_id` trần) cho tới Task 2+. Task 1 chỉ thêm một
test đỏ (`services/cosa/tests/control-plane.test.ts`) chứng minh lỗ hổng đang
tồn tại, để không ai vô tình coi endpoint hiện tại là an toàn trong lúc chờ
migrate.

## Context

`README.md` mục "Điều kiện bắt buộc trước khi mở workspace ra bên ngoài" đã
ghi nhận từ trước: *"Gia nhập workspace phải dùng invitation/approval có hạn,
có người cấp quyền và audit trail; một `workspace_id` biết được không phải là
bằng chứng để cấp membership."* Implementation hiện tại vi phạm đúng nguyên
tắc này:

- `POST /platform/auth/companies/join` (`services/cosa/handlers/
  company.handler.ts::joinCompany`) nhận `{ company_id }` từ bất kỳ platform
  user nào đã đăng nhập.
- `joinExistingCompany` (`services/cosa/services/company.service.ts:121-177`)
  chỉ kiểm tra workspace tồn tại và đang `active`, rồi **insert thẳng**
  `workspaceMemberships` với `role_id = "member"` — không kiểm tra người gọi
  có được mời hay không, không cần founder/admin phê duyệt, không audit trail
  nào khác ngoài chính row membership.
- Hệ quả: bất kỳ ai biết (hoặc đoán/liệt kê) một `company_id` hợp lệ đều tự
  cấp được membership cho chính mình vào công ty đó. Test hiện có trong
  `control-plane.test.ts` ("joins an existing company for a new user") coi
  đây là hành vi *mong đợi* — đúng ra nó đang document một lỗ hổng.

Trước khi đổi schema (thêm bảng invitation, đổi endpoint, v.v.) ở các task
sau, ADR này chốt các quyết định thiết kế **không được suy diễn ngầm khi
code** — mọi giá trị dưới đây là quyết định tường minh, không phải mặc định
tự chọn lúc implement.

### Interface chốt

```ts
type InvitationRole = "member" | "admin";
type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";

interface CreateWorkspaceInvitationParams {
  workspace_id: string;
  email: string;
  role_id: InvitationRole;
  expires_in_hours?: number;
}

interface AcceptWorkspaceInvitationParams {
  token: string;
}
```

## Decision

Các quyết định sau là **contract mặc định**, áp dụng nguyên văn cho migration
ở các task tiếp theo — không được nới lỏng hay bổ sung ngoại lệ ngầm khi
code:

1. **Token: ngẫu nhiên 32 byte, chỉ trả về một lần.** Invitation token được
   sinh bằng CSPRNG (tối thiểu 32 byte entropy, ví dụ `crypto.randomBytes(32)`
   rồi encode base64url), trả về cho caller đúng một lần tại thời điểm tạo lời
   mời (trong response của `CreateWorkspaceInvitationParams`, ví dụ qua email
   hoặc link). Sau đó **không endpoint nào trả lại token thô** — kể cả cho
   chính founder đã tạo ra nó.

2. **Database chỉ lưu SHA-256 hash của token, không lưu token thô.** Cột lưu
   trữ trong bảng invitation là `token_hash = SHA-256(token)`; khi accept,
   server hash token nhận được rồi so khớp `token_hash`. Nếu database bị lộ
   (backup, dump, truy vấn trái phép), không ai lấy lại được token gốc để
   accept invitation thay người khác.

3. **Invitation chỉ cấp được `member` hoặc `admin`.** `role_id` trong
   `CreateWorkspaceInvitationParams` giới hạn đúng `InvitationRole = "member"
   | "admin"`. Không invitation nào được cấp `founder`/`co-founder` — vai trò
   đó chỉ tồn tại từ luồng tạo workspace (`createNewCompany`) hoặc một cơ chế
   chuyển giao quyền founder riêng biệt, ngoài phạm vi ADR này.

4. **Ai được issue/revoke invitation:** chỉ **founder, co-founder, hoặc
   admin** của đúng workspace đó. Kiểm tra vai trò này phải chạy ở server
   (đọc `workspaceMemberships.roleId` của caller trong đúng `workspace_id`),
   không suy diễn từ token hay tin tưởng input client. Một `admin` được mời
   bởi invitation khác vẫn có quyền issue/revoke invitation tiếp theo (không
   giới hạn chỉ founder).

5. **Email phải khớp principal lúc accept.** `AcceptWorkspaceInvitationParams`
   chỉ nhận `token`; server tra invitation theo `token_hash`, lấy `email` đã
   lưu trong invitation, rồi bắt buộc **email đó trùng với email của principal
   đang gọi accept** (so sánh case-insensitive sau chuẩn hoá, khớp cách so
   sánh email hiện dùng cho đăng nhập). Nếu người đang đăng nhập có email khác
   — kể cả khi họ có token hợp lệ do bị lộ — accept phải từ chối
   (`permission_denied`), không tự động gán invitation đó cho principal hiện
   tại.

6. **Expiry mặc định 168 giờ (7 ngày).** `expires_in_hours` là optional, mặc
   định `168` khi không truyền. Invitation quá hạn chuyển `status = "expired"`
   (có thể là lazy check tại thời điểm accept, không bắt buộc job quét nền) và
   accept một invitation hết hạn phải từ chối, không tự gia hạn ngầm.

7. **Token single-use.** Sau khi accept thành công, `status` chuyển
   `"accepted"` và token không dùng lại được — accept lần thứ hai với cùng
   token phải từ chối (invitation không còn ở trạng thái `"pending"`).

8. **Retry sau accept trả về membership hiện có, không tạo bản ghi thứ hai.**
   Nếu accept được gọi lại (network retry, double-click, client resend) sau
   khi đã thành công — hoặc nếu principal đã là member của workspace đó qua
   đường khác — response phải trả về **membership hiện có** (idempotent theo
   nghĩa nghiệp vụ: kết quả cuối cùng giống nhau), tuyệt đối không insert thêm
   một row `workspaceMemberships` thứ hai cho cùng `(workspace_id, user_id)`.
   Đây là cùng nguyên tắc idempotency mà `joinExistingCompany` hiện tại đã áp
   dụng đúng cho trường hợp "đã là member" — giữ lại hành vi này khi migrate,
   chỉ thay điều kiện được phép tạo membership MỚI.

### Không nằm trong phạm vi Task 1

- Đóng endpoint `POST /platform/auth/companies/join` hiện tại (join bằng
  `company_id` trần) — việc này thuộc Task 2+, sau khi invitation flow đã có
  implementation và test xanh.
- Schema bảng invitation cụ thể (tên bảng, migration SQL) — thuộc task sau,
  ADR này chỉ chốt interface/contract logic.
- Cơ chế gửi email lời mời (SMTP/provider) — ngoài phạm vi ADR.

## Consequences

- **Không có compatibility fallback cho client cũ.** Khi endpoint join-by-ID
  bị đóng ở task sau, mọi client (Flutter app, script, integration ngoài) gọi
  `POST /platform/auth/companies/join` với `{ company_id }` trần sẽ nhận
  `permission_denied` vĩnh viễn — không có chế độ "vẫn chấp nhận company_id
  cho phiên bản app cũ". Client bắt buộc phải chuyển sang luồng tạo/nhận
  invitation trước khi endpoint cũ bị đóng. README được cập nhật để ghi rõ
  điều này ngay từ bây giờ, dù endpoint chưa đóng trong Task 1.
- Test đỏ thêm trong `services/cosa/tests/control-plane.test.ts` ("rejects a
  second user joining an existing company by bare company_id (no
  invitation)") sẽ tiếp tục fail cho tới khi Task 2+ thay `joinExistingCompany`
  bằng logic invitation-only. Đây là tín hiệu tiến độ dự kiến, không phải bug
  cần vá ngay trong Task 1.
- Test hiện có "joins an existing company for a new user" (đang document hành
  vi cũ là thành công) sẽ phải sửa hoặc xoá ở Task 2+ khi hành vi đổi sang từ
  chối — không sửa trong Task 1 để giữ đúng phạm vi "chỉ thêm ADR + test đỏ,
  không đổi implementation".

## Cross-links

- `README.md` — mục "Điều kiện bắt buộc trước khi mở workspace ra bên ngoài",
  mục 1 ("Gia nhập workspace").
- `services/cosa/services/company.service.ts::joinExistingCompany` — implementation
  hiện tại (insecure), sẽ bị thay ở task sau.
- `services/cosa/handlers/company.handler.ts::joinCompanyFor` /
  `joinCompany` — endpoint hiện tại nhận `company_id` trần.
- `services/cosa/tests/control-plane.test.ts` — test đỏ chứng minh lỗ hổng.
- `docs/architecture/adr/ADR-COSA-DELEGATION-002-agent-run-tenant-token.md` —
  tham khảo format ADR và nguyên tắc "mỗi secret/token đúng một chiều, không
  tái dùng chéo", cùng tinh thần với nguyên tắc token single-use/hash-only ở
  ADR này.
- `.superpowers/sdd/2026-09-08-platform-authority-durability-hardening/` —
  brief và report của Task 1 cùng các task tiếp theo trong chuỗi hardening
  này.
