---
name: finance-rd-accounting
description: Quản trị tài chính và định tuyến hạch toán chi phí R&D phần mềm theo chuẩn IAS 38 và US GAAP ASC 350-40, phân định chi phí hoạt động (OpEx) và ứng viên vốn hóa (CapEx).
---

# Kế Toán Chi Phí R&D Phần Mềm & Định Tuyến Vốn Hóa (SaaS R&D Accounting & CapEx/OpEx Router)

## 1. Mục Tiêu (Objective)
Cung cấp khuôn khổ quản trị tài chính và định tuyến hạch toán chi phí nghiên cứu và phát triển (R&D) cho doanh nghiệp phần mềm SaaS. Kỹ năng này rà soát các hạng mục chi tiêu kỹ thuật đối chiếu với **6 tiêu chí vốn hóa tài sản vô hình theo chuẩn mực quốc tế IAS 38 và chuẩn US GAAP ASC 350-40 (Internal-Use Software)**. 

> [!IMPORTANT]
> **Quy Tắc Quản Trị Bất Khả Xâm Phạm:**
> Kỹ năng này là **CÔNG CỤ HỖ TRỢ RA QUYẾT ĐỊNH (Decision Support Only)**. Hệ thống **TUYỆT ĐỐI KHÔNG TỰ Ý GHI SỔ KẾ TOÁN (No Auto-Booking)**. Mọi kết quả phân tích bắt buộc phải được đóng gói thành hồ sơ trình duyệt chuyển giao đích danh cho **`R&D Finance Controller`** và Kiểm toán viên độc lập ký duyệt.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi lập ngân sách phát triển sản phẩm công nghệ trong các giai đoạn `P2_SOLUTION_VALIDATION`, `P3_BUILD_VALIDATE`.
  - Khi chuẩn bị hồ sơ báo cáo tài chính định kỳ, hồ sơ kiểm toán năm hoặc rà soát tính khả thi vốn hóa chi phí lập trình.
  - Khi phân tích chỉ số tài chính R&D burn rate và hiệu quả hoàn vốn đầu tư R&D (R&D ROI / rNPV).
