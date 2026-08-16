# Tài liệu triển khai trên Google AI Studio

## SaaS quản trị kế toán doanh nghiệp siêu nhỏ theo Thông tư 58/2026/TT-BTC

**Cách dùng:** Tải kèm tệp `BTC-TT-58-2026.pdf` vào cùng cuộc trò chuyện Google AI Studio, sau đó dán toàn bộ phần **MASTER PROMPT** bên dưới. Yêu cầu AI Studio xây theo từng giai đoạn nhưng phải giữ nguyên mô hình dữ liệu và quy tắc tuân thủ đã nêu.

**Nguồn pháp lý:** Thông tư 58/2026/TT-BTC, ban hành ngày 25/05/2026, hiệu lực từ 01/07/2026, hướng dẫn chế độ kế toán cho doanh nghiệp siêu nhỏ. Tài liệu này chuyển hóa yêu cầu của Thông tư thành đặc tả sản phẩm/kỹ thuật. Đây không thay thế ý kiến của kế toán viên hoặc tư vấn thuế.

---

# MASTER PROMPT

Bạn là một nhóm sản phẩm và kỹ thuật gồm: Product Manager SaaS B2B, kiến trúc sư Next.js/PostgreSQL, chuyên gia bảo mật dữ liệu tài chính, UX designer tiếng Việt và chuyên gia phân tích nghiệp vụ kế toán doanh nghiệp siêu nhỏ Việt Nam.

Hãy xây dựng ứng dụng web SaaS tên tạm thời **Sổ Nhỏ**: quản trị kế toán cho doanh nghiệp siêu nhỏ và hộ/cá nhân kinh doanh tự nguyện áp dụng Thông tư 58/2026/TT-BTC. Tôi đã đính kèm bản PDF của Thông tư trong cuộc trò chuyện. Trước khi viết mã, hãy đọc PDF, lập bảng đối chiếu yêu cầu pháp lý với từng chức năng và giữ bảng này trong `docs/compliance-mapping.md`.

Không chỉ tạo giao diện mẫu. Hãy tạo một ứng dụng có kiến trúc, cơ sở dữ liệu, kiểm soát truy cập, quy tắc nghiệp vụ, dữ liệu minh họa, kiểm thử và hướng dẫn chạy đầy đủ. Ưu tiên tính đúng của sổ/báo cáo hơn hiệu ứng giao diện.

## 1. Mục tiêu sản phẩm và ranh giới

1. Ứng dụng là SaaS đa doanh nghiệp (`workspace`), mỗi workspace là một doanh nghiệp/hộ kinh doanh độc lập hoàn toàn về dữ liệu.
2. Phiên bản đầu phục vụ **doanh nghiệp siêu nhỏ theo TT58**, không tự nhận hỗ trợ đầy đủ doanh nghiệp áp dụng Thông tư 133 hoặc 200.
3. Phần mềm hỗ trợ nhập liệu, quản trị chứng từ, ghi sổ, lập báo cáo và đối soát. Không được khẳng định tự động quyết toán/nộp thuế chính xác tuyệt đối hoặc thay thế tư vấn thuế.
4. Thông tư quy định sổ và báo cáo; việc xác định nghĩa vụ, tỷ lệ, thuế suất thuế vẫn theo pháp luật thuế. Vì vậy không mã hóa cứng thuế suất vào mã nguồn. Dùng danh mục quy tắc có hiệu lực theo thời gian và luôn hiển thị trạng thái “Cần kế toán xác nhận” trước khi chốt kỳ.
5. Giao diện tiếng Việt, tiền mặc định VND, múi giờ `Asia/Ho_Chi_Minh`, lưu số tiền bằng `numeric/decimal`, tuyệt đối không dùng `float`.

## 2. Công nghệ bắt buộc

