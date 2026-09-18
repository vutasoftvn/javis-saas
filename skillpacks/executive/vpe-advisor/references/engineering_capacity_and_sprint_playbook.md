# Engineering Capacity & Sprint Management Playbook (Chuẩn 12WY)

> **Tài liệu tham chiếu chuyên sâu dành cho:** VPE Advisor, Engineering Managers & Scrum Masters  
> **Nguyên tắc cốt lõi:** Chu kỳ 6 sprints 2 tuần, Bảo vệ 20% dung lượng nợ kỹ thuật, Tuần 13 Buffer Sprint.

---

## 1. Cấu Trúc Sprint 2 Tuần Trong Chu Kỳ 12-Week Year

Một chu kỳ 12WY được chia thành đúng 6 sprints phát triển tính năng và 1 sprint đệm:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Tuần 01 - 02: Sprint 1 (Khởi động mục tiêu chu kỳ)                     │
│ Tuần 03 - 04: Sprint 2 (Tăng tốc phân phối)                           │
│ Tuần 05 - 06: Sprint 3 (Mid-cycle Review & Đánh giá giả định)          │
│ Tuần 07 - 08: Sprint 4 (Hoàn thiện các Product Bets lớn)               │
│ Tuần 09 - 10: Sprint 5 (Tối ưu hóa và kiểm thử tích hợp)               │
│ Tuần 11 - 12: Sprint 6 (Nước rút chốt mục tiêu chu kỳ 12WY)           │
├────────────────────────────────────────────────────────────────────────┤
│ Tuần 13:      SPRINT ĐỆM (Buffer & Tech Debt Clean-up Sprint)          │
│               Dọn dẹp nợ kỹ thuật, nâng cấp thư viện, viết tài liệu    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Quy Tắc Bất Biến 20% Ngân Sách Nợ Kỹ Thuật (20% Tech Debt Budget)

Trong bất kỳ sprint nào, dung lượng của đội ngũ kỹ sư được phân bổ theo tỷ lệ cố định:

- **70% Dung Lượng:** Phát triển tính năng mới theo Product Bets đã duyệt với CPO.
- **20% Dung Lượng (BẮT BUỘC):** Trả nợ kỹ thuật, refactor mã nguồn phức tạp, tối ưu database queries, viết thêm integration tests.
- **10% Dung Lượng:** Dự phòng cho các sự cố khẩn cấp (Hotfixes) hoặc hỗ trợ khách hàng cấp bách.

> **Cảnh Báo VPE:** Tuyệt đối không bao giờ nhượng bộ cam kết 100% dung lượng cho tính năng mới. Việc cắt bỏ 20% nợ kỹ thuật hôm nay sẽ dẫn đến tê liệt hệ thống và tốc độ phát triển giảm 50% trong 24 tuần tới.

---

## 3. Tiêu Chuẩn Code Review SLA $\le 4$ Giờ

- Một pull request (PR) lý tưởng có quy mô nhỏ: $< 300$ dòng code thay đổi.
- Thời gian chờ review không được quá 4 giờ làm việc. Kỹ sư reviewer phải ưu tiên review code trước khi bắt đầu viết code mới để tránh làm nghẽn dòng chảy công việc của đồng đội.
