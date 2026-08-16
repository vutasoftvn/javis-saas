# Kế Hoạch Triển Khai Chi Tiết: Phase 4
## Finance Lite & SaaS Kế Toán Doanh Nghiệp Siêu Nhỏ (Thông Tư 58/2026/TT-BTC "Sổ Nhỏ")

Tài liệu này là thiết kế kỹ thuật chi tiết để triển khai toàn diện **Domain 4: Finance Lite & SaaS Kế Toán TT58** cho COSA OS.

---

## 1. Mục Tiêu Triển Khai

1. **Finance Lite cho Founder**:
   - Theo dõi thời gian thực: Tổng tiền mặt / ngân hàng hiện có, Doanh thu kỳ này, Chi phí phát sinh, Công nợ phải thu / phải trả, Runway (số tháng hoạt động còn lại), Tốc độ đốt tiền (Burn rate), Lợi nhuận ước tính.
2. **Sổ Nhỏ - Kế Toán TT 58/2026/TT-BTC**:
   - **4 Hồ sơ thuế theo phương pháp tính (P1 - P4)**:
     - `P1`: GTGT % doanh thu + TNDN % doanh thu $\rightarrow$ Sổ bắt buộc `S1-DNSN`.
     - `P2`: GTGT % doanh thu + TNDN trên thu nhập tính thuế $\rightarrow$ Sổ `S2a, S2b, S2c, S2d-DNSN`.
     - `P3`: GTGT khấu trừ + TNDN % doanh thu $\rightarrow$ Sổ `S3a, S3b-DNSN`.
     - `P4`: GTGT khấu trừ + TNDN trên thu nhập tính thuế $\rightarrow$ Sổ `S2b, S2c, S2d, S3b-DNSN`.
     - Sổ quản trị tự chọn: `S4a` (Công nợ), `S4b` (TSCĐ), `S4c` (Thuế khác), `S4d` (Vốn chủ sở hữu).
   - **Cơ chế Document-Driven Posting Engine**:
     - Chứng từ (`accounting_documents`) là nguồn dữ liệu chuẩn duy nhất.
     - Posting engine tự động sinh các dòng sổ (`accounting_records` / `register_entries`) có liên kết truy vết chứng từ nguồn.
     - Chứng từ `POSTED` không được sửa/xóa cứng; chỉ cho phép `VOIDED` kèm bút toán đảo ngược.
   - **Kho & Tính giá xuất kho bình quân kỳ**:
     $$\text{Đơn giá xuất} = \frac{\text{Giá trị tồn đầu} + \text{Giá trị nhập}}{\text{Số lượng tồn đầu} + \text{Số lượng nhập}}$$
     Chặn xuất âm kho theo mặc định.
   - **Báo cáo Tài chính B01 & B02**:
     - `B01-DNSN` (Tình hình tài chính): Kiểm tra cân đối $\text{Tổng tài sản} = \text{Tổng nguồn vốn}$.
     - `B02-DNSN` (Kết quả kinh doanh): Doanh thu, chi phí, thuế, lợi nhuận sau thuế.

---

## 2. Kiến Trúc & API Endpoints

### 2.1 Backend Routers (`/api/v1/workspaces/{workspace_id}/finance/tt58`)
- `GET /metrics/founder-lite`: Tổng hợp số dư, runway, burn rate, công nợ.
- `POST /documents`: Tạo chứng từ kế toán mới (`DRAFT`).
- `POST /documents/{id}/post`: Ghi sổ chứng từ tự động sang các mẫu sổ tương ứng theo Profile thuế.
- `POST /documents/{id}/void`: Hủy chứng từ và ghi bút toán đảo.
- `GET /registers/{code}`: Đọc dữ liệu sổ kế toán `S1`, `S2a-d`, `S3a-b`, `S4a-d`.
- `GET /inventory/valuation`: Tính toán giá xuất kho bình quân và lượng tồn kho.
- `GET /reports/b01`: Bảng tình hình tài chính `B01-DNSN` (kiểm tra cân đối).
- `GET /reports/b02`: Báo cáo kết quả hoạt động kinh doanh `B02-DNSN`.

---

## 3. Kế Hoạch Kiểm Thử (Verification Plan)

1. **Pytest Backend (`test_p4_finance_tt58.py`)**:
   - `test_finance_cross_tenant_forbidden`
   - `test_document_creation_and_posting_engine`
   - `test_voided_document_creates_reversal_entry`
   - `test_inventory_average_cost_valuation`
   - `test_b01_balance_sheet_equality`
   - `test_founder_finance_lite_metrics`
2. **Frontend Analysis**:
   - `flutter analyze lib/` đạt 0 issues.