- Next.js hiện hành, TypeScript, App Router, Server Components và Route Handlers.
- PostgreSQL và Supabase cho Auth, Database, Storage, Row Level Security. Tách lớp truy cập dữ liệu để sau này có thể thay Supabase mà không đổi nghiệp vụ.
- ORM kiểu Drizzle hoặc Prisma; chọn một và dùng nhất quán.
- Zod cho kiểm tra dữ liệu đầu vào; React Hook Form cho biểu mẫu; Tailwind CSS và thư viện component dễ truy cập.
- Xuất Excel bằng thư viện đáng tin cậy, xuất PDF từ server/template có kiểm thử bố cục.
- Dùng background job/queue cho sinh báo cáo, tính khấu hao, khóa sổ, import hóa đơn/sao kê. Không đặt tác vụ dài trong request của người dùng.
- Không để khóa bí mật, service role key hoặc logic kiểm tra quyền ở phía trình duyệt.

Tạo `.env.example`, `README.md`, migration SQL, seed data, test và hướng dẫn cấu hình Supabase. Nếu môi trường Google AI Studio không kết nối được Supabase, hãy tạo adapter mock chạy được cục bộ, nhưng vẫn tạo đầy đủ schema/migration thật.

## 3. Mô hình nghiệp vụ - bốn hồ sơ thuế

Trong onboarding, người dùng bắt buộc chọn một hồ sơ thuế hiệu lực theo năm tài chính. Thiết kế bằng hai thuộc tính ghép lại, không tạo bốn code path rời rạc:

- `vat_method`: `DIRECT_PERCENT_REVENUE` hoặc `DEDUCTION`.
- `cit_method`: `DIRECT_PERCENT_REVENUE` hoặc `TAXABLE_INCOME`.

| Mã hồ sơ | GTGT | TNDN | Sổ bắt buộc |
|---|---|---|---|
| P1 | Tỷ lệ % trên doanh thu | Tỷ lệ % trên doanh thu | S1-DNSN |
| P2 | Tỷ lệ % trên doanh thu | Trên thu nhập tính thuế | S2a, S2b, S2c, S2d-DNSN |
| P3 | Khấu trừ | Tỷ lệ % trên doanh thu | S3a, S3b-DNSN |
| P4 | Khấu trừ | Trên thu nhập tính thuế | S2b, S2c, S2d, S3b-DNSN |

Sổ tự chọn cho mọi hồ sơ khi cần quản trị: S4a công nợ, S4b TSCĐ, S4c thuế khác, S4d vốn chủ sở hữu.

Không cho sửa trực tiếp hồ sơ thuế/chế độ kế toán của kỳ đã bắt đầu. Khi thay đổi, tạo một `accounting_policy_version` mới chỉ có hiệu lực từ ngày đầu năm tài chính tiếp theo; có luồng chuyển số dư đầu kỳ.

## 4. Nguyên tắc lõi: chứng từ là nguồn dữ liệu, sổ là kết quả

Không xây phần mềm theo cách người dùng nhập cùng một nghiệp vụ ở nhiều sổ. Mỗi nghiệp vụ tạo ra một `document` cùng các `document_lines`, sau đó engine ghi sổ sinh `register_entries` có truy vết về chứng từ nguồn.

Ví dụ bán hàng trả chậm:

1. Người dùng lập hóa đơn/doanh thu, chọn nhóm hàng hóa - ngành nghề và quy tắc VAT/CIT.
2. Engine tạo dòng doanh thu vào S1, S2a, S2b hoặc S3a tùy hồ sơ.
3. Engine tạo công nợ phải thu S4a nếu chưa thu tiền.
4. Khi thu tiền, lập Phiếu thu 01-TT và cập nhật S2d.
5. Nếu GTGT khấu trừ, cập nhật S3b từ thông tin GTGT đầu ra.

Ví dụ mua hàng nhập kho chưa thanh toán:

1. Lập chứng từ mua hàng, đính kèm hóa đơn/bảng kê nếu có.
2. Sinh Phiếu nhập kho 01-VT và `inventory_movement` nhập kho.
3. Cập nhật tồn kho S2c, công nợ phải trả S4a và chi phí/tax input theo hồ sơ thuế.
4. Khi chi tiền, lập Phiếu chi 02-TT, cập nhật S2d và thanh toán công nợ.

