# COSA — Seed Catalog “Quyền lợi hiện hành” theo tài liệu Founders’ Meetup #1

**Tên file:** `COSA_Current_Benefits_Seed_Catalog_From_Founders_Meetup.md`  
**Mục đích:** tạo **bộ dữ liệu mẫu ban đầu** về quyền lợi/chương trình hỗ trợ mà tài liệu Founders’ Meetup #1 trình bày như đang có thể tiếp cận, để COSA hiển thị, matching với Project và cho Founder kiểm chứng lại.  
**Phạm vi:** tài liệu bổ sung cho `COSA_Policy_Funding_Intelligence_Integration.md`; **không thay thế** tài liệu kiến trúc đang triển khai.  
**Nguyên tắc:** dữ liệu dưới đây được lấy theo nội dung tài liệu đính kèm, **chưa được COSA xác minh độc lập với văn bản/cổng chính thức**.

---

# 1. Mục tiêu tài liệu

Tài liệu này chỉ giải quyết một việc:

> **Seed — tạo dữ liệu mẫu “quyền lợi hiện hành” cho COSA dựa trên tài liệu Founders’ Meetup #1.**

Founder sẽ kiểm chứng thủ công trong giai đoạn đầu.

Ở giai đoạn sau, COSA dùng AI để:

1. kiểm tra nguồn chính thức;
2. phân tích văn bản;
3. phát hiện thay đổi;
4. cập nhật điều kiện/chỉ tiêu/thời hạn;
5. cảnh báo Founder;
6. lưu lịch sử thay đổi và bằng chứng nguồn.

Không sửa lại kiến trúc Policy/Funding Intelligence đã được mô tả trong tài liệu trước.

---

# 2. Quy ước trạng thái cho dữ liệu seed

Không gán ngay `ACTIVE` chỉ vì slide nói chương trình đang triển khai.

Bổ sung trạng thái tạm thời dành cho seed:

- `SOURCE_CLAIMED_CURRENT` — tài liệu nguồn trình bày như quyền lợi/chương trình hiện hành.
- `PENDING_FOUNDER_VERIFICATION` — chờ Founder kiểm chứng.
- `VERIFIED_ACTIVE` — đã được Founder/Admin xác minh đang hiệu lực/đang tiếp nhận.
- `VERIFIED_ENACTED` — đã xác minh có căn cứ pháp lý nhưng chưa chắc đang mở đợt.
- `VERIFIED_CLOSED` — đã xác minh đợt hiện tại đã đóng.
- `REJECTED_SOURCE_DATA` — Founder xác minh thấy thông tin nguồn không đúng/không còn đúng.
- `DRAFT_WATCHLIST` — dự thảo, chỉ theo dõi; không tính là quyền lợi hiện hành.

## Quy tắc khi import

Tất cả record từ tài liệu này mặc định:

```yaml
source_type: PRESENTATION
source_title: "Next Wave of Startups 2026 — Founders’ Meetup #1"
verification_status: PENDING_FOUNDER_VERIFICATION
publish_to_matching: true
matching_mode: "soft"
legal_claim_verified: false
```

`publish_to_matching: true` cho phép COSA dùng làm **mẫu gợi ý**, nhưng UI phải hiển thị rõ:

> **Chưa xác minh chính thức — Founder cần kiểm chứng trước khi sử dụng.**

---

# 3. Nhóm quyền lợi/chương trình cần seed

Đề xuất chia bộ dữ liệu ban đầu thành 6 nhóm:

1. **Tài trợ & quỹ**
2. **Tín dụng & hỗ trợ lãi suất**
3. **Voucher & hỗ trợ phi tài chính**
4. **Thuế, đất đai, sandbox & đặt hàng**
5. **Chương trình địa phương — TP.HCM**
6. **Nguồn lực tư nhân / cloud credit**

---

# 4. Seed 01 — NAFOSTED: tài trợ nghiên cứu ứng dụng

## Tên hiển thị

**NAFOSTED — Quỹ Phát triển Khoa học và Công nghệ Quốc gia**

## Loại

`Grant — Tài trợ`

## Tài liệu nguồn mô tả

- tài trợ nghiên cứu ứng dụng;
- mức trần được slide nêu: **8 tỷ đồng/nhiệm vụ**;
- khuyến khích **≥20% vốn đối ứng ngoài ngân sách**;
- doanh nghiệp được tài liệu trình bày là đối tượng có thể nhận tài trợ, không chỉ viện/trường;
- quy trình nộp hồ sơ nghiên cứu ứng dụng được tài liệu cho biết đã số hóa qua hệ thống STM.

## Seed record

```yaml
id: seed-nafosted-applied-rd
name: "NAFOSTED — Tài trợ nghiên cứu ứng dụng"
program_type: GRANT
provider: "NAFOSTED"
company_types:
  - STARTUP
  - SCIENCE_TECH_ENTERPRISE
  - SME_INNOVATION
project_stages:
  - POC
  - PROTOTYPE
  - MVP
  - RND
funding_max_claimed_vnd: 8000000000
matching_fund_claimed: "Khuyến khích >=20% vốn đối ứng ngoài ngân sách"
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
source_claim: "Theo slide Founders’ Meetup #1"
```

## Founder cần kiểm chứng

- mức trần 8 tỷ hiện áp dụng cho loại nhiệm vụ nào;
- doanh nghiệp nào đủ tư cách đứng tên;
- yêu cầu vốn đối ứng bắt buộc hay chỉ khuyến khích;
- đợt nhận hồ sơ hiện tại;
- biểu mẫu và hệ thống nộp.