- **Khi nào KHÔNG dùng**:
  - Khi quyết toán thuế doanh nghiệp hoặc định giá cổ phần công ty (dùng `finance.cfo-review`).
  - Khi mua sắm thiết bị văn phòng thông thường hoặc đàm phán hợp đồng nhà cung cấp (dùng `finance.procurement-optimizer`).
  - Khi theo dõi dòng tiền tổng thể toàn công ty (dùng `finance.runway-forecast`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Danh mục chi phí phát triển phần mềm (bảng lương đội ngũ kỹ sư, chi phí hạ tầng cloud dev, phí bản quyền công cụ dev).
- Hồ sơ kỹ thuật chứng minh tính khả thi (PoC / Working Model đã hoàn thành) đối với các dự án đề xuất vốn hóa.
- Định danh nhân sự tài chính chịu trách nhiệm (`finance_controller_name`).

## 4. Các Bước Tất Định (Deterministic Steps)

```
┌────────────────────────────────────────────────────────┐
│ 1. PHÂN LOẠI GIAI ĐOẠN DỰ ÁN (STAGE GATE DISCIPLINE)   │
│    • Sơ khởi / Ý tưởng (Preliminary) -> 100% OpEx      │
│    • Phát triển ứng dụng (Development) -> Xét vốn hóa  │
│    • Vận hành & Bảo trì (Post-implementation) -> OpEx  │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. KIỂM ĐỊNH 6 TIÊU CHÍ IAS 38 / ASC 350-40            │
│    1. Feasibility      2. Intention     3. Usability   │
│    4. Economic Benefit 5. Resources     6. Measurement │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. ĐỊNH TUYẾN KẾ TOÁN (RDCapexOpexRouter)              │
│    • EXPENSE: Hạch toán chi phí kỳ phát sinh           │
│    • CAPITALIZE-CANDIDATE: Đủ 6/6 điều kiện            │
│    • FINANCE-OWNER-REVIEW: Hồ sơ chưa đủ căn cứ        │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. BÀN GIAO ĐÍCH DANH CHO R&D FINANCE CONTROLLER       │
└────────────────────────────────────────────────────────┘
```

1. **Phân Loại Giai Đoạn Dự Án**:
   - *Giai đoạn nghiên cứu / sơ khởi (Preliminary Project Stage)*: Khảo sát thị trường, đánh giá giải pháp công nghệ, thử nghiệm thuật toán chưa thành PoC $\rightarrow$ **BẮT BUỘC HẠCH TOÁN CHI PHÍ (OpEx / Expense as incurred)** theo IAS 38.54 và ASC 350-40-25-1.
   - *Giai đoạn phát triển ứng dụng (Application Development Stage)*: Thiết kế chi tiết, lập trình mã nguồn, cấu hình hạ tầng sản xuất, kiểm thử chấp nhận $\rightarrow$ Được xem xét vốn hóa nếu thỏa mãn đủ 6 tiêu chí.
   - *Giai đoạn sau triển khai (Post-Implementation / Operation Stage)*: Đào tạo người dùng, bảo trì sửa lỗi, nâng cấp nhỏ $\rightarrow$ **HẠCH TOÁN CHI PHÍ (OpEx)**.
2. **Kiểm Định 6 Tiêu Chí Vốn Hóa IAS 38**:
   - Sử dụng `RDCapexOpexRouter` (`packages/agent/research/analyzers/rd_capex_opex_router.py`).
   - Rà soát tính đầy đủ của 6 bằng chứng:
     - `technical_feasibility`: Có bản mẫu working model hoặc kết quả PoC thành công.
     - `intention_to_complete`: Nghị quyết hội đồng quản trị hoặc roadmap sản phẩm đã duyệt.
     - `ability_to_use_or_sell`: Kiến trúc phần mềm sẵn sàng triển khai SaaS hoặc phục vụ nội bộ.
     - `probable_future_benefit`: Mô hình kinh doanh chứng minh doanh thu hoặc tiết kiệm chi phí.
     - `adequate_resources`: Đã phân bổ đủ ngân sách và nhân sự dev để hoàn thiện.
     - `reliable_measurement`: Hệ thống Jira/Timesheet bóc tách chính xác số giờ dev cho tính năng.
3. **Tổng Hợp Báo Cáo Định Tuyến Ngân Sách**:
   - Tính toán tổng ngân sách, tỷ lệ CapEx / OpEx.
   - Gắn nhãn phân loại: `CAPITALIZE-CANDIDATE`, `EXPENSE`, hoặc `FINANCE-OWNER-REVIEW`.
4. **Bàn Giao Hồ Sơ Phê Duyệt**:
   - Đóng gói toàn bộ tài liệu dẫn chứng, chuyển giao hồ sơ cho `R&D Finance Controller` để tiến hành làm việc với kiểm toán.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- Kỹ năng phân tích thuần túy, dữ liệu đọc từ ngân sách dự án. Không gọi API bên thứ ba.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- **Tài liệu chứng minh cho từng tiêu chí**: Mỗi tiêu chí trong 6 điều kiện vốn hóa phải có liên kết đến tài liệu kỹ thuật hoặc văn bản phê duyệt cụ thể.
- **Cấm tự ý hạch toán**: Tuyệt đối không được xuất ra các câu lệnh ghi sổ kép nợ/có (journal entries) mà không có chữ ký của nhân sự tài chính phụ trách.

## 7. Safe Fallback
- Khi dự án đang trong giai đoạn phát triển nhưng dữ liệu chấm công (Timesheet) chưa bóc tách tin cậy:
  - Agent tự động chuyển hạng mục sang `FINANCE-OWNER-REVIEW` kèm khuyến nghị: *"Chưa đủ điều kiện tin cậy để đo lường chi phí (Criteria 6) - Hạch toán thận trọng vào OpEx cho đến khi hoàn thiện timesheet"*.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Định Tuyến Chi Phí R&D Phần Mềm (R&D Accounting Brief)

## 1. Tóm Tắt Phân Bổ Ngân Sách (Executive Summary)
- **Chuẩn mực áp dụng**: [IFRS (IAS 38) / US GAAP (ASC 350-40)]
- **Tổng ngân sách R&D kỳ này**: $XXX,XXX.00
  - **Chi phí hoạt động (OpEx)**: $XX,XXX.00 (XX.X%)
  - **Ứng viên vốn hóa (CapEx)**: $XX,XXX.00 (XX.X%)
  - **Cần thẩm định thêm**: $XX,XXX.00
- **Nhân sự tài chính phụ trách**: [Tên R&D Finance Controller]

## 2. Bảng Rà Soát Chi Tiết Từng Hạng Mục
| ID | Hạng mục công việc / Tính năng | Giai đoạn | Chi phí ($) | Tiêu chí đạt (6/6) | Định tuyến kế toán | Người duyệt đích danh |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| RD-01 | Nghiên cứu công nghệ LLM | Research | $15,000 | 0/6 | **EXPENSE (OpEx)** | R&D Finance Controller |
| RD-02 | Xây dựng Workflow Engine | Development | $45,000 | 6/6 | **CAPITALIZE-CANDIDATE** | R&D Finance Controller + Auditor |
| RD-03 | Sửa lỗi và tối ưu hiệu năng | Maintenance | $10,000 | N/A | **EXPENSE (OpEx)** | R&D Finance Controller |

## 3. Khối Căn Cứ Pháp Lý & Kế Toán
- **Hạng mục RD-01**: Tuân thủ IAS 38.54 - Chi phí nghiên cứu ban đầu không tạo ra tài sản vô hình chắc chắn.
- **Hạng mục RD-02**: Đã nghiệm thu PoC kỹ thuật (Tiêu chí 1), có kế hoạch phát hành thương mại (Tiêu chí 2, 3), dự báo ARR $150K (Tiêu chí 4), đội ngũ dev 4 người cam kết (Tiêu chí 5), timesheet Jira chi tiết (Tiêu chí 6).

---
> [!NOTE]
> **Miễn trừ trách nhiệm:** Đây là tài liệu hỗ trợ ra quyết định nội bộ. Quyết định hạch toán cuối cùng phụ thuộc vào phê duyệt của Giám đốc Tài chính và Kiểm toán viên độc lập.
```

## 9. Xử Lý Lỗi & Phòng Vệ An Toàn (Security & Edge Cases)
- **Rủi ro vốn hóa khống (Aggressive Capitalization Risk)**: Doanh nghiệp công nghệ thường có xu hướng vốn hóa quá mức để làm đẹp chỉ số EBITDA. Agent bắt buộc phải duy trì lập trường kiểm toán thận trọng, tự động từ chối vốn hóa nếu thiếu bằng chứng về tính khả thi kỹ thuật.
- **Phân định ranh giới sửa lỗi vs tính năng mới**: Các công việc refactor hoặc sửa bug nhỏ không làm gia tăng giá trị tài sản phải được hạch toán vào OpEx.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: research-ops/skills/research-finance
  upstream_version: 2.9.0
  license: MIT
adaptation:
  kept:
    - 6 tiêu chí vốn hóa phát triển theo chuẩn IAS 38 và ASC 350-40
    - Phân chia 3 giai đoạn sơ khởi / phát triển / bảo trì
    - Cơ chế định tuyến chuyển giao đích danh cho Finance Controller
    - Khối miễn trừ trách nhiệm pháp lý và cấm auto-booking
  changed:
    - Bản địa hóa sang tiếng Việt và cấu trúc 10 mục chuẩn COSA
    - Đóng gói thành skillpack finance.rd-accounting
    - Tích hợp RDCapexOpexRouter thuần Python stdlib
  added:
    - Rào chắn kiểm toán thận trọng chống vốn hóa khống
    - Tích hợp gate G2-G5 trong vòng đời dự án COSA
  excluded:
    - Các script mô hình hóa tỷ lệ F&A gián tiếp của trường đại học
```