Sau khi ghi sổ, không xóa cứng chứng từ. Chỉ cho phép hủy hoặc tạo chứng từ điều chỉnh, luôn lưu ai làm, thời điểm, lý do, dữ liệu trước/sau và quan hệ với chứng từ gốc.

## 5. Phân hệ bắt buộc

### 5.1. Onboarding và quản trị workspace

- Đăng ký, đăng nhập, quên mật khẩu, lời mời thành viên.
- Tạo workspace hoặc tham gia workspace bằng lời mời.
- Wizard: pháp nhân, mã số thuế, địa chỉ, năm tài chính, ngày bắt đầu áp dụng, phương pháp GTGT/TNDN, ngân hàng, kho và số dư đầu kỳ.
- Nhập số dư chuyển đổi từ TT132: tiền mặt/ngân hàng, phải thu/phải trả, GTGT đầu vào/đầu ra, tồn kho, TSCĐ, thuế khác, vốn góp và lợi nhuận chưa phân phối.
- Cấu hình người ký: người lập biểu, phụ trách kế toán hoặc kế toán trưởng, người đại diện theo pháp luật. TT58 không bắt buộc kế toán trưởng nên không chặn doanh nghiệp nếu chỉ có “phụ trách kế toán”.

Vai trò tối thiểu:

- `OWNER`: chủ doanh nghiệp, cấu hình, phê duyệt, truy cập tất cả.
- `ACCOUNTANT`: lập/ghi sổ/chốt báo cáo theo quyền được giao.
- `CASHIER`: phiếu thu, phiếu chi, xem quỹ.
- `WAREHOUSE_KEEPER`: phiếu nhập, xuất, kiểm kho.
- `EXTERNAL_ACCOUNTANT`: kế toán dịch vụ, giới hạn theo workspace/kỳ.
- `VIEWER_AUDITOR`: chỉ đọc, tải báo cáo, xem audit log.

### 5.2. Danh mục và chứng từ

- Khách hàng, nhà cung cấp, nhân viên/đối tượng khác.
- Hàng hóa, vật liệu, dụng cụ, sản phẩm; mã, tên, đơn vị tính, nhóm doanh thu, kho mặc định.
- Nhóm doanh thu/ngành nghề gắn với `tax_rule` hiệu lực theo ngày, tách VAT và CIT.
- Tài khoản quỹ, tài khoản ngân hàng, kho, loại TSCĐ, nhóm chi phí.
- Chứng từ bán hàng, mua hàng/chi phí, thu, chi, nhập kho, xuất kho, nộp thuế, hoàn thuế, tăng/giảm TSCĐ, tăng/giảm vốn.
- Tải tệp hóa đơn điện tử, XML, PDF, ảnh chứng từ; có chống tải tệp độc hại, quyền truy cập và lịch sử tải xuống.

### 5.3. Tiền, công nợ, kho và TSCĐ

- S2d theo dõi riêng tiền mặt và từng tài khoản tiền gửi không kỳ hạn.
- S4a theo từng đối tượng và hạn thanh toán: phải thu, phải trả, tạm ứng, vay, lương, ký quỹ/ký cược.
- S2c theo từng hàng hóa và kho: nhập, xuất, tồn số lượng và giá trị.
- Giá xuất kho dùng bình quân cả kỳ:

`đơn giá xuất = (giá trị tồn đầu kỳ + giá trị nhập trong kỳ) / (số lượng tồn đầu kỳ + số lượng nhập trong kỳ)`.

- Không cho xuất âm kho nếu workspace không bật một chính sách ngoại lệ có nêu lý do và quyền phê duyệt.
- S4b theo dõi nguyên giá, ngày đưa vào sử dụng, tỷ lệ/mức khấu hao, khấu hao lũy kế, ghi giảm và lý do giảm.
- S4d theo dõi vốn góp, lợi nhuận sau thuế chưa phân phối và các quỹ.