---

# 5. Seed 02 — NATIF: tài trợ đổi mới công nghệ/đổi mới sáng tạo

## Tên hiển thị

**NATIF — Tài trợ & đặt hàng nhiệm vụ đổi mới sáng tạo**

`NATIF (National Technology Innovation Fund — Quỹ Đổi mới công nghệ Quốc gia)`

## Loại

- `Grant — Tài trợ`
- `Commissioned Task — Nhiệm vụ đặt hàng`

## Nội dung tài liệu nguồn

Tài liệu trình bày 5 nhóm nội dung có thể được tài trợ/đặt hàng:

1. đổi mới công nghệ;
2. đổi mới sáng tạo;
3. phát triển tài sản trí tuệ;
4. nâng cao năng suất, chất lượng;
5. hỗ trợ khởi nghiệp sáng tạo.

Tài liệu cũng trình bày:

- 2 hình thức: doanh nghiệp chủ động đề xuất hoặc Nhà nước đặt hàng;
- thời hạn hợp đồng có thể **≤60 tháng**;
- cơ chế khoán chi đến sản phẩm cuối cùng;
- doanh nghiệp cần pháp nhân, năng lực triển khai và phương án tài chính đối ứng có minh chứng.

## Seed record

```yaml
id: seed-natif-innovation-grant
name: "NATIF — Tài trợ & đặt hàng nhiệm vụ đổi mới sáng tạo"
program_type:
  - GRANT
  - COMMISSIONED_TASK
provider: "NATIF"
eligible_content:
  - "Đổi mới công nghệ"
  - "Đổi mới sáng tạo"
  - "Phát triển tài sản trí tuệ"
  - "Nâng cao năng suất, chất lượng"
  - "Hỗ trợ khởi nghiệp sáng tạo"
max_contract_months_claimed: 60
requires_legal_entity: true
requires_execution_capability: true
requires_financial_plan: true
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

## Founder cần kiểm chứng

- loại nhiệm vụ đang mở;
- định mức hỗ trợ;
- đối tượng;
- vốn đối ứng;
- hồ sơ;
- thời gian xét;
- căn cứ pháp lý chính xác.

---

# 6. Seed 03 — NATIF: hỗ trợ lãi suất vay đổi mới công nghệ

## Tên hiển thị

**NATIF — Hỗ trợ lãi suất vay đổi mới công nghệ**

## Loại

`Interest Subsidy — Hỗ trợ lãi suất`

## Tài liệu nguồn mô tả

Tài liệu trình bày:

- NATIF chi trả **50% lãi suất vay thực tế**;
- mức trần hỗ trợ được slide nêu là **6%/năm**;
- thời hạn hỗ trợ tối đa **5 năm / 60 tháng**;
- thời hạn xét duyệt hồ sơ được slide nêu **≤30 ngày**;
- khoản vay còn thời hạn **≥12 tháng**;
- ngân hàng kiểm soát giải ngân và xác nhận sử dụng vốn;
- một slide khác ghi cơ chế đang thí điểm với 20 doanh nghiệp đến hết 9/2026.

## Ví dụ trong tài liệu

Vay **10 tỷ đồng**, lãi suất **6%/năm** → tài liệu minh họa NATIF hỗ trợ 3%/năm → tiết kiệm khoảng **300 triệu đồng/năm**, tối đa khoảng **1,5 tỷ đồng/5 năm**.

## Seed record

```yaml
id: seed-natif-interest-support
name: "NATIF — Hỗ trợ lãi suất vay đổi mới công nghệ"
program_type: INTEREST_SUBSIDY
provider: "NATIF"
support_ratio_claimed: 0.50
support_rate_cap_claimed: "6%/năm"
support_duration_max_months_claimed: 60
review_time_claimed: "<=30 ngày"
minimum_remaining_loan_term_claimed: ">=12 tháng"
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

## Cảnh báo UI bắt buộc

> **Các tỷ lệ và thời hạn trên đang lấy theo tài liệu hội thảo, chưa được COSA xác minh độc lập.**

---

# 7. Seed 04 — NATIF Voucher: phiếu hỗ trợ tài chính

## Tên hiển thị

**NATIF Voucher — Phiếu hỗ trợ tài chính cho sản phẩm/dịch vụ mới**

`Voucher — Phiếu hỗ trợ/trợ giá`

## Mục tiêu theo tài liệu

Thúc đẩy thương mại hóa sản phẩm/dịch vụ mới bằng cách hỗ trợ người dùng/khách hàng trải nghiệm sản phẩm của startup/doanh nghiệp KH&CN.

## Tài liệu nguồn trình bày

- tối đa **3 loại sản phẩm/dịch vụ mới** cho mỗi đối tượng cung cấp trong 1 năm tài chính;
- voucher có hiệu lực **≤12 tháng**;
- phát hành số hóa trên nền tảng của Quỹ;
- quy trình:
  1. NATIF phát hành voucher;
  2. khách hàng sử dụng voucher để mua giảm giá;
  3. doanh nghiệp gửi hồ sơ thanh toán;
  4. NATIF hoàn trả phần giảm trừ cho doanh nghiệp.

## Seed record

