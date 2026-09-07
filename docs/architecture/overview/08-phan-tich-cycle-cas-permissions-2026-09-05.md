# Phân tích bổ sung: chu kỳ thực thi, Cas.so và quyền hạn

Ngày rà soát: 2026-09-05. Code nền: `e4829b75`, nhánh `main`. Đây là phân tích và đề xuất, chưa phải thiết kế đã triển khai. Tài liệu 07 là kết quả audit trước; tài liệu này điều chỉnh khuyến nghị theo yêu cầu mới của founder. Không thay đổi application code.

**Ba quyết định định hướng**

1. Dùng phương pháp 12WY làm mẫu tổ chức thực thi; mô hình sản phẩm là chu kỳ N tuần do founder chọn. OKR xác định kết quả, chu kỳ tổ chức đợt thực hiện, weekly tổ chức cam kết và phản hồi.
2. Tích hợp đúng Cas.so, nền tảng trước đây mang tên bankHub. Đồng bộ giao dịch ngân hàng; khoản chi đi qua đề nghị chi → founder duyệt → QR người thụ hưởng → founder chuyển tiền → đối soát. Không cần triển khai agent tự chuyển tiền cho phạm vi này.
3. Cần quyền dạng dữ liệu để founder quản lý, nhưng phải hợp nhất các nguồn policy hiện có và enforce ở backend/gateway. Một bảng permissions hoặc chỉ dẫn trong prompt riêng lẻ không đủ.

**1. Chu kỳ N tuần, OKR và weekly**

**Code đã có gì, vướng ở đâu?**

| Bằng chứng code | Hệ quả |
|---|---|
| [Schema operations](/services/company/shared/db/schema/operations.ts:67) có `okr_cycles → okr_objectives → key_results`; đồng thời `twelve_week_cycles → weekly_plans → weekly_commitments → tasks` | Có hai mô hình mục tiêu và thực thi, chưa có liên kết KR trực tiếp trong commitment. `initiativeId` không bù được vì initiative hiện cũng không có FK tới KR |
| [Create cycle](/services/company/operations/services/twelve-week-year.service.ts:108) nhận `durationWeeks`, mặc định 12; nhận start/end độc lập | Backend đã có nền tảng linh hoạt; còn thiếu xác thực số tuần nguyên dương và lịch nhất quán tại đường tạo này |
| [Operating setup](/services/company/operations/strategy/services/project-operating-setup.service.ts:92) giới hạn P0 1–2 tuần, P1 2–4 tuần; kiểm lại khi kích hoạt | Lựa chọn độ dài chu kỳ đang bị buộc bởi thời lượng stage. Cần tách thời hạn kiểm chứng stage khỏi thời lượng chu kỳ |
| [Weekly goal](/services/company/operations/strategy/services/weekly-goal.service.ts:59) chọn cycle mới nhất rồi upsert `weekNo: 1` | Sửa mục tiêu tuần sau có thể sửa tuần đầu; cycle mới nhất chưa chắc là cycle đang chạy |
| [Modal chuyển chu kỳ](/frontend/lib/modules/strategy/widgets/twelve_wy/twelve_wy_modals.dart:370) nói tuần 13 bắt buộc | UX chưa phù hợp chu kỳ 2, 6 hoặc 16 tuần |
| [Weekly reviews](/services/company/shared/db/schema/strategy.ts:322) gắn workspace/ngày đầu tuần, không gắn weekly plan | Cần phân biệt review tổng hợp của founder và review từng kế hoạch dự án |
| [OKR scoring](/services/company/operations/services/okr-scoring.service.ts:1) dùng `current / target` | Không phản ánh tiến bộ từ baseline và chấm sai chỉ số cần giảm |

**Mô hình nghiệp vụ nên dùng**

