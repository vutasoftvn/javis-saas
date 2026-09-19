---
name: research-market-sizing
description: Tính toán quy mô thị trường tổng thể (TAM), thị trường phục vụ được (SAM) và thị trường mục tiêu đạt được (SOM) bằng phương pháp đối chiếu kép (Top-down và Bottoms-up), đo lường độ lệch tam giác và lập kế hoạch cỡ mẫu khảo sát Cochran.
---

# Quy Trình Định Quy Mô Thị Trường & Đối Chiếu Tam Giác (TAM/SAM/SOM Market Sizing & Triangulation)

## 1. Mục Tiêu (Objective)
Xác định quy mô thị trường mục tiêu một cách khoa học, khách quan và có thể kiểm chứng độc lập. Kỹ năng này bắt buộc tính toán song song bằng **cả hai phương pháp: Top-down (Từ trên xuống) VÀ Bottoms-up (Từ dưới lên)**, đo lường độ lệch tam giác (*Triangulation Divergence*), và thiết kế cỡ mẫu khảo sát định lượng theo công thức Cochran nhằm loại trừ hoàn toàn việc phỏng đoán số liệu thiếu căn cứ.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Giai đoạn `P1_PROBLEM_VALIDATION` hoặc `P2_SOLUTION_VALIDATION` khi cần chứng minh quy mô cơ hội kinh doanh cho Gate G1/G2.
  - Khi chuẩn bị hồ sơ gọi vốn (Pitch Deck, Investment Memo) hoặc lập kế hoạch kinh doanh hàng năm.
  - Khi cần thiết kế cỡ mẫu khảo sát thị trường định lượng có ý nghĩa thống kê.
