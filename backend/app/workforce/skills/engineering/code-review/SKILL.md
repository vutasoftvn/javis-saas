---
id: engineering.code_review
name: Secure Code Review & Architecture Compliance Skill
department: engineering
version: 1.0.0
description: Đánh giá chất lượng code, phát hiện lỗ hổng bảo mật OWASP, kiểm tra tuân thủ kiến trúc và tối ưu hiệu năng.
risk_level: medium
required_tools:
  - git.diff.read
  - static_analysis.run
---

# Engineering — Code Review & Kiến Trúc

## 1. Mục tiêu
Đảm bảo mã nguồn tuân thủ Clean Code, không để lọt Hardcoded Secrets, SQL Injection, và duy trì tính toàn vẹn của mô hình kiến trúc đa domain.

## 2. Quy trình Thực thi
1. Kiểm tra Git diff của nhánh hoặc Pull Request.
2. Quét bảo mật: Phát hiện API keys, password, secret refs chưa được mã hóa.
3. Kiểm tra kiến trúc: Không import chéo vi phạm ranh giới Domain, tuân thủ mô hình bất biến và type-safety.
4. Xuất bản nhận xét review chi tiết kèm đề xuất cải thiện (Diff format).
