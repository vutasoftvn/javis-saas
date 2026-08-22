# Strategy & Startup Co-Founder Methodology Domain

Bounded context quản lý phương pháp luận Co-Founder và Strategy cho startup trong hệ thống COSA.

## Business Flow

```
Project → Stage → Assumption → Experiment → Evidence → Gate → Decision → Next Best Action
```

1. **Project**: Dự án khởi nghiệp/sáng kiến chiến lược cốt lõi.
2. **Stage**: Giai đoạn phát triển hiện tại của dự án theo quy chuẩn (ví dụ: `S0_GENESIS`, `S1_PROBLEM_VALIDATION`, `S2_SOLUTION_VALIDATION`, `S3_MVP_BUILD`, `S4_PRODUCT_MARKET_FIT`, `S5_SCALE`).
3. **Assumption**: Các giả thuyết và tiền đề kinh doanh cần được kiểm chứng, xếp hạng theo `importance × uncertainty`.
4. **Experiment**: Các thử nghiệm được thiết kế để xác thực/bác bỏ giả thuyết.
5. **Evidence**: Dữ liệu và bằng chứng thu thập được từ thực tế (interviews, transactions, metrics, surveys, v.v.), được chấm điểm `strength` và `confidence` theo thang [0, 1].
6. **Gate**: Cổng đánh giá chính sách giai đoạn (`StagePolicy` & `GateEvaluation`) dựa trên bằng chứng và rủi ro cản trở, thực thi 100% tất định (không gọi LLM).
7. **Decision**: Bản ghi quyết định điều hành (`proceed`, `pivot`, `kill`, `hold`) kèm snapshot bằng chứng tại thời điểm đánh giá.
8. **Next Best Action**: Danh sách hành động ưu tiên tối ưu tiếp theo được đề xuất và xếp hạng theo thuật toán tất định từ các nguồn dữ liệu thực tế (assumptions chưa giải quyết, blocker tasks, khoảng cách OKR, điều kiện gate).