| Thành phần | Câu hỏi được trả lời | Quy tắc đề xuất |
|---|---|---|
| Project stage | Đã có bằng chứng gì để sang bước tiếp theo? | Chuyển stage qua gate/evidence và quyết định có thẩm quyền; không tự chuyển vì hết N tuần |
| Objective + KR | Muốn đạt kết quả gì và đo bằng gì? | Có owner, phạm vi, thời hạn, baseline, target, loại chỉ số, nguồn đo |
| Chu kỳ thực thi | Trong đợt này tập trung vào kết quả nào? | Founder chọn tên, N tuần, ngày bắt đầu, mục tiêu và năng lực thực hiện |
| Weekly plan | Tuần này cam kết làm gì? | Gắn cycle, tuần cụ thể, cam kết có owner và tiêu chí hoàn thành |
| Task / agent run | Ai thực hiện từng việc bằng cách nào? | Task đóng khi đạt tiêu chí; run hoàn tất chưa mặc nhiên là task hoặc KR hoàn tất |
| Weekly review | Hoạt động và kết quả thực tế nói gì? | Đối chiếu cam kết, KR, cash, nghĩa vụ và quyết định tuần tiếp theo |

Quan hệ đề xuất: `Objective → KR ↔ chu kỳ thực thi → weekly plan → commitment → task`. Liên kết KR–cycle thể hiện đóng góp, không nhân bản cùng KR vào mỗi chu kỳ. Một KR có thể đi qua nhiều chu kỳ; một chu kỳ có thể phục vụ vài KR. Cần giới hạn số mục tiêu đồng thời theo năng lực làm việc, không bằng ràng buộc 1:1 trong DB.

Với founder đơn lẻ, mặc định cho kỳ OKR trùng kỳ thực thi để thao tác đơn giản. Khi cần mục tiêu dài hơn, cho phép một kỳ OKR bao phủ nhiều chu kỳ ngắn. Nếu lịch vượt ranh giới kỳ OKR, yêu cầu quyết định tiếp tục/đổi liên kết rõ ràng, không âm thầm kéo dài mục tiêu đã đóng. Không bắt founder ở discovery tạo OKR hình thức: commitment có thể phục vụ experiment, nghĩa vụ pháp lý hoặc vận hành thường xuyên, với mục đích và evidence tương ứng.

Tên UI nên là “Chu kỳ thực thi”, tên cụ thể founder tự đặt, ví dụ “Tìm 5 khách hàng pilot”. Cho mẫu 2/4/6/8/12 tuần và nhập N nguyên dương. Khi chọn 12 tuần, có thể gọi mẫu 12WY; khi chọn N khác, diễn đạt là chu kỳ tùy chỉnh theo cách tổ chức đó. Giới hạn P0/P1 trở thành gợi ý nhịp kiểm chứng, nếu cần vẫn giữ một deadline stage riêng. Không dùng deadline này để khóa N.

Kết thúc chu kỳ phải dựa trên ngày kết thúc thực tế. Review cuối kỳ là một sự kiện; thời gian nghỉ là lựa chọn, không có “tuần 13 bắt buộc” cho mọi chu kỳ. Khi đổi độ dài giữa kỳ, lưu revision/lý do và chỉ điều chỉnh lịch tương lai; không viết lại cam kết/score lịch sử. Chu kỳ dài có thể tạo tuần tương lai theo nhu cầu, không cần sinh toàn bộ task ngay từ đầu.

**Execution score và outcome score phải có hai nguồn dữ liệu khác nhau.** Ví dụ: mục tiêu 5 khách hàng pilot trong 6 tuần. Tuần này thực hiện 8/10 cuộc hẹn đã cam kết, execution score là 80%; mới có 2/5 pilot hợp lệ thì outcome progress là 40%. Hoàn thành 100% task không chứng minh đạt mục tiêu thị trường.

Với KR tuyến tính, có thể dùng `clamp((current - baseline) / (target - baseline), 0, 1)` cho tiến bộ từ baseline, xử lý riêng khi target bằng baseline. Đây là đề xuất cách đo, cần phân biệt với chỉ số “mức đạt target” trên dashboard. KR milestone, giữ trong một khoảng hoặc duy trì SLA cần bộ đánh giá riêng. Ví dụ baseline churn 10%, target 5%, current 8% tương ứng tiến bộ 40%; hàm hiện tại trả 100%. Khi đo doanh thu, baseline 100, target 200, current 150 thì tiến bộ là 50%, còn target attainment là 75%: phải ghi rõ đang hiển thị loại nào.