```yaml
id: seed-natif-innovation-voucher
name: "NATIF Voucher — Phiếu hỗ trợ tài chính"
program_type: VOUCHER
provider: "NATIF"
max_products_services_per_year_claimed: 3
voucher_validity_max_months_claimed: 12
market_validation_use_case: true
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

## Liên kết với COSA

```text
Voucher
→ CRM Campaign
→ Lead
→ Customer
→ Order
→ Evidence
→ Reimbursement Claim
```

---

# 8. Seed 05 — Voucher/phiếu hỗ trợ cho thử nghiệm, kiểm định, tư vấn, thị trường

Tài liệu còn mô tả `Voucher ĐMST — Phiếu hỗ trợ đổi mới sáng tạo` ở nghĩa rộng:

- thử nghiệm;
- kiểm định;
- tư vấn;
- tiếp cận thị trường.

Để tránh nhập nhằng với NATIF Voucher cho khách hàng mua giảm giá, seed thành một record khác:

```yaml
id: seed-innovation-service-voucher
name: "Phiếu hỗ trợ đổi mới sáng tạo — Dịch vụ thử nghiệm/kiểm định/tư vấn"
program_type: SERVICE_VOUCHER
eligible_costs_claimed:
  - "Thử nghiệm"
  - "Kiểm định"
  - "Tư vấn"
  - "Tiếp cận thị trường"
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

UI phải ghi:

> **Cần xác minh cơ quan phát hành, đối tượng và định mức trước khi sử dụng.**

---

# 9. Seed 06 — Hỗ trợ chuyên gia & tư vấn

## Tên hiển thị

**Hỗ trợ chuyên gia & tư vấn**

## Nội dung nguồn

Tài liệu mô tả chi phí chuyên gia:

- công nghệ;
- pháp lý;
- tài chính;
- quản trị;
- kết nối đầu tư.

Ở phần TP.HCM, tài liệu đưa ví dụ mức hỗ trợ chuyên gia tối đa **100 triệu đồng/dự án** theo chương trình được nêu trong slide.

## Seed

```yaml
id: seed-expert-consulting-support
name: "Hỗ trợ chuyên gia & tư vấn"
program_type: EXPERT_SUPPORT
eligible_services:
  - TECHNOLOGY
  - LEGAL
  - FINANCE
  - MANAGEMENT
  - INVESTMENT_CONNECTION
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

Không nhập 100 triệu vào record quốc gia chung; mức này chỉ gắn vào record TP.HCM ở phần sau.

---

# 10. Seed 07 — Hỗ trợ thử nghiệm & sản xuất thử

## Tên hiển thị

**Hỗ trợ thử nghiệm và sản xuất thử**

## Nội dung nguồn

Tài liệu mô tả hỗ trợ chi phí:

- cơ sở vật chất;
- vật tư;
- linh kiện;
- phát triển sản phẩm mẫu;
- chuẩn bị thương mại hóa.

## Seed

```yaml
id: seed-pilot-production-support
name: "Hỗ trợ thử nghiệm & sản xuất thử"
program_type: PILOT_PRODUCTION_SUPPORT
eligible_costs_claimed:
  - "Cơ sở vật chất"
  - "Vật tư"
  - "Linh kiện"
  - "Sản phẩm mẫu"
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

---

# 11. Seed 08 — Hỗ trợ chuyển giao công nghệ

## Tên hiển thị

**Hỗ trợ chuyển giao công nghệ**

## Nội dung nguồn

Tài liệu trình bày các hình thức:

- mua bản quyền công nghệ;
- giải mã;
- làm chủ công nghệ;
- kết nối bên chuyển giao và bên nhận;
- giao dịch qua sàn giao dịch công nghệ.

## Seed

```yaml
id: seed-technology-transfer-support
name: "Hỗ trợ chuyển giao công nghệ"
program_type: TECHNOLOGY_TRANSFER_SUPPORT
eligible_activities_claimed:
  - "Mua bản quyền công nghệ"
  - "Giải mã công nghệ"
  - "Làm chủ công nghệ"
  - "Kết nối chuyển giao"
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

---

# 12. Seed 09 — Hạ tầng dùng chung

## Tên hiển thị

**Hạ tầng dùng chung cho đổi mới sáng tạo**

## Tài liệu nguồn mô tả

- phòng LAB;
- cơ sở ươm tạo;
- khu công nghệ cao;
- không gian làm việc chung;
- maker space;
- thử nghiệm thị trường;
- hạ tầng trung tâm đổi mới sáng tạo.

## Seed

```yaml
id: seed-shared-innovation-infrastructure
name: "Hạ tầng dùng chung cho đổi mới sáng tạo"
program_type: INFRASTRUCTURE_SUPPORT
support_mode: NON_CASH
resource_types:
  - LAB
  - INCUBATOR
  - HIGH_TECH_PARK
  - COWORKING
  - MAKER_SPACE
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

---

# 13. Seed 10 — Đào tạo nguồn nhân lực

## Tên hiển thị

**Hỗ trợ đào tạo nguồn nhân lực**

## Nguồn mô tả

Tài liệu nêu:

- khóa đào tạo;
- chứng chỉ công nghệ;
- đào tạo trong/ngoài nước;
- ưu tiên nhân lực chủ chốt của dự án.

## Seed

```yaml
id: seed-workforce-training
name: "Hỗ trợ đào tạo nguồn nhân lực"
program_type: TRAINING_SUPPORT
support_mode: NON_CASH_OR_REIMBURSEMENT
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

---

# 14. Seed 11 — Ưu đãi thuế cho doanh nghiệp KH&CN/công nghệ

## Tên hiển thị

**Ưu đãi thuế cho doanh nghiệp KH&CN/công nghệ**

## Tài liệu nguồn mô tả

- miễn/giảm thuế thu nhập doanh nghiệp theo giai đoạn hoạt động.

Tài liệu không nêu đủ mức, thời gian và điều kiện cụ thể trong phần slide được sử dụng.

## Seed

```yaml
id: seed-science-tech-tax-incentive
name: "Ưu đãi thuế cho doanh nghiệp KH&CN/công nghệ"
program_type: TAX_INCENTIVE
company_types:
  - SCIENCE_TECH_ENTERPRISE
  - TECHNOLOGY_ENTERPRISE