- **Khi nào KHÔNG dùng**:
  - Khi chỉ cần phân tích chân dung khách hàng hoặc định vị thương hiệu (dùng `strategy.positioning`).
  - Khi cần khảo sát xu hướng thời gian thực đa kênh (dùng `research.industry-trends`).
  - Khi theo dõi số liệu tài chính nội bộ thực tế của công ty (dùng `finance.unit-economics`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- `workspace_id` và `project_id` hợp lệ.
- Dữ liệu Top-down: Báo cáo phân tích ngành, thống kê chính phủ hoặc tổ chức nghiên cứu uy tín.
- Dữ liệu Bottoms-up: Ước tính số lượng khách hàng mục tiêu trong phân khúc và giá bán trung bình năm (ACV/ARPU).

## 4. Các Bước Tất Định (Deterministic Steps)

```
┌───────────────────────────┐      ┌───────────────────────────┐
│     TOP-DOWN METHOD       │      │     BOTTOMS-UP METHOD     │
│ TAM = Total Market Value  │      │ TAM = Customers x Price   │
│ SAM = TAM x Serviceable % │      │ SAM = TAM x Serviceable % │
│ SOM = SAM x Reachable %   │      │ SOM = SAM x Realistic %   │
└─────────────┬─────────────┘      └─────────────┬─────────────┘
              │                                  │
              └─────────────────┬────────────────┘
                                ▼
              ┌──────────────────────────────────┐
              │     TRIANGULATION TEST           │
              │  Delta = |TAM_td - TAM_bu| / TAM │
              │  Delta <= 30% -> Triangulation OK│
              │  Delta >  30% -> FAILED (Review) │
              └─────────────────┬────────────────┘
                                ▼
              ┌──────────────────────────────────┐
              │    COCHRAN SURVEY SAMPLE PLAN    │
              │   n0 = (Z^2 * p * (1-p)) / e^2   │
              │   Invites = n / Response_Rate    │
              └──────────────────────────────────┘
```

1. **Thu Thập & Xác Minh Dữ Liệu Đầu Vào**:
   - Khảo sát các báo cáo thị trường cấp 1 (Primary) hoặc cấp 2 (Secondary) qua `web.search`.
   - Xác định rõ phân khúc khách hàng tiềm năng ($N$), giá bán kỳ vọng ($P$), tỷ lệ thị trường có thể phục vụ được ($S_{fraction}$), và tỷ lệ thâm nhập thực tế ($R_{share}$).
2. **Tính Toán Top-Down**:
   - $TAM_{top\_down} = \text{Tổng giá trị thị trường ngành}$
   - $SAM_{top\_down} = TAM_{top\_down} \times S_{fraction}$
   - $SOM_{top\_down} = SAM_{top\_down} \times R_{share}$
3. **Tính Toán Bottoms-Up**:
   - $TAM_{bottoms\_up} = N_{customers} \times P_{annual}$
   - $SAM_{bottoms\_up} = TAM_{bottoms\_up} \times S_{fraction}$
   - $SOM_{bottoms\_up} = SAM_{bottoms\_up} \times R_{adoption}$
   - Số khách hàng ngụ ý tại SOM: $\text{Implied Customers} = \lfloor SOM_{bottoms\_up} / P_{annual} \rfloor$.
4. **Kiểm Định Độ Lệch Tam Giác (Triangulation Divergence Test)**:
   - Sử dụng `MarketSizingTriangulator` (`packages/agent/research/analyzers/market_sizing_triangulator.py`).
   - Tính $\Delta = \frac{|TAM_{top\_down} - TAM_{bottoms\_up}|}{TAM_{top\_down}}$.
   - Đối chiếu với dung sai của phân khúc: B2B SaaS $\le 30\%$, Enterprise $\le 25\%$, Consumer $\le 40\%$.
   - Nếu $\Delta > \text{Dung sai}$: Bắt buộc gắn cờ `TRIANGULATION FAILED`, chỉ ra nguyên nhân phân kỳ (giả định quy mô khách hàng hay giá bán bị lệch so với dữ liệu vĩ mô).
5. **Lập Kế Hoạch Khảo Sát Định Lượng (Cochran Sample Size Planning)**:
   - Sử dụng `SurveySamplePlanner` (`packages/agent/research/analyzers/survey_sample_planner.py`).
   - Xác định cỡ mẫu cần hoàn thành với độ tin cậy 95% ($Z=1.96$) và biên độ sai số $e=0.05$:
     $n_0 = \frac{1.96^2 \times 0.5 \times 0.5}{0.05^2} \approx 385\text{ mẫu}$.
   - Nếu tệp khách hàng hữu hạn ($N < 50,000$): Áp dụng hiệu chỉnh $n = \frac{n_0}{1 + (n_0-1)/N}$.
   - Tính toán số lượng lời mời cần gửi dựa trên tỷ lệ phản hồi dự kiến: $\text{Invites} = \lceil n / \text{Response Rate} \rceil$.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `web.search`: Tra cứu số liệu báo cáo ngành từ các tổ chức uy tín, cổng dữ liệu thống kê, và báo cáo nghiên cứu độc lập.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- **Quy tắc bất khả xâm phạm về nguồn gốc**: Tuyệt đối **KHÔNG BAO GIỜ** trích dẫn một con số TAM đơn lẻ mà không có phương pháp tính toán và các giả định đi kèm.
- **Nguồn chứng minh minh bạch**: Mọi số liệu vĩ mô phải có URL tham chiếu nguồn cấp 1 hoặc cấp 2 xác định.
- **Cơ chế Anti-Self-Validation**: Báo cáo quy mô thị trường được tạo dưới dạng bản nháp `candidate` và phải qua phê duyệt của Founder/Admin trước khi gate evaluation ghi nhận.

## 7. Safe Fallback (Khi Chưa Đủ Dữ Liệu)
Khi dữ liệu nghiên cứu bên ngoài bị thiếu hoặc `web.search` chưa khả dụng:
- Agent thông báo rõ nguồn dữ liệu đang thiếu và đưa ra bảng giả định thận trọng (Conservative Scenario).
- Gắn nhãn `[HYPOTHETICAL - REQUIRES EMPIRICAL VALIDATION]` trên mọi con số tính toán.
- Tuyệt đối không tự bịa đặt số liệu thống kê hoặc tên báo cáo ngành.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Định Quy Mô Thị Trường (TAM/SAM/SOM Triangulation Brief)

## 1. Tóm Tắt Quy Mô Thị Trường (Executive Summary)
- **Tên thị trường & Phân khúc**: Mid-market B2B HR Analytics (US & SEA)
- **Profile ngành**: `b2b-saas` (Ngưỡng dung sai: 30%)
- **Kết luận đối chiếu tam giác**: [Triangulation OK / TRIANGULATION FAILED] (Độ lệch: XX.X%)

## 2. Bảng Đối Chiếu Song Song (Dual-Methodology Comparison)
| Chỉ số | Top-Down (Từ trên xuống) | Bottoms-Up (Từ dưới lên) | Chênh lệch (Delta) |
| :--- | :--- | :--- | :--- |
| **TAM** (Tổng quy mô) | $X,XXX,XXX,XXX | $X,XXX,XXX,XXX | XX.X% |
| **SAM** (Phục vụ được) | $XXX,XXX,XXX | $XXX,XXX,XXX | XX.X% |
| **SOM** (Mục tiêu 12-24m) | $XX,XXX,XXX | $XX,XXX,XXX | Số KH ngụ ý: XXX KH |

## 3. Khối Giả Định & Nguồn Bằng Chứng (Assumptions & Citations)
- **Top-Down Sources**: [[Gartner/IDC Report](https://example.com)] - Ngày: [YYYY-MM-DD]
- **Bottoms-Up Assumptions**:
  - Số lượng doanh nghiệp mục tiêu ($N$): XX,XXX doanh nghiệp (Nguồn: Cổng thống kê)
  - Giá bán trung bình năm (ACV): $XX,XXX / năm
  - Tỷ lệ thị trường phục vụ ($S_{fraction}$): XX%
  - Tỷ lệ thâm nhập thực tế ($R_{share}$): X%

## 4. Kế Hoạch Khảo Sát Khách Hàng Định Lượng (Cochran Survey Plan)
- **Độ tin cậy**: 95% (Z = 1.96) | **Biên độ sai số (MOE)**: +/- 5.0%
- **Cỡ mẫu cần hoàn thành (Completes)**: XXX người
- **Tỷ lệ phản hồi dự kiến**: XX% -> **Số lượng khảo sát cần gửi**: X,XXX invites

## 5. Rủi Ro & Khuyến Nghị Hành Động
- [Cảnh báo về rủi ro bão hòa hoặc sai số giá bán]
- **Hành động đề xuất**: Tiến hành kiểm định thực nghiệm thông qua survey hoặc smoke test.
```

## 9. Xử Lý Lỗi & Phòng Vệ An Toàn (Security & Edge Cases)
- **Thiên lệch báo cáo tiếp thị (Vendor Bias)**: Các báo cáo do đối thủ cạnh tranh hoặc bên bán công nghệ công bố thường thổi phồng TAM. Phải ghi nhận cờ `[Vendor Sponsored Report]` và chiết khấu $20\% - 40\%$ vào kịch bản cơ sở.
- **Rào cản chia số 0 (Zero Division)**: Kiểm tra an toàn biến số giá và dung lượng thị trường trước khi tính toán.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: research-ops/skills/market-research
  upstream_version: 2.9.0
  license: MIT
adaptation:
  kept:
    - Phương pháp tính TAM/SAM/SOM kép Top-down và Bottoms-up
    - Khái niệm độ lệch tam giác Triangulation Divergence
    - Công thức Cochran tính cỡ mẫu khảo sát định lượng
    - Khối giả định bắt buộc đi kèm con số quy mô
  changed:
    - Bản địa hóa sang tiếng Việt và tích hợp chuẩn cấu trúc 10 mục của COSA
    - Nâng cấp phiên bản lên 1.2.0
    - Kết nối với bộ phân tích chuẩn MarketSizingTriangulator và SurveySamplePlanner
  added:
    - Tích hợp rào chắn gate P1_PROBLEM_VALIDATION / G1
    - Gắn nhãn rủi ro Vendor Sponsored Report
  excluded:
    - Các script phụ thuộc thư viện môi trường ngoài luồng
```