### 5.4. Thuế

- S1: doanh thu theo nhóm có cùng tỷ lệ VAT/CIT.
- S2a: doanh thu theo nhóm VAT và VAT đầu kỳ/phát sinh/đã nộp/cuối kỳ.
- S2b: doanh thu, thu nhập và các nhóm chi phí: nguyên vật liệu/hàng hóa; nhân công; khấu hao; dịch vụ mua ngoài; lãi vay; chi khác.
- S3a: doanh thu theo nhóm TNDN và TNDN đầu kỳ/phát sinh/đã nộp/cuối kỳ.
- S3b: VAT đầu vào, VAT đầu ra, số còn được khấu trừ/hoàn, số phải nộp, đã nộp và đã hoàn.
- S4c: thuế xuất nhập khẩu, TTĐB, tài nguyên, bảo vệ môi trường, sử dụng đất và thuế khác.
- Mỗi dòng thuế phải chứa: căn cứ chứng từ, ngày, loại thuế, phương pháp, nhóm ngành, rule version, cơ sở tính, thuế suất/tỷ lệ hoặc mức tuyệt đối, kết quả tính, trạng thái xác nhận, số đã nộp/hoàn.
- Có khu vực nhập thông báo thuế của cơ quan thuế và màn hình đối chiếu số hệ thống với số đã thông báo; hiển thị chênh lệch, không tự ghi đè dữ liệu.

### 5.5. Báo cáo, khóa sổ và lưu trữ

- Sinh đầy đủ S1, S2a-d, S3a-b, S4a-d theo mẫu TT58; lọc theo kỳ, kho, ngân hàng, đối tượng và nhóm thuế khi phù hợp.
- Sinh Phiếu thu 01-TT, Phiếu chi 02-TT, Phiếu nhập kho 01-VT, Phiếu xuất kho 02-VT.
- Với `cit_method = TAXABLE_INCOME`, tạo B01-DNSN và B02-DNSN. B01 gồm tiền, phải thu, tồn kho, TSCĐ, tài sản khác, nợ phải trả, thuế phải nộp và vốn chủ. B02 gồm doanh thu/thu nhập thuần, chi phí, lợi nhuận trước thuế, chi phí TNDN, lợi nhuận sau thuế.
- Các công thức bắt buộc: B01 `Tổng tài sản = Tổng nguồn vốn`; B02 `lợi nhuận trước thuế = doanh thu và thu nhập thuần - chi phí`; `lợi nhuận sau thuế = lợi nhuận trước thuế - chi phí TNDN`.
- Nếu TNDN tính theo tỷ lệ doanh thu, vẫn cho phép lập báo cáo nội bộ nhưng đánh nhãn “Không bắt buộc nộp theo TT58, trừ khi pháp luật khác yêu cầu”.
- Dashboard hiển thị danh sách công việc: chứng từ chưa duyệt, tiền/quỹ, công nợ đến hạn, tồn kho thấp, VAT/TNDN tạm tính, chênh lệch đối soát và nhắc báo cáo năm. Với trường hợp bắt buộc, cấu hình hạn báo cáo tài chính năm là 90 ngày sau khi kết thúc năm tài chính.
- Khóa sổ theo tháng/quý/năm. Kỳ đã khóa chỉ mở lại bởi OWNER với lý do; việc mở lại phải ghi audit log và làm vô hiệu snapshot báo cáo cũ theo phiên bản, không được mất báo cáo đã phát hành.

## 6. Thiết kế cơ sở dữ liệu tối thiểu

Tạo migration có khóa ngoại, index và RLS cho các bảng sau:

```text
workspaces, organizations, workspace_members, role_assignments
fiscal_years, accounting_periods, accounting_policy_versions, signing_profiles
tax_rules, revenue_tax_groups, tax_obligations, tax_payments, tax_refunds
parties, items, warehouses, cash_accounts, bank_accounts
documents, document_lines, document_attachments, document_approvals
cash_transactions, obligations, settlements
inventory_movements, inventory_period_valuations
fixed_assets, depreciation_runs, equity_movements
register_entries, register_snapshots, opening_balance_imports
report_runs, report_files, period_closures, audit_logs
```

Yêu cầu dữ liệu:

- Mọi bản ghi dữ liệu doanh nghiệp có `workspace_id` và RLS kiểm tra thành viên thuộc workspace đó.
- `documents` có `document_type`, `document_no`, `document_date`, `accounting_date`, `status`, `reference_no`, `description`, `currency`, `total_amount`, `source_document_id`, `posted_at`, `posted_by`.
- Dùng trạng thái `DRAFT`, `PENDING_APPROVAL`, `POSTED`, `VOIDED`, `ADJUSTED`; không cho sửa số liệu kinh tế khi `POSTED`.
- `register_entries` phải lưu `register_code`, `row_type`, `row_key`, `accounting_date`, `amount`, `quantity`, `tax_rule_id`, `source_document_id`, `source_line_id`, `policy_version_id`.
- Mọi báo cáo đã phát hành lưu snapshot dữ liệu, mã phiên bản, người tạo, ngày tạo, trạng thái phê duyệt và file xuất.
- Ràng buộc duy nhất cho số chứng từ theo workspace, loại chứng từ, năm tài chính và số chứng từ.

## 7. Màn hình và trải nghiệm người dùng

Tạo layout desktop-first nhưng responsive cho tablet/mobile. Sidebar cố định gồm:

1. Tổng quan
2. Chứng từ
3. Bán hàng và doanh thu
4. Mua hàng và chi phí
5. Quỹ và ngân hàng
6. Kho
7. Công nợ
8. Thuế
9. Tài sản cố định
10. Vốn chủ sở hữu
11. Sổ kế toán
12. Báo cáo tài chính
13. Thiết lập

Mọi trang danh sách có: bộ lọc thời gian, trạng thái, tìm kiếm, phân trang, xuất dữ liệu phù hợp quyền hạn và nút tạo mới rõ ràng. Biểu mẫu nhập liệu phải có lưu nháp, kiểm tra lỗi trước khi ghi sổ, đính kèm chứng từ, xem tác động dự kiến lên sổ và xác nhận trước khi ghi sổ.

Thiết kế dashboard gọn gàng, dễ hiểu với chủ doanh nghiệp không chuyên kế toán: tiền hiện có, doanh thu/chi phí kỳ này, công nợ phải thu/phải trả, hàng tồn, thuế cần xác nhận, trạng thái khóa sổ và công việc sắp đến hạn.

## 8. API và quy tắc bảo mật

- Thiết kế API theo tài nguyên và validate toàn bộ input bằng Zod ở server.
- Mọi API phải xác định workspace từ session và kiểm tra quyền theo vai trò; không nhận `workspace_id` đáng tin từ client mà không kiểm tra quyền.
- Ghi `audit_logs` cho đăng nhập, thay đổi quyền, tạo/sửa/hủy/ghi sổ chứng từ, mở/khóa kỳ, xuất báo cáo và tải tệp chứng từ.
- Dùng soft-delete/voiding có kiểm soát, không xóa dữ liệu tài chính đã ghi sổ.
- Dùng URL tệp có thời hạn, kiểm tra loại/kích thước tệp và quét chống mã độc nếu môi trường hỗ trợ.
- Không nhúng thông tin bí mật vào source code hoặc log dữ liệu nhạy cảm.

## 9. Kiểm thử và tiêu chí nghiệm thu

Tạo dữ liệu demo cho cả P1, P2, P3, P4 và viết unit/integration tests tối thiểu cho:

1. Một hóa đơn bán hàng chỉ sinh các dòng sổ phù hợp hồ sơ thuế đã chọn.
2. Chi phí được tổng hợp đúng sáu nhóm chi phí của S2b.
3. Nhập/xuất kho tính đúng đơn giá bình quân cả kỳ và không âm kho theo chính sách mặc định.
4. VAT khấu trừ phân biệt đúng đầu vào/đầu ra, đã nộp, hoàn và số dư chuyển kỳ.
5. TNDN theo thu nhập tính thuế và theo tỷ lệ doanh thu không dùng chung công thức sai.
6. B01 luôn cân `Tài sản = Nợ phải trả + Vốn chủ sở hữu` trước khi được phát hành.
7. B02 tính đúng lợi nhuận trước/sau thuế.
8. Không thành viên workspace nào có thể đọc/sửa dữ liệu workspace khác, kể cả qua API trực tiếp.
9. Chứng từ đã POSTED không thể bị sửa/xóa; nghiệp vụ điều chỉnh có trace đầy đủ.
10. Thay đổi chính sách thuế trong năm tài chính bị từ chối; thay đổi đầu năm sau tạo phiên bản mới và chuyển số dư.
11. PDF/Excel xuất ra có đầy đủ tiêu đề biểu mẫu, năm, đơn vị tính, người lập, phụ trách kế toán/kế toán trưởng và người đại diện theo pháp luật theo cấu hình.

## 10. Thứ tự thực hiện

Thực hiện theo các milestone; sau mỗi milestone, báo cáo tệp đã tạo, migration đã chạy, test đã chạy và phần chưa hoàn thành. Không bỏ qua bước trước để chỉ làm UI.

1. Khởi tạo Next.js, cấu trúc thư mục, UI shell, xác thực và workspace.
2. Migration PostgreSQL, RLS, seed data, adapter truy cập dữ liệu và audit log.
3. Wizard onboarding, chính sách kế toán phiên bản hóa, danh mục dùng chung và nhập số dư đầu kỳ.
4. Chứng từ gốc, quy trình duyệt/ghi sổ/điều chỉnh và engine sinh register entries.
5. Bán hàng, mua hàng/chi phí, tiền, công nợ, kho, phiếu thu/chi/nhập/xuất.
6. Tax rule engine, S1/S2/S3/S4, đối soát nghĩa vụ thuế.
7. TSCĐ, vốn chủ, B01/B02, khóa sổ, PDF/Excel và dashboard.
8. Hoàn thiện test, quyền hạn, responsive UI, accessibility, README và dữ liệu demo.

## 11. Yêu cầu đầu ra của bạn

Bắt đầu bằng phần “Kế hoạch triển khai và các giả định” thật ngắn, sau đó tạo mã nguồn theo milestone 1. Không chờ thêm yêu cầu nếu không có blocker thực sự. Khi một thông tin thuế không có trong TT58 hoặc không chắc chắn, hãy tạo cấu hình có hiệu lực theo ngày, ghi chú cần xác nhận pháp lý và không tự bịa thuế suất.

Khi hoàn thành từng milestone, luôn nêu:

- chức năng hoạt động được;
- file/migration mới hoặc đã sửa;
- cách kiểm thử;
- các giới hạn pháp lý hoặc tích hợp còn lại.

Hãy bắt đầu ngay với milestone 1.

---

## Ghi chú vận hành sau khi AI Studio tạo dự án

1. Cung cấp URL/khoá Supabase qua biến môi trường, không dán vào prompt hoặc mã nguồn.
2. Dùng một workspace demo riêng, không dùng dữ liệu tài chính thật trước khi RLS, backup và audit log được kiểm thử.
3. Nhờ kế toán/tư vấn thuế rà soát danh mục ngành nghề, tỷ lệ thuế và biểu mẫu xuất trước khi phát hành thương mại.
4. Các kết nối hóa đơn điện tử, ngân hàng, chữ ký số và cơ quan thuế phải được phát triển theo API/hợp đồng và tiêu chuẩn của nhà cung cấp tương ứng.
