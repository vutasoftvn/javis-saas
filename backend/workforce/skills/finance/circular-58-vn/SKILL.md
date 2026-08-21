---
id: finance.circular_58_vn
name: Circular 58 Vietnam Accounting Compliance Skill
department: finance
version: 1.0.0
description: Rà soát và phân loại hạch toán chi phí theo chuẩn Thông tư 58 / Chế độ Kế toán Doanh nghiệp Việt Nam.
risk_level: medium
required_tools:
  - finance.read_details
  - finance.post_entry
---

# Finance — Rà soát & Hạch toán Theo Chuẩn Kế toán Việt Nam

## 1. Mục tiêu
Đảm bảo các nghiệp vụ chi tiêu, hóa đơn GTGT đầu vào/đầu ra và các khoản tạm ứng được phân bổ đúng tài khoản kế toán và hợp lệ về mặt thuế.

## 2. Quy trình Thực thi
1. Kiểm tra tính hợp lệ của hóa đơn điện tử (Mã tra cứu, Chữ ký số, Thuế suất VAT 8%/10%).
2. Định khoản nghiệp vụ theo hệ thống tài khoản kế toán Việt Nam (TK 111, 112, 131, 331, 642, 156, 133).
3. Đánh giá tính hợp lý của chi phí được trừ khi tính thuế TNDN.
4. Xuất bảng tổng hợp phân tích dòng tiền và đối chiếu công nợ.