amount_claimed: null
duration_claimed: null
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

## UI

Không hiển thị số % hoặc số năm miễn giảm nếu Founder chưa xác minh.

---

# 15. Seed 12 — Ưu đãi đất/mặt bằng

## Tên hiển thị

**Ưu đãi tiền thuê đất & mặt bằng công nghệ**

## Tài liệu nguồn mô tả

- ưu đãi tiền thuê đất;
- ưu đãi mặt bằng;
- áp dụng tại khu công nghệ cao/khu CNTT tập trung.

```yaml
id: seed-tech-land-incentive
name: "Ưu đãi đất & mặt bằng công nghệ"
program_type: LAND_INCENTIVE
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

---

# 16. Seed 13 — Ưu tiên mua sắm công/đặt hàng sản phẩm

## Tên hiển thị

**Mua sắm công & đặt hàng sản phẩm đổi mới**

## Nội dung nguồn

Tài liệu trình bày:

- ưu tiên mua sắm công;
- đặt hàng;
- giao trực tiếp;
- khoán chi theo kết quả đầu ra;
- khuyến khích sản phẩm “Make in Viet Nam” đáp ứng yêu cầu kỹ thuật.

```yaml
id: seed-public-procurement-innovation
name: "Mua sắm công & đặt hàng sản phẩm đổi mới"
program_type:
  - PUBLIC_PROCUREMENT
  - COMMISSIONED_TASK
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

---

# 17. Seed 14 — Sandbox: thử nghiệm có kiểm soát

## Tên hiển thị

**Sandbox — Cơ chế thử nghiệm có kiểm soát**

## Mô tả tiếng Việt bắt buộc

`Sandbox` trong COSA phải luôn hiển thị kèm:

> **Cơ chế thử nghiệm có kiểm soát cho công nghệ, sản phẩm hoặc mô hình kinh doanh mới trong phạm vi và điều kiện được cơ quan có thẩm quyền cho phép.**

## Tài liệu nêu ví dụ

- AI;
- blockchain;
- tài sản số;
- công nghệ/mô hình mới.

```yaml
id: seed-regulatory-sandbox
name: "Sandbox — Cơ chế thử nghiệm có kiểm soát"
program_type: SANDBOX
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

Không được hiển thị:

> “AI/blockchain được phép sandbox”

nếu chưa xác minh sandbox cụ thể nào đang mở.

---

# 18. Seed 15 — Quỹ bảo lãnh tín dụng cho DNNVV

## Tên hiển thị

**Quỹ bảo lãnh tín dụng cho doanh nghiệp nhỏ và vừa**

## Nguồn mô tả

Tài liệu cho biết đây là:

- kênh bảo lãnh truyền thống tại địa phương;
- có thể áp dụng song song cho startup/spin-off đã có doanh thu.

```yaml
id: seed-sme-credit-guarantee
name: "Quỹ bảo lãnh tín dụng cho DNNVV"
program_type: CREDIT_GUARANTEE
company_types:
  - SME
  - STARTUP
  - SPIN_OFF
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

Founder cần xác minh theo địa phương cụ thể.

---

# 19. Seed 16 — Kênh vốn cổ phần & gọi vốn cộng đồng

Tài liệu trình bày:

- nền tảng gọi vốn cộng đồng;
- sàn giao dịch vốn cho khởi nghiệp sáng tạo;
- được khuyến khích phát triển đa dạng.

Không được seed thành “quyền được gọi vốn”.

Chỉ tạo **resource category — nhóm nguồn lực**:

```yaml
id: seed-equity-crowdfunding-channel
name: "Kênh vốn cổ phần & gọi vốn cộng đồng"
program_type: CAPITAL_CHANNEL
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

COSA phải yêu cầu Founder xác minh nền tảng/kênh cụ thể trước khi dùng.

---

# 20. Seed 17 — TP.HCM: NQ 20/2023 — tiền ươm tạo, ươm tạo, tăng tốc

## Tên hiển thị

**TP.HCM — Gói hỗ trợ khởi nghiệp sáng tạo theo giai đoạn**

## Tài liệu nguồn trình bày

### Tiền ươm tạo

- **40 triệu đồng**
- thời gian **≤6 tháng**

### Ươm tạo

- **80 triệu đồng**
- thời gian **≤12 tháng**

### Tăng tốc

- **400 triệu đồng**
- thời gian **≤12 tháng**
- ưu tiên có vốn đối ứng

Tài liệu ghi áp dụng cho **9 lĩnh vực ưu tiên**.

## Seed

```yaml
id: seed-hcmc-nq20-stage-support
name: "TP.HCM — Hỗ trợ tiền ươm tạo, ươm tạo, tăng tốc"
program_type: LOCAL_STARTUP_SUPPORT
geography: "TP.HCM"
packages:
  - stage: PRE_INCUBATION
    amount_claimed_vnd: 40000000
    max_months_claimed: 6
  - stage: INCUBATION
    amount_claimed_vnd: 80000000
    max_months_claimed: 12
  - stage: ACCELERATION
    amount_claimed_vnd: 400000000
    max_months_claimed: 12
    matching_fund_preferred_claimed: true
