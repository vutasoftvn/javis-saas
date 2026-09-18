# Data Governance & Quality Framework Playbook

> **Tài liệu tham chiếu chuyên sâu dành cho:** CDO Advisor & Data Platform Engineers  
> **Nguyên tắc cốt lõi:** Data Quality Index $\ge 90\%$, Nguồn gốc dữ liệu minh bạch (Data Lineage), Rà soát Data Drift mỗi 2 tuần.

---

## 1. Chỉ Số Chất Lượng Dữ Liệu Tổng Hợp (Data Quality Index - DQI)

Dữ liệu là nguồn sống của AI và các quyết định của ban giám đốc. CDO Advisor lượng hóa chất lượng dữ liệu theo công thức:

$$\text{DQI (0 - 100)} = (\text{Tính Đầy Đủ \%} \times 0.4) + (\text{Độ Chính Xác \%} \times 0.4) + (\text{Điểm Độ Tươi} \times 0.2)$$

Trong đó:
- **Tính Đầy Đủ (Completeness):** Tỷ lệ các trường dữ liệu bắt buộc không bị `null` hoặc rỗng.
- **Độ Chính Xác (Accuracy):** Tỷ lệ bản ghi vượt qua các bài kiểm tra logic nghiệp vụ và schema validation.
- **Điểm Độ Tươi (Freshness Score):** $\max(0, 100 - (\text{Số Giờ Trễ} \times 2.0))$.

> **Ngưỡng Hành Động:** Nếu $\text{DQI} < 80$ điểm, dashboard chỉ số liên quan sẽ bị gắn nhãn cảnh báo màu vàng `⚠️ Dữ liệu chưa qua xác thực chất lượng`.

---

## 2. Quản Trị Nguồn Gốc Dữ Liệu (Data Lineage & Traceability)

Mọi số liệu tài chính, người dùng và bối cảnh nạp cho AI phải có khả năng truy vết ngược dòng (Provenance):

```
SỰ KIỆN GỐC (Event Ingestion) ──> BIẾN ĐỔI (ETL / Dbt Model) ──> KHO DỮ LIỆU (Warehouse) ──> DASHBOARD / AI CONTEXT
(PostgreSQL / Stripe webhook)        (Có version commit Git)         (Bảng bất biến / Partition)     (Có thẻ thời gian snapshot)
```

- Mọi số liệu báo cáo trước HĐQT phải trỏ được chính xác về ID bản ghi cơ sở dữ liệu nguồn; cấm tuyệt đối các số liệu "tính tay" trong bảng tính Excel không thể tái lập.
