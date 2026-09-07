# Thiết kế đa ngôn ngữ VI–EN và module visibility

## Mục tiêu

Cho phép mỗi người dùng COSA dùng giao diện tiếng Việt hoặc tiếng Anh, đồng bộ
lựa chọn đó từ profile về thiết bị, và nhận phản hồi từ agent theo ngôn ngữ đã
lưu. Đồng thời, mỗi workspace và người dùng có thể kiểm soát việc hiển thị các
module Finance, Legal và CRM mà không thay đổi quyền, dữ liệu hoặc suy diễn
quốc gia/pháp luật từ ngôn ngữ.

## Phạm vi phát hành

- Chỉ hỗ trợ BCP-47 `vi-VN` và `en-US`.
- Dịch toàn bộ chuỗi hiển thị do Flutter sở hữu, gồm trạng thái rỗng, lỗi,
  điều hướng, profile, chat, Finance, Legal, CRM và luồng giọng nói.
- Dùng GetX `Translations` và `Get.updateLocale`, không đưa chuỗi dịch vào
  backend hoặc dùng dịch máy khi runtime.
- Lưu `preferredLocale` theo người dùng ở COSA Control Plane. Đây là nguồn
  chuẩn giữa các thiết bị; cache local chỉ phục vụ khởi động và offline.
- Agent trả lời theo `preferredLocale`; ngôn ngữ của câu nhập không tự đổi
  preference. Chỉ lệnh rõ ràng của người dùng trong một lượt mới được override
  phản hồi cho lượt đó.
- Finance, Legal và CRM có hai tầng trạng thái: workspace cho phép hiển thị,
  người dùng chọn hiện/ẩn. Cả hai chỉ điều khiển discovery/UI, không thay thế
  kiểm tra capability, role, membership hay governance ở API.

## Ngoài phạm vi

- Không thêm country, jurisdiction, tax residency, currency mặc định mới,
  accounting regime mới hoặc legal rule mới.
- Không thay đổi TT58, VND, legal applicability, dữ liệu tài chính hay audit.
- Không tự dịch nội dung pháp luật/kế toán, dữ liệu nghiệp vụ do người dùng
  nhập, evidence hoặc artifact lịch sử.
- Không dùng locale để quyết định tiền tệ, timezone, jurisdiction hoặc quyền.

## Quyết định kiến trúc

### 1. Locale là preference của người dùng, không phải của workspace

Control Plane thêm `profiles.preferred_locale`, bắt buộc là `vi-VN` hoặc
`en-US`, mặc định `vi-VN` để giữ nguyên hành vi tenant hiện tại. `GET
/platform/auth/me` trả field này và `PATCH /platform/auth/me` cho chính chủ
đổi field này; endpoint từ chối locale khác thay vì fallback âm thầm.

Sau khi login hoặc `SessionController.activateWorkspace()` xác thực identity,
Flutter nhận profile server-authoritative, áp dụng `Get.updateLocale`, rồi
cache `preferred_locale` bằng SharedPreferences. Cache không phải credential;
token vẫn ở secure storage như hiện tại. Khi offline, app được phép dựng UI
theo cache nhưng không được ghi đè preference server khi kết nối trở lại.
Khi đổi ngôn ngữ, UI chỉ đổi sau khi PATCH thành công; khi PATCH lỗi, UI và
cache giữ locale trước đó, hiển thị lỗi bằng locale hiện tại.

### 2. GetX translation catalogue là nguồn chuỗi giao diện

Tạo `AppTranslations extends Translations` với map cố định cho `vi_VN` và
`en_US`. Mọi chuỗi user-facing trong `frontend/lib/` được chuyển sang key
semantic, ví dụ `profile.language.title`, `chat.empty.title`,
`finance.visibility.unavailable`; code, API path, enum, log/error kỹ thuật và
identifier không được dịch. `GetMaterialApp` dùng locale do một
`LocaleController` hydrate từ profile/cache quản lý, không còn khóa cứng
`Locale('vi', 'VN')`.

Ngày, số và tiền trong UI dùng `intl` với locale hiện tại. Giá trị currency
vẫn là mã ISO/API trả về; formatting không được đổi currency. Các component
hiện gắn `VND`, `TT58`, hoặc tên biểu mẫu Việt Nam được dịch nhãn hiển thị,
nhưng logic nghiệp vụ và lối vào TT58 giữ nguyên.

### 3. LocaleContext đi xuyên qua agent

`LocaleContext` chỉ gồm locale output hợp lệ (`vi-VN` hoặc `en-US`) và nguồn
quyết định (`profile`, `turn_override`, `system_fallback`). Nó được resolve ở
boundary có identity trước khi tạo `RunRequest`. Request chat gửi locale hiện
tại; backend xác thực membership rồi resolve preference server-side để client
không thể ép locale người dùng khác. `RunRequest.locale` luôn nhận giá trị đã
resolve.

Thứ tự chọn phản hồi là: lệnh ngôn ngữ rõ ràng, giới hạn trong một lượt →
`profiles.preferred_locale` của principal → `vi-VN` cho system run không có
người dùng. Nội dung người dùng viết bằng bất kỳ ngôn ngữ nào không có tác
dụng thay đổi thứ tự này. Lệnh override được ghi vào metadata run có cấu trúc,
không được suy ra bằng substring từ prompt.

Các worker dùng `prepare_request`/`prepare_run`, autopilot và copilot phải
nhận locale trong payload đã được server tạo. Copilot bỏ prompt tiếng Việt cố
định; instruction chung vẫn canonical English, còn nội dung user-facing được
render theo `LocaleContext`. Voice transcription gửi language tag theo locale
đã resolve (`vi` cho `vi-VN`, `en` cho `en-US`).