legal_basis_claimed: "NQ 20/2023/NQ-HĐND"
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

---

# 21. Seed 18 — TP.HCM: NQ 23/2026 — hỗ trợ công nghiệp công nghệ số

## Tên hiển thị

**TP.HCM — Hỗ trợ khởi nghiệp sáng tạo công nghiệp công nghệ số**

## Tài liệu nguồn trình bày

Hiệu lực được slide ghi: **01/7/2026**.

Hỗ trợ **50% chi phí**, với các mức tối đa tài liệu nêu:

- đào tạo: **≤100 triệu đồng**;
- chuyên gia: **≤100 triệu đồng**;
- R&D/sản xuất thử: **≤150 triệu đồng**;
- tư vấn: **≤50 triệu đồng**;
- mua & đổi mới công nghệ: **≤400 triệu đồng/dự án**.

## Seed

```yaml
id: seed-hcmc-nq23-2026-digital-tech
name: "TP.HCM — Hỗ trợ khởi nghiệp sáng tạo công nghiệp công nghệ số"
program_type: LOCAL_DIGITAL_INNOVATION_SUPPORT
geography: "TP.HCM"
legal_basis_claimed: "NQ 23/2026/NQ-HĐND"
effective_date_claimed: "2026-07-01"
support_ratio_claimed: 0.50
caps_claimed:
  training_vnd: 100000000
  expert_vnd: 100000000
  rnd_pilot_vnd: 150000000
  consulting_vnd: 50000000
  technology_purchase_innovation_vnd: 400000000
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

Đây là record nên Founder ưu tiên kiểm chứng sớm nếu COSA hoặc Project liên quan hoạt động tại TP.HCM.

---

# 22. Seed 19 — TP.HCM: mạng lưới trung tâm đổi mới sáng tạo

Tài liệu nêu:

**QĐ 3190/QĐ-UBND — Đề án phát triển mạng lưới trung tâm đổi mới sáng tạo tầm cỡ quốc tế tại TP.HCM.**

Không coi đây là grant.

Seed dưới nhóm `ECOSYSTEM_INFRASTRUCTURE`.

```yaml
id: seed-hcmc-innovation-center-network
name: "TP.HCM — Mạng lưới trung tâm đổi mới sáng tạo"
program_type: ECOSYSTEM_INFRASTRUCTURE
geography: "TP.HCM"
legal_basis_claimed: "QĐ 3190/QĐ-UBND"
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

---

# 23. Seed 20 — TP.HCM: thu hút chuyên gia/nhà khoa học

Tài liệu nêu:

**QĐ 05/2026/QĐ-UBND** liên quan thu hút chuyên gia, nhà khoa học, người có tài năng đặc biệt của Thành phố.

Không đủ thông tin để suy luận Founder/startup được hưởng gì cụ thể.

Seed ở dạng `REFERENCE_ONLY`.

```yaml
id: seed-hcmc-talent-attraction-reference
name: "TP.HCM — Chính sách thu hút chuyên gia, nhà khoa học"
program_type: TALENT_POLICY
geography: "TP.HCM"
legal_basis_claimed: "QĐ 05/2026/QĐ-UBND"
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
publish_to_matching: false
```

---

# 24. Seed 21 — AWS Activate: Founders package

Đây là **nguồn lực tư nhân**, không phải chính sách Nhà nước.

## Tên hiển thị

**AWS Activate Founders — Cloud Credit cho startup**

`Cloud Credit — hạn mức/tín dụng sử dụng dịch vụ hạ tầng đám mây`

## Tài liệu nguồn trình bày

- gói Founders: **1.000 USD AWS credits**;
- hướng đến startup self-funded/bootstrapped, chưa thuộc Activate Provider.

```yaml
id: seed-aws-activate-founders
name: "AWS Activate Founders"
program_type: CLOUD_CREDIT
provider: "AWS"
claimed_value_usd: 1000
support_mode: NON_CASH
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

---

# 25. Seed 22 — AWS Activate: Portfolio package

## Tài liệu nguồn trình bày

- tối đa **100.000 USD AWS credits**;
- dành cho startup thuộc/được hỗ trợ bởi Activate Provider, tài liệu mô tả đến Series A.

```yaml
id: seed-aws-activate-portfolio
name: "AWS Activate Portfolio"
program_type: CLOUD_CREDIT
provider: "AWS"
claimed_value_max_usd: 100000
support_mode: NON_CASH
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

Không ghi nhận vào cash funding.

---

# 26. Seed 23 — Nguồn lực hệ sinh thái: chuyên gia, cố vấn, kết nối

Tài liệu trình bày startup còn có thể nhận:

- đào tạo/huấn luyện;
- mạng lưới chuyên gia/cố vấn;
- ngày hội đổi mới sáng tạo;
- giải thưởng;
- truyền thông;
- bản đồ công nghệ;
- sàn giao dịch công nghệ;
- hợp tác trong nước/quốc tế.

Seed thành một nhóm `ECOSYSTEM_SUPPORT`, không coi là tiền mặt.

```yaml
id: seed-ecosystem-soft-support
name: "Nguồn lực hệ sinh thái đổi mới sáng tạo"
program_type: ECOSYSTEM_SUPPORT
support_mode: NON_CASH
resources:
  - TRAINING
  - MENTOR_NETWORK
  - INNOVATION_EVENTS
  - AWARDS
  - COMMUNICATION
  - TECHNOLOGY_MAP
  - TECHNOLOGY_EXCHANGE
  - INTERNATIONAL_COOPERATION
status: SOURCE_CLAIMED_CURRENT
verification_status: PENDING_FOUNDER_VERIFICATION
```