KR check-in nên có lịch sử observation: giá trị, kỳ đo, nguồn, evidence, người/hệ thống ghi nhận và thời điểm. Các chỉ số có độ trễ phải hiển thị độ mới dữ liệu. Không ghi đè currentValue rồi mất nguồn gốc. Score tuần nên suy ra từ cam kết đã chốt và kết quả đủ bằng chứng; nếu cho sửa thủ công thì phải là override có lý do. [Update weekly plan](/services/company/operations/services/twelve-week-year.service.ts:187) hiện nhận trực tiếp executionScore/outcomeScore từ caller.

Phần schema cần bổ sung có mục tiêu: liên kết cycle–KR, commitment–KR hoặc experiment/obligation; owner bằng WorkforceMember; observation KR. Weekly review tổng hợp workspace có thể tham chiếu nhiều weekly plan để phục vụ cuộc review chung của founder. Không nhất thiết biến mỗi màn hình thành một loại bảng mới.

Các invariant cần chốt khi triển khai: `1 ≤ weekNo ≤ N`; ngày tuần nằm trong cycle; cùng workspace/project hợp lệ; uniqueness cycle+weekNo; cùng một quy ước timezone/ngày đầu tuần cho tính lịch; chọn đúng cycle đang hoạt động theo phạm vi. Nếu mỗi project chỉ có một cycle đang chạy, enforce ở DB/service; nếu cho nhiều luồng, phải có stream/owner và yêu cầu chọn rõ. Không coi cycle mới nhất là cycle hiện tại.

**2. Finance: Cas.so, QR chi tiền và TT58**