### 4. Prompt và skill

Prompt platform có thể tiếp tục canonical English. Locale policy của
`PromptBundle` bắt buộc dùng `RunRequest.locale`. Skillpack built-in giữ một
definition/hash và instruction governance; không nhân đôi skill ID/version
chỉ để dịch. Khi skill tạo prose user-facing, kernel locale policy điều khiển
đầu ra. Bản dịch curated của skill ở tương lai phải là versioned content có
hash riêng và policy selection rõ ràng; không thuộc release này.

### 5. Module visibility tách khỏi entitlement và jurisdiction

Định nghĩa module key cố định: `finance`, `legal`, `crm`. Workspace operator
(founder/co-founder/admin) có thể đặt `workspace_module_settings.enabled`.
Người dùng là thành viên workspace có thể đặt `user_module_preferences.visible`
cho một module đã enabled. Quy tắc effective visibility là:

```
effectiveVisible = workspaceEnabled && userVisible
```

`workspaceEnabled=false` ẩn entry point và trả trạng thái disabled cho UI;
không xóa dữ liệu, không thu hồi role, không đổi endpoint contract. API vẫn
phải làm authorization bình thường. Nếu một API cần product entitlement để
tránh dùng module khi workspace disable, entitlement đó là server-side gate
riêng, không dựa vào việc frontend ẩn nút.

Visibility không phải country configuration. Khi sau này thêm quốc gia mới,
jurisdiction profile phải gắn với legal entity, có source/review/effective
date và accounting mapping riêng. Một user dùng `en-US` vẫn có thể vận hành
pháp nhân Việt Nam theo TT58; một user dùng `vi-VN` cũng không tự có quyền
dùng bộ quy định khác.

## Luồng dữ liệu

```text
profiles.preferred_locale (Control Plane)
  -> GET /platform/auth/me
  -> Flutter LocaleController + local cache
  -> Get.updateLocale / AppTranslations
  -> chat/voice request locale
  -> authenticated server resolution
  -> RunRequest.locale
  -> PromptBundle locale policy
  -> agent response

workspace_module_settings + user_module_preferences
  -> effective visibility DTO
  -> Flutter navigation and module entry points
```

## Hợp đồng API đề xuất

```ts
type SupportedLocale = "vi-VN" | "en-US";
type ModuleKey = "finance" | "legal" | "crm";

interface PlatformUserProfile {
  id: string;
  fullName: string | null;
  preferredLocale: SupportedLocale;
}

interface UpdateMeParams {
  preferredLocale?: SupportedLocale;
  // các field profile hiện có giữ nguyên
}

interface WorkspaceModuleVisibility {
  moduleKey: ModuleKey;
  workspaceEnabled: boolean;
  userVisible: boolean;
  effectiveVisible: boolean;
}
```

## Migration và tương thích ngược

- Migration chỉ expand: thêm `preferred_locale` nullable với default/backfill
  `vi-VN`, sau đó constraint/not-null trong cùng migration nếu database cho
  phép default an toàn.
- Thêm bảng settings/preferences với khóa duy nhất theo
  `(workspace_id, module_key)` và `(workspace_id, user_id, module_key)`.
- Backfill workspace settings: Finance, Legal, CRM enabled để giữ UI hiện
  tại; user preference `visible=true` được resolve khi chưa có row để tránh
  migration khổng lồ. Sau lần user đổi preference, persist explicit row.
- Không migration data Finance/Legal/CRM và không sửa row luật/kế toán.

## Bảo mật và tenancy

- `PATCH /platform/auth/me` chỉ cập nhật profile của caller; không nhận
  `user_id` từ body.
- Workspace module mutation bắt buộc workspace operator; user preference
  mutation yêu cầu membership và chỉ sửa caller.
- Tất cả query preference/filter phải bind workspace ID và user ID, không
  lookup theo user trên toàn cục khi tính visibility workspace.
- Locale không đi vào authorization, capability policy, financial approval,
  accounting predicate hoặc legal applicability.
- Worker/system run không được tin locale không có provenance trong payload;
  thiếu principal thì dùng `vi-VN` rõ ràng và ghi `system_fallback`.

## Tiêu chí nghiệm thu

1. Đổi profile từ `vi-VN` sang `en-US` phản ánh trên thiết bị khác sau login
   hoặc refresh profile; mất mạng không làm mất cache cũ.
2. Toàn bộ Flutter screen user-facing trong phạm vi được catalog hóa có bản
   dịch VI và EN, không còn `Text('...')` là copy user-facing trực tiếp.
3. User lưu `en-US` viết tiếng Việt vẫn nhận response agent tiếng Anh; request
   rõ ràng “reply in Vietnamese for this answer” chỉ đổi đúng lượt đó.
4. Chat, copilot, autopilot và voice gửi/resolve locale hợp lệ; giá trị lạ bị
   reject ở API boundary.
5. User A không đổi được profile User B; user ngoài workspace không đọc/đổi
   module preference workspace đó.
6. Finance/Legal/CRM bị ẩn đúng theo effective visibility, nhưng việc ẩn không
   thay đổi role/capability hay xoá dữ liệu.
7. Đổi VI/EN không thay đổi VND, TT58, legal entity, jurisdiction, tax hay
   accounting data.

## Kế hoạch phát hành

Phát hành theo bốn lát độc lập có rollback an toàn: (1) profile locale và
locale controller, (2) catalogue UI/voice, (3) propagation agent, (4) module
visibility. Mỗi lát có feature flag/route contract kiểm thử riêng và chỉ bật
sau khi migration expand, tenancy negative tests và regression test của luồng
đăng nhập/session xanh.