---

# 27. Không đưa các nội dung “Dự thảo 2026–2035” vào quyền lợi hiện hành

Tài liệu có nhóm nội dung được ghi rõ:

> **DỰ THẢO — đang lấy ý kiến (7/2026)**

Bao gồm 5 chương trình quốc gia dự kiến:

1. Chương trình Khởi nghiệp sáng tạo quốc gia.
2. Chương trình Quốc gia Đổi mới công nghệ.
3. Chương trình Quốc gia Phát triển sở hữu trí tuệ.
4. Chương trình Quốc gia Nâng cao năng suất, chất lượng.
5. Chương trình Quốc gia Phát triển thị trường KH&CN.

Các thông tin như:

- hỗ trợ PoC/MVP khoảng 500 triệu/doanh nghiệp;
- tổng kinh phí khoảng 1.650 tỷ;
- các mục tiêu 2030/2035;

**không seed vào Current Benefits.**

Seed riêng:

```yaml
status: DRAFT_WATCHLIST
publish_to_matching: false
```

COSA chỉ hiển thị:

> **Dự thảo đang theo dõi — chưa dùng để kết luận Project được hưởng quyền lợi.**

---

# 28. Current Benefits — màn hình mẫu

## Menu

**Nguồn lực & Chính sách → Quyền lợi hiện hành**

## Bộ lọc

- Project.
- Địa phương.
- Giai đoạn.
- TRL.
- Loại quyền lợi.
- Nguồn.
- Đã kiểm chứng / Chưa kiểm chứng.

## Card mẫu

### NATIF — Hỗ trợ lãi suất vay đổi mới công nghệ

**Loại:** Hỗ trợ lãi suất  
**Nguồn:** Founders’ Meetup #1  
**Trạng thái:** Chưa xác minh chính thức  
**Theo tài liệu:** 50% lãi vay thực tế, trần 6%/năm, tối đa 5 năm  
**Match Score:** 84/100  
**Readiness:** 52/100

**Còn thiếu:**

- khoản vay đủ điều kiện;
- hồ sơ dự án đổi mới công nghệ;
- minh chứng sử dụng vốn;
- xác minh đợt tiếp nhận hiện tại.

Buttons:

- `Kiểm chứng`
- `Xem nguồn`
- `Phân tích Project`
- `Chuẩn bị hồ sơ`
- `Bỏ qua`

---

# 29. Founder Verification — Flow kiểm chứng thủ công giai đoạn đầu

Khi Founder chọn `Kiểm chứng`:

```text
Seed Record
→ Mở nguồn gốc
→ Founder nhập URL/văn bản chính thức
→ Đối chiếu từng claim
→ Confirm / Edit / Reject
→ Lưu bằng chứng
→ Chuyển trạng thái
```

## Founder có 4 lựa chọn

### 1. Xác minh đúng

`VERIFIED_ACTIVE` hoặc `VERIFIED_ENACTED`

### 2. Đúng một phần

Founder sửa:

- amount;
- eligibility;
- deadline;
- legal basis;
- geography;
- application link.

Lưu diff.

### 3. Không còn đúng

`VERIFIED_CLOSED` hoặc `REJECTED_SOURCE_DATA`

### 4. Chưa đủ thông tin

Giữ:

`PENDING_FOUNDER_VERIFICATION`

---

# 30. Verification Evidence — Minh chứng kiểm chứng

Mỗi lần Founder xác minh lưu:

```yaml
verification:
  verified_by: founder_user_id
  verified_at: timestamp
  source_url: "..."
  source_document_id: "..."
  official_authority: "..."
  result: VERIFIED_ACTIVE
  notes: "..."
```

Cần lưu snapshot hoặc metadata của tài liệu nguồn nếu có thể.

---

# 31. AI Verification — Kiểm chứng bằng AI ở giai đoạn sau

Sau khi nền tảng ổn định, triển khai AI verifier.

## Nhiệm vụ AI

1. tìm nguồn chính thức;
2. tải nội dung;
3. so sánh với record hiện tại;
4. xác định:
   - còn hiệu lực?
   - đang mở hồ sơ?
   - amount có đổi?
   - đối tượng có đổi?
   - deadline có đổi?
   - form có đổi?
5. tạo Change Proposal — đề xuất thay đổi;
6. giải thích sự khác biệt.

## Không nên cho AI cập nhật trực tiếp ngay từ đầu

Workflow:

```text
AI detects change
→ creates Change Proposal
→ Admin/Founder review
→ Approve
→ Update Production Record
→ Recalculate Matches
→ Notify affected Projects
```

---

# 32. AI Change Proposal — đề xuất thay đổi

Entity:

`policy_change_proposals`

Fields:

- `program_id`
- `field_name`
- `old_value`
- `new_value`
- `source_url`
- `source_excerpt`
- `confidence`
- `change_type`
- `detected_at`
- `ai_model`
- `prompt_version`
- `review_status`
- `reviewed_by`

## Change Type

- `AMOUNT_CHANGED`
- `ELIGIBILITY_CHANGED`
- `DEADLINE_CHANGED`
- `STATUS_CHANGED`
- `DOCUMENT_CHANGED`
- `LEGAL_BASIS_CHANGED`
- `APPLICATION_CHANNEL_CHANGED`
- `NEW_PROGRAM`
- `PROGRAM_CLOSED`

---

# 33. AI Update Priority

COSA không cần kiểm tra mọi record với cùng tần suất.