**Phân biệt đúng sản phẩm Cas.so.** Website Cas.so xác nhận nền tảng này trước đây là bankHub. Không lấy hợp đồng API cũ ở developer.casso.vn làm hợp đồng mặc định cho tích hợp này. [Cas.so](https://cas.so/).

Transactions sử dụng scope `transaction`; founder liên kết qua Cas Link, backend đổi publicToken lấy accessToken rồi gọi GET `/transactions`. Luồng cấp quyền là `/grant/token → Cas Link → /grant/exchange`; token truy cập phải được giữ phía backend. [Transactions](https://cas.so/product/transactions/), [Cas Link](https://cas.so/general/link/).

QR Pay được mô tả là QR theo đơn hàng, có tài khoản ảo và nhận webhook kèm `paymentMeta.referenceNumber` để khớp tiền nhận với đơn hàng. Vì vậy QR Pay phù hợp thu tiền. Với chi cho nhà cung cấp bất kỳ, cần QR mã hóa tài khoản nhà cung cấp. API VietQR.io cho phép tạo QR từ ngân hàng, tài khoản nhận, số tiền và nội dung chuyển khoản; API này là lựa chọn cần đánh giá trong cùng hệ sinh thái, không mặc định có cùng grant/quyền với Cas QR Pay. [QR Pay](https://cas.so/product/qr-pay/), [VietQR generate](https://vietqr.io/en/generate/).

**Đối chiếu trực tiếp code với nhà cung cấp:**

- [GET bank transactions](/services/company/finance-legal/handlers/finance-tt58.handler.ts:96) chỉ đọc DB ứng dụng. [Bank connection service](/services/company/finance-legal/services/bank-connection.service.ts:44) tạo connection PENDING và giữ secretRef. Chưa thấy client Cas.so thực hiện grant/exchange/transactions trong phạm vi đã rà.
- [Webhook handler](/services/company/finance-legal/handlers/cas-webhook.handler.ts:7) nhận trường rawPayload dạng string. [Webhook service](/services/company/finance-legal/services/cas-webhook.service.ts:11) chờ eventId/eventType/connectionId/workspaceId/data. Mẫu công bố của Cas.so là raw JSON chứa webhookType/webhookCode/grantId/transaction. Gửi mẫu đó trực tiếp vào contract hiện tại sẽ không đáp ứng đầu vào; nếu đã có adapter bên ngoài thì adapter cần được chứng minh và kiểm thử, chưa thấy trong code đã đọc. [Mẫu chính thức](https://cas.so/product/qr-pay/).
- Code tự giả định header X-Cas-Signature với HMAC SHA256. Trang webhook công khai đã đọc chưa xác nhận cơ chế này. Cần xác nhận contract bảo vệ webhook cho môi trường triển khai, không bỏ xác thực để làm integration chạy. [Webhook Cas.so](https://cas.so/general/api/webhook/).
- Mapping workspace phải được suy ra từ grant/connection đã liên kết ở server. Chuẩn hóa amount, chiều thu/chi, currency và thời gian từ schema provider; không mặc định direction=IN hoặc amount=0 khi dữ liệu chưa đủ như [ingestion hiện tại](/services/company/finance-legal/services/cas-webhook.service.ts:150).
- Inbox đã lưu dữ liệu và trạng thái, có nền tảng chống trùng. Cần worker retry cho bản ghi FAILED: handler hiện trả ok sau khi lỗi xử lý nội bộ và bỏ qua duplicate, nên provider retry không thay thế được cơ chế retry nội bộ.

Luồng dữ liệu đề xuất: đồng bộ lịch sử khi kết nối; GET định kỳ để bù thiếu, phân trang/cursor theo contract thực; nhận webhook ở những scope/ngân hàng hỗ trợ; hợp nhất tất cả qua cùng ingestion idempotent. Không giả định scope transaction tự cấp mọi Balance Hook, vì hướng dẫn Balance Hook hiện nêu qrpay/virtual_account. Cần chốt hỗ trợ thực tế theo ngân hàng và grant. [Balance Hook](https://cas.so/product/balance-hook/).

**Luồng chi founder quét QR**

`Đề nghị chi → kiểm tra hồ sơ/ngân sách/quyền → founder duyệt → QR người thụ hưởng → founder chuyển bằng app ngân hàng → nhận giao dịch đi → đối soát → cập nhật thanh toán và sổ liên quan`.

1. Đề nghị chi có pháp nhân, người thụ hưởng, ngân hàng/tài khoản, số tiền/currency, nội dung, chứng từ gốc, hạn trả, project/budget và người đề nghị.
2. Duyệt ràng buộc với phiên bản cùng hash các trường ảnh hưởng thanh toán. Sửa người nhận, tài khoản, số tiền hoặc nội dung sau duyệt phải quay về xét duyệt. QR chỉ tạo từ bản đã duyệt, không từ payload tự do của model.
3. Màn hình chi hiển thị tên người nhận, ngân hàng, tài khoản, số tiền, mã đề nghị và QR. Founder kiểm tra trên app ngân hàng trước khi xác nhận chuyển.
4. “Đã hiển thị QR”, “founder báo đã chuyển” và “đã thấy giao dịch ngân hàng” là các trạng thái khác nhau. Không ghi PAID khi tạo QR hoặc khi agent nói hoàn tất.
5. Tự khớp dựa trên tài khoản nguồn, tiền tệ, số tiền, mã tham chiếu và dữ liệu người nhận nếu provider có. Trường thiếu hoặc nhiều ứng viên thì đưa vào review, không dựa riêng số tiền/thời gian. Dùng allocation để hỗ trợ một phần/nhiều khoản và tránh đối soát hai lần.
6. Nếu founder chi bằng tài khoản cá nhân chưa liên kết, CAS của tài khoản doanh nghiệp không chứng minh được khoản chi đó. Thu thập bằng chứng, phân biệt xác nhận thủ công và xử lý khoản founder chi hộ/hoàn ứng theo hồ sơ thực tế.
7. Hủy/hết hạn đề nghị trong app không chứng minh QR đã lưu trên điện thoại mất khả năng sử dụng. Nếu tiền đi muộn vẫn ghi nhận giao dịch thực và đưa vào xử lý ngoại lệ. Khoản đã trả chỉ còn xem biên nhận; UI tránh khuyến khích quét lại.

Nên có payment request và liên kết phân bổ thanh toán tới bank transaction/chứng từ. Tách trạng thái duyệt, trạng thái thanh toán và trạng thái ghi sổ: một khoản có thể được duyệt nhưng chưa trả, trả một phần, hoặc đã trả nhưng đang thiếu hồ sơ phân loại. Việc ghi nhận công nợ/chứng từ có thể xảy ra trước thanh toán; luồng trên không có nghĩa mọi nghiệp vụ kế toán đều đợi tiền ngân hàng.

Với yêu cầu mới, sửa khuyến nghị audit trước: workflow [finance.payout.execute](/apps/cosa/workflows/specs.py:28) nên ngừng quảng bá/không cho chạy hoặc thay bằng workflow đề nghị chi–QR–đối soát. Không ưu tiên xây executor chuyển khoản tự động. Finance agent đủ vai trò chuẩn bị hồ sơ, phân loại và đề xuất đối soát; founder thực hiện lệnh ngân hàng.

**TT58 là lớp ghi sổ/báo cáo, CAS là nguồn dữ liệu ngân hàng.** Theo Bộ Tài chính, TT58/2026/TT-BTC hướng dẫn chế độ kế toán doanh nghiệp siêu nhỏ, hiệu lực từ 01/07/2026 và áp dụng cho năm tài chính bắt đầu từ ngày đó trở đi. Hướng dẫn đơn giản hóa sổ, không bắt buộc sử dụng hệ thống tài khoản kế toán; BCTC gồm Báo cáo tình hình tài chính và Báo cáo kết quả hoạt động kinh doanh. [Bộ Tài chính](https://www.mof.gov.vn/tin-tuc-tai-chinh/tin-chinh-sach-tai-chinh/quy-dinh-moi-ve-che-do-ke-toan-cho-doanh-nghiep-sieu-nho).

Hệ quả thiết kế đề xuất: cấu hình chế độ theo pháp nhân, tính áp dụng và năm tài chính; bộ sổ/báo cáo có version. Không áp nhãn TT58 cho mọi workspace hoặc đổi chế độ chỉ vì ngày hiện tại qua 01/07. Cần đối chiếu toàn văn/phụ lục khi triển khai biểu mẫu; lần rà này chưa xác nhận đầy đủ mọi mẫu sổ trong code.

Không suy ra doanh thu từ mọi giao dịch tiền vào hay chi phí từ mọi giao dịch tiền ra. Tiền vay/góp vốn/chuyển nội bộ, tạm ứng, hoàn tiền, thanh toán công nợ cần phân loại theo hồ sơ. Dashboard cash và báo cáo kết quả kinh doanh có thể dùng cùng giao dịch nền nhưng khác quy tắc tổng hợp. Phần ngân hàng không thay chứng từ, công nợ, kỳ kế toán và các nghiệp vụ không qua ngân hàng.

[FinanceTT58Service frontend](/frontend/lib/modules/finance/services/finance_tt58_service.dart:1) đang throw UnimplementedError và còn nhắc TT58/2024; [controller](/frontend/lib/modules/finance/controllers/finance_controller.dart:139) vẫn gọi nó. Cần nối UI tới nghiệp vụ thực và map bộ báo cáo đúng chế độ, không coi màn hình mang tên TT58 là đã tuân thủ. Các lỗi khóa kỳ, currency và đối soát cạnh tranh ở audit 07 vẫn cần xử lý.

**3. Quyền hạn founder quản lý và agent thực thi**

Có, nên có permissions dạng dữ liệu. Nhưng hệ thống đã có nhiều cấu phần quyền, nên mục tiêu là một mô hình thống nhất, không thêm bảng độc lập thứ ba rồi mỗi đường gọi đọc một bảng.

| Hiện trạng | Phần cần điều chỉnh |
|---|---|
| [TenantContext](/services/company/identity/services/tenant-context.service.ts:21) ánh xạ role sang read/write/* trong code | Bổ sung quyền hành động cụ thể; membership chỉ xác định thuộc workspace |
| [workspace_capability_policy](/services/company/shared/db/schema/operations.ts:309) lưu workspace/capability/decision | Thiếu chủ thể được cấp, phạm vi, điều kiện, version/lịch sử |
| [workspace_agent_policy](/services/cosa/storage/schema.ts:68) lưu tool pattern và decision riêng | Cần phân định policy business gốc và bản phân phối cho runtime; không hai nơi chỉnh cùng ý nghĩa độc lập |
| [Engagement authority/grants](/services/company/shared/db/schema/customer-engagement.ts:169) có WorkforceMember, thời hạn, policy version | Tái sử dụng nguyên tắc identity và ủy quyền; giữ binding chuyên biệt engagement khi cần |
| [Policy mutation](/services/company/operations/services/execution-plan.service.ts:689) chưa kiểm command permission tại service | Sửa ngay quyền agent.policy.manage/permissions.manage, không chỉ bổ sung UI quản trị |

Phân biệt ba khái niệm: permission cho phép chủ thể làm hành động nghiệp vụ trên tài nguyên; capability là công cụ agent có thể gọi; approval là chấp thuận một hành động cụ thể, không tự cấp quyền lâu dài. Agent được cài tool không có nghĩa được dùng với mọi workspace/project hoặc mọi số tiền.

**Các nhóm dữ liệu đề xuất, tên bảng là gợi ý để thiết kế migration:**

| Nhóm | Nội dung |
|---|---|
| permission_definitions | Catalog quyền được code hỗ trợ, resource/action, mức rủi ro, có giới hạn chỉ con người hay không; founder không tự tạo chuỗi quyền mà backend không hiểu |
| workspace_roles | Vai trò mẫu và vai trò founder tùy chỉnh trong workspace |
| role_permissions | Vai trò được làm hành động nào; scope/điều kiện có schema kiểm soát |
| member_role_assignments | Gán role cho WorkforceMember, workspace/project/phạm vi, thời hạn, người cấp; áp dụng cả human và AI |
| Policy rules có version | Mở rộng/hợp nhất policy hiện có: ALLOW/DENY/REQUIRE_APPROVAL, hạn mức kèm currency, điều kiện, người duyệt, thời hạn và audit |

Không nhất thiết tạo mới cả năm nhóm nếu bảng hiện có đáp ứng. Company nên sở hữu quyền hành động nghiệp vụ; COSA có thể giữ các giới hạn runtime/platform riêng và nhận bản policy có version. Cần phân biệt giới hạn nền tảng với chính sách founder để chúng cùng được kiểm tra, không đè nhau.

Quyền thực tế của agent phải đồng thời thỏa mãn: quyền của principal thực thi; phạm vi ủy quyền của người/service giao việc; capability trong AgentSpec; workspace/project/task scope; connector grant còn hiệu lực; trạng thái nghiệp vụ và policy hiện hành; approval hợp lệ nếu được yêu cầu. Một nguồn DENY hoặc invariant không thỏa thì chặn. Không có quyền rõ ràng cho hành động thì từ chối, không tự ALLOW chỉ vì chưa có rule.

Enforce tại Company service cho cả UI/API và ở gateway trước tool side effect. Gateway không thay tenant guard của service. Kiểm lại quyền/connector khi resume hoặc retry; phê duyệt cũ không phục hồi quyền đã thu hồi. Reuse approval binding run/tool_call/checkpoint hiện có, bổ sung request version/hash cho các nghiệp vụ tài chính. Audit lưu principal, delegator, policy version, tài nguyên, quyết định, approver và kết quả.

Founder cấu hình quyền trong giới hạn sản phẩm: không cho phép vượt workspace, sửa lịch sử audit hoặc biến một lời khẳng định của model thành bằng chứng tiền đã chuyển. Với thiết kế QR hiện tại, agent không có quyền ký chuyển tiền ngân hàng. Founder đơn lẻ vẫn có thể tự tạo và duyệt khoản chi nếu chính sách cho phép; không ép hai người duyệt với mọi doanh nghiệp nhỏ.

**Ma trận mặc định đề xuất:**

| Hành động | Founder | Finance agent | Operations agent | Auditor |
|---|---|---|---|---|
| Xem giao dịch ngân hàng | Có | Theo phạm vi được giao | Chỉ tổng hợp cần cho công việc | Đọc theo phạm vi |
| Tạo đề nghị chi | Có | Có, nếu được cấp quyền | Có thể đề nghị trong project được giao | Không |
| Phê duyệt chi | Có, theo policy | Không | Không | Không |
| Tạo/hiển thị QR đã duyệt | Có | Qua service, chỉ đúng bản đã duyệt | Theo quyền xem khoản chi | Chỉ đọc nếu được cấp |
| Xác nhận chuyển trên app ngân hàng | Founder thực hiện | Không | Không | Không |
| Đề xuất đối soát | Có | Có | Không mặc định | Không sửa |
| Chấp nhận đối soát | Có | Chỉ theo rule và bằng chứng đủ điều kiện | Không mặc định | Không |
| Soạn kế hoạch/cam kết tuần | Có | Trong phần việc tài chính | Có, trong scope | Không |
| Sửa target KR đã chốt | Có, lưu revision | Chỉ đề xuất | Chỉ đề xuất | Không |
| Sửa quyền/policy | Founder hoặc người được ủy quyền rõ | Không tự cấp quyền | Không tự cấp quyền | Không |

UI nên hiển thị theo người/agent × hành động nghiệp vụ với ba lựa chọn “Cho phép / Cần duyệt / Không cho phép”, kèm scope và điều kiện khi cần. Trước khi lưu cho founder xem ví dụ hành động sẽ được cho phép/chặn và những rule bị tác động. “Có quyền tạo QR” tuyệt đối không được trình bày thành “có quyền chuyển tiền”.

**4. Nối ba phần và thứ tự thực hiện**

Một ví dụ xuyên suốt: KR 5 pilot → chu kỳ 6 tuần → tuần 2 cam kết phỏng vấn và onboarding → cần khoản chi dịch vụ → agent lập đề nghị theo budget/project → founder duyệt và quét QR → CAS ghi nhận tiền đi → đối soát/ghi sổ → weekly review cập nhật execution, pilot thực tế và cash. Chi tiền hoặc hoàn thành onboarding task chưa đủ để cộng một pilot nếu tiêu chí pilot chưa đạt.

Không cần tăng số agent để có vòng này. Strategy chịu trách nhiệm đề xuất mục tiêu và giải thích kết quả; Operations phân rã, theo dõi cam kết; Finance chuẩn bị chi/đối soát/cash; Legal cung cấp điều kiện áp dụng và nghĩa vụ; founder chốt quyết định. Các vai trò có thể là skill/workflow trên agent hiện có, với quyền và đầu ra rõ.

Thứ tự đề xuất:

1. Sửa quyền command và thu hồi policy; xác định một nguồn quyền nghiệp vụ thống nhất. Đồng thời định nghĩa rõ principal/grant Cas và contract webhook thực.
2. Sửa lịch cycle/weekly, bỏ giả định tuần 1/13; tách stage deadline khỏi N; nối commitment–KR và chuẩn hóa score/evidence.
3. Hoàn thiện Cas Link, Transactions, ingestion/webhook/retry; thêm đề nghị chi–QR–đối soát với founder chuyển tiền.
4. Nối frontend finance, sổ/báo cáo theo pháp nhân/năm tài chính, khóa kỳ và phân loại nghiệp vụ; hoàn thiện weekly review tổng hợp.

Kiểm chứng khi triển khai phải bao gồm: chu kỳ 2/6/12/16 tuần; sửa mục tiêu ở tuần 2 không đổi tuần 1; chỉ số cần giảm và có baseline; webhook mẫu Cas thật, duplicate và retry sau lỗi; GET/webhook cùng một giao dịch không ghi đôi; đổi người nhận sau duyệt; founder báo đã chuyển nhưng chưa có bank evidence; auditor sửa policy bị từ chối; agent retry sau thu hồi quyền bị chặn; phạm vi hai workspace tách biệt.

Giới hạn kiểm chứng của lần bổ sung: trace tĩnh code/service/schema/caller và đối chiếu nguồn công khai; chưa gọi Cas sandbox/production, chưa dùng tài khoản ngân hàng thật, chưa xác nhận toàn bộ phụ lục TT58, chưa triển khai hoặc chạy integration tests mới. Kết quả test của audit 07 giữ nguyên phạm vi đã nêu, không chứng minh các phần đề xuất này đã hoạt động.
