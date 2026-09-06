# TT58/2026 — Mapping sổ/báo cáo (F5)

**Trạng thái: CHƯA XÁC MINH.** Nội dung dưới đây là bản rút gọn dùng để dựng
engine và fixture test — KHÔNG được đối chiếu với toàn văn Thông tư 58/2024
hay phụ lục chính thức. Founder phải xác nhận qua
`POST /finance/accounting-mapping/TT58_2026/v1/confirm` chỉ sau khi đã tự
đối chiếu nguồn chính thức tại
[Bộ Tài chính](https://www.mof.gov.vn/tin-tuc-tai-chinh/tin-chinh-sach-tai-chinh/quy-dinh-moi-ve-che-do-ke-toan-cho-doanh-nghiep-sieu-nho).
Trước khi confirm, mọi report dùng mapping_version này ở trạng thái
`INCOMPLETE` với issue `mapping_not_confirmed_by_founder` — đây là hành vi
đúng theo thiết kế, không phải lỗi.

## Nguồn nội dung

Nội dung mapping thật nằm trong
`services/company/finance-legal/services/accounting-mapping.ts`
(`TT58_2026_MAPPING`). File này là tài liệu tham chiếu, không phải nguồn dữ
liệu — sửa mapping phải sửa file TS, không sửa file markdown này.

## Dòng báo cáo hiện có (v1, rút gọn cho fixture)

| Report | Line code | Ý nghĩa | Bucket | Dấu |
|---|---|---|---|---|
| B01 | TS | Tiền và tương đương tiền | cash | + |
| B01 | PHAI_THU | Phải thu khách hàng | receivable | + |
| B01 | NO_VAY | Nợ vay | loan | + |
| B01 | VON_GOP | Vốn góp chủ sở hữu | capital | + |
| B02 | LOI_NHUAN | Lợi nhuận kỳ | profit | + |

`lineCode = "TS"` là mã lịch sử (giữ nguyên vì đã dùng trong test/snapshot đã
sinh), nhưng dòng này CHỈ cộng bucket `cash` — không phải tổng tài sản. Tổng
tài sản trong v1 là `TS + PHAI_THU`, do bên tiêu thụ tự cộng; mapping chưa có
dòng tổng riêng. Trước đây dòng này bị đặt tên "Tổng tài sản (…)" nên người
đọc thấy một con số chỉ-là-tiền dưới nhãn tổng tài sản — đã sửa nhãn, không
đổi `lineCode`/`officialCode`/`bucket`.

## Chưa có trong v1

Dòng cho `advance`, `internal_transfer`, thuế, tài sản cố định, B03 (lưu
chuyển tiền tệ), F01 (thuyết minh) — thêm khi có yêu cầu thật và nguồn xác
minh được, không tự suy diễn trước.