## Priority A — kiểm tra thường xuyên

- chương trình đang nhận hồ sơ;
- deadline;
- đợt hỗ trợ địa phương;
- voucher;
- accelerator/cloud credits;
- chính sách ảnh hưởng Project đang active.

## Priority B

- quỹ quốc gia;
- điều kiện pháp lý;
- hỗ trợ thuế/đất;
- chương trình dài hạn.

## Priority C

- reference/background;
- hệ sinh thái;
- chính sách không có Project match.

---

# 34. Matching với Project khi dữ liệu chưa xác minh

Để hỗ trợ Founder ngay trong giai đoạn seed:

```text
Verified Active
→ Match Score × 1.0

Verified Enacted
→ Match Score × 0.9

Source Claimed Current / Pending Verification
→ Match Score × 0.6

Draft Watchlist
→ Không đưa vào Current Opportunity
```

UI không hiển thị multiplier kỹ thuật.

Chỉ hiển thị:

- **Đã xác minh**
- **Chưa xác minh**
- **Dự thảo**

---

# 35. Confidence không phải Eligibility

Không dùng `AI Confidence` để thay cho điều kiện.

Ví dụ:

> AI tự tin 96% rằng slide ghi “400 triệu”.

Điều này **không có nghĩa** Founder đủ điều kiện nhận 400 triệu.

COSA phải giữ 4 lớp riêng:

1. `Source Confidence — độ tin cậy khi AI đọc nguồn`
2. `Verification Status — trạng thái kiểm chứng`
3. `Eligibility — điều kiện`
4. `Match Score — mức độ phù hợp`

---

# 36. Glossary hiển thị cho Founder

| English | Tiếng Việt |
|---|---|
| Current Benefit | Quyền lợi/chương trình hỗ trợ hiện hành |
| Seed Data | Dữ liệu mẫu ban đầu |
| Verification | Kiểm chứng |
| Source Claim | Thông tin được nguồn trình bày |
| Grant | Tài trợ |
| Interest Subsidy | Hỗ trợ lãi suất |
| Voucher | Phiếu hỗ trợ/trợ giá |
| Cloud Credit | Hạn mức sử dụng dịch vụ cloud |
| Sandbox | Thử nghiệm có kiểm soát |
| Match Score | Điểm phù hợp |
| Readiness Score | Điểm sẵn sàng |
| Eligibility | Điều kiện đủ |
| Draft Watchlist | Danh sách dự thảo cần theo dõi |
| Change Proposal | Đề xuất cập nhật thay đổi |
| Provenance | Nguồn gốc/truy xuất nguồn |

---

# 37. Data Model bổ sung tối thiểu

Không tạo bảng mới nếu schema trong tài liệu trước đã có.

Chỉ cần bổ sung nếu thiếu:

```text
policy_programs
policy_program_claims
policy_verifications
policy_change_proposals
program_rounds
provider_programs
```

## `policy_program_claims`

Dùng để lưu đúng những gì nguồn nói trước khi xác minh:

```yaml
claim_type: SUPPORT_AMOUNT
claim_value: "50%"
claim_source: source_document_id
claim_page: 70
verified: false
```

Điều này giúp tách:

> **Nguồn nói gì**

khỏi:

> **COSA đã xác minh gì**

---

# 38. Claim-based Architecture — kiến trúc theo “mệnh đề nguồn”

Đề xuất quan trọng cho giai đoạn AI sau này:

Không ghi trực tiếp:

```text
program.support_ratio = 50%
```

nếu chưa xác minh.

Thay bằng:

```text
Claim A:
source = presentation
value = 50%
verified = false

Claim B:
source = official decree
value = 50%
verified = true
```

Khi có Claim B, Production field mới được cập nhật.

Lợi ích:

- AI dễ đối chiếu;
- không làm mất lịch sử;
- phát hiện mâu thuẫn;
- biết nguồn nào đáng tin hơn;
- dễ audit.

---

# 39. Source Priority — ưu tiên nguồn

Khi AI kiểm chứng sau này, dùng thứ tự:

1. Văn bản pháp luật/văn bản chính thức.
2. Cổng cơ quan chủ trì/quỹ.
3. Cổng cơ quan nhà nước.
4. Thông báo chương trình chính thức.
5. Tài liệu hội thảo chính thức.
6. Báo chí.
7. Nguồn thứ ba.

Nguồn mức 5–7 không tự động override dữ liệu đã xác minh từ mức 1–4.

---

# 40. Ingestion — nhập nguồn mới

Flow:

```text
Source
→ Store Snapshot
→ Parse
→ Extract Claims
→ Match Existing Programs
→ Detect Differences
→ Create Change Proposal
→ Review
→ Publish
```

Nếu AI không chắc chương trình mới có phải cùng program cũ:

> tạo `POSSIBLE_DUPLICATE`, không tự merge.

---

# 41. Hologram Hub — Current Benefits cards

Chỉ hiển thị 3–5 card đáng chú ý.

Ví dụ:

### Cơ hội chưa kiểm chứng

**TP.HCM — Hỗ trợ công nghệ số**

- Theo tài liệu: hỗ trợ 50% một số nhóm chi phí.
- Match với COSA: Cao.
- Trạng thái: **Chờ kiểm chứng**.
- Action: `Kiểm chứng ngay`.

### Cơ hội đã xác minh

**AWS Activate**

- Cloud Credit.
- Project phù hợp.
- Founder đã xác minh ngày …
- Action: `Chuẩn bị đăng ký`.

### Cần theo dõi

**Chương trình quốc gia 2026–2035**

- DRAFT — Dự thảo.
- Không tính vào funding plan.
- Action: `Theo dõi`.

---

# 42. Không ghi nhận “quyền lợi” vào Finance trước khi được phê duyệt/nhận

Phân biệt:

```text
Opportunity
≠ Application
≠ Approved Award
≠ Disbursement
≠ Accounting Transaction
```

Cụ thể:

- Seed record → chỉ là cơ hội.
- Founder xác minh → cơ hội đáng tin hơn.
- Application submitted → đã nộp.
- Approved → được phê duyệt.
- Disbursed → thực nhận.
- Finance → ghi nhận theo transaction và quy tắc kế toán.

Cloud Credit:

- ghi `non_cash_support`;
- không ghi doanh thu/tiền mặt.

---

# 43. Acceptance Criteria cho tài liệu bổ sung này

Tính năng được coi là đạt khi:

- [ ] Có màn hình `Quyền lợi hiện hành`.
- [ ] Import được tối thiểu các seed record trong tài liệu này.
- [ ] Mỗi record hiển thị `Chưa xác minh`.
- [ ] Founder có thể Verify / Edit / Reject.
- [ ] Có source document.
- [ ] Có claims.
- [ ] Có audit.
- [ ] DRAFT không xuất hiện như quyền lợi hiện hành.
- [ ] Matching vẫn hoạt động với dữ liệu seed nhưng có cảnh báo.
- [ ] Founder có thể gắn official source vào record.
- [ ] Sau Verify, hệ thống recalculates Match/Eligibility.
- [ ] Không ghi funding vào Finance chỉ vì record tồn tại.
- [ ] Có cấu trúc sẵn cho AI Change Proposal về sau.

---

# 44. Seed import order

Ưu tiên triển khai theo thứ tự:

## P0

1. NATIF tài trợ/đặt hàng.
2. NATIF hỗ trợ lãi suất.
3. NATIF Voucher.
4. TP.HCM NQ 20/2023.
5. TP.HCM NQ 23/2026.
6. AWS Activate Founders/Portfolio.

## P1

7. NAFOSTED.
8. chuyên gia/tư vấn.
9. sản xuất thử.
10. chuyển giao công nghệ.
11. hạ tầng dùng chung.
12. đào tạo.

## P2

13. ưu đãi thuế.
14. ưu đãi đất.
15. sandbox.
16. mua sắm/đặt hàng công.
17. bảo lãnh tín dụng.
18. các nguồn lực hệ sinh thái.

Lý do:

P0 dễ tạo giá trị Founder nhìn thấy và có thể kiểm chứng thực tế sớm.

---

# 45. Hướng dẫn triển khai cho Claude Code

Tài liệu này là **extension document — tài liệu mở rộng**, không thay kiến trúc hiện tại.

Claude Code cần:

1. đọc `COSA_Policy_Funding_Intelligence_Integration.md`;
2. xác định các bảng/schema đã triển khai;
3. chỉ bổ sung seed/catalog/claim/verification còn thiếu;
4. không tạo module trùng;
5. không thay đổi Project/12WY/Finance đang hoạt động;
6. import seed bằng migration hoặc seed script;
7. mọi record seed có `PENDING_FOUNDER_VERIFICATION`;
8. DRAFT record có `publish_to_matching=false`;
9. hỗ trợ Founder verify từng claim;
10. lưu diff khi sửa;
11. không auto-activate;
12. chuẩn bị interface để sau này AI tạo `Change Proposal`.

---

# 46. Demo Flow bắt buộc

## Flow A — Seed Opportunity

```text
Founder
→ Nguồn lực & Chính sách
→ Quyền lợi hiện hành
→ NATIF hỗ trợ lãi suất
→ thấy “Chưa xác minh”
→ Xem nguồn
```

## Flow B — Founder Verify

```text
Record
→ Kiểm chứng
→ gắn nguồn chính thức
→ sửa claim nếu cần
→ Verify
→ status = VERIFIED_ACTIVE
→ recalculate Project match
```

## Flow C — Reject

```text
Record
→ Founder phát hiện slide không còn đúng
→ Reject
→ REJECTED_SOURCE_DATA
→ không dùng cho matching
→ giữ lịch sử
```

## Flow D — AI Update sau này

```text
Official Source changes
→ AI detects
→ Change Proposal
→ Founder/Admin approve
→ Update
→ Notify Projects
```

---

# 47. Kết luận

Bộ seed này giúp COSA có **dữ liệu quyền lợi mẫu ngay trong khi kiến trúc Policy/Funding Intelligence đang được triển khai**, nhưng vẫn giữ ranh giới an toàn:

> **Slide hội thảo = nguồn tham khảo ban đầu.**  
> **Founder verification = bước xác minh giai đoạn đầu.**  
> **AI verification/update = bước tự động hóa ở giai đoạn sau.**

COSA không cần chờ hoàn thành hệ thống crawler/AI pháp lý mới tạo giá trị.

Có thể triển khai theo lộ trình:

```text
Tài liệu hội thảo
→ Seed Current Benefits
→ Founder kiểm chứng
→ Production Catalog
→ AI theo dõi nguồn
→ AI phát hiện thay đổi
→ Founder/Admin duyệt
→ COSA tự cập nhật matching
```

Mục tiêu cuối cùng:

> **Founder không phải đọc lại toàn bộ chính sách mỗi lần. COSA lưu những gì đã biết, biết cái gì đã được xác minh, phát hiện cái gì thay đổi và chỉ đưa Founder những cơ hội đáng hành động.**
