---
name: commercial-launch
description: Hướng dẫn quản lý kế hoạch ra mắt sản phẩm (GTM Launch), kiểm tra các cổng sẵn sàng (Readiness Gates), kịch bản ngày ra mắt và kiểm soát chất lượng hậu ra mắt.
---

# Quy Trình Quản Lý Kế Hoạch Ra Mắt Sản Phẩm (Product Launch & GTM Readiness)

## 1. Mục Tiêu (Objective)
Đảm bảo quy trình ra mắt sản phẩm hoặc tính năng mới (Go-To-Market Launch) diễn ra an toàn, có kiểm soát và phối hợp nhịp nhàng giữa các bộ phận (Sản phẩm, Kỹ thuật, Marketing, Chăm sóc khách hàng, Pháp lý); thiết lập các cổng kiểm tra độ sẵn sàng (Readiness Gates) trước khi công bố ra thị trường.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi chuẩn bị phát hành tính năng lớn, phiên bản Beta hoặc ra mắt sản phẩm chính thức ra thị trường.
  - Khi cần checklist kiểm tra toàn diện trước ngày ra mắt (Pre-launch review).
  - Khi xây dựng kịch bản vận hành chi tiết cho ngày ra mắt (Launch Day Runbook) và quy trình xử lý sự cố.
- **Khi nào KHÔNG dùng**:
  - Khi chỉ cần viết nội dung bài thông báo hoặc bản tin ra mắt (dùng `marketing.copywriting`).
  - Khi đánh giá hiệu quả số liệu sau khi chiến dịch ra mắt đã chạy xong nhiều tuần (dùng `marketing.campaign-review`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Thông tin về tính năng/sản phẩm ra mắt, ngày phát hành dự kiến và danh sách các kênh phân phối.
- Trạng thái hoàn thành kỹ thuật và hồ sơ định vị (`marketing.positioning`).

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Kiểm Tra Cổng Sẵn Sàng (Readiness Gate Criteria)**:
   - *Technical Readiness (Kỹ thuật)*: Môi trường production ổn định, kiểm thử tải (Load test) hoàn tất, quy trình sao lưu và rollback sẵn sàng, giám sát lỗi (Sentry/APM) đang hoạt động.
   - *Marketing & Assets Readiness (Tiếp thị)*: Trang landing page, tài liệu giới thiệu, ảnh/video demo, bài viết blog đã được chuẩn bị và duyệt nội dung.
   - *Billing & Legal Readiness (Thanh toán & Pháp lý)*: Cổng thanh toán hoạt động chính xác trong môi trường live, điều khoản dịch vụ (Terms of Service) và chính sách quyền riêng tư (Privacy Policy) đã cập nhật.
   - *Support & Documentation Readiness (Hỗ trợ)*: Đội ngũ hỗ trợ đã được đào tạo về tính năng mới, tài liệu hướng dẫn sử dụng (Help Center / Docs) đã xuất bản.
2. **Xây Dựng Kịch Bản Ngày Ra Mắt (Launch Day Runbook)**:
   - Thời gian biểu theo từng giờ (T-2h, T-0, T+2h, T+6h).
   - Phân công người chịu trách nhiệm trực tiếp (DRI - Directly Responsible Individual) cho từng kênh thông báo (Product Hunt, Email, Social, PR, In-app banner).
   - Quy trình báo cáo và leo thang sự cố (Incident Escalation Matrix).
3. **Giám Sát Thời Gian Thực & Kế Hoạch Ứng Phó (Live Monitoring)**:
   - Theo dõi lưu lượng truy cập máy chủ, tỷ lệ lỗi 5xx, số lượng vé hỗ trợ phát sinh, và phản hồi trực tiếp của cộng đồng trong 24 giờ đầu.
4. **Quy Trình Đánh Giá Hậu Ra Mắt (Post-Launch Review)**:
   - Sau 48 - 72 giờ: Đánh giá số lượng người dùng kích hoạt, tỷ lệ chuyển đổi ban đầu, phân loại các lỗi phát sinh cần khắc phục khẩn cấp (Hotfix triage).
   - Sau 14 ngày: Họp rút kinh nghiệm (Post-mortem retro) và đo lường tỷ lệ giữ chân ban đầu.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Tài liệu được xuất bản dưới dạng kế hoạch checklist và runbook phối hợp.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Cổng sẵn sàng (Readiness Gate) chỉ được đánh dấu là `Passed` khi có xác nhận kiểm thử thực tế từ các bộ phận liên quan (ví dụ: đã thực hiện giao dịch thử $1 thành công trên production).
- Không tự ý bỏ qua các bước kiểm tra an toàn kỹ thuật hoặc pháp lý.

## 7. Safe Fallback & Giới Hạn Nghiêm Ngặt (Non-Deployment Policy)
- **Giới hạn nghiêm ngặt**: Skillpack này CHỈ đóng vai trò kiểm soát quy trình, cung cấp checklist và điều phối kế hoạch.
- **Tuyệt đối KHÔNG**: Tự động bấm nút kích hoạt deployment lên server production, tự động gửi email thông báo hàng loạt ra ngoài, hay tự động đăng bài lên mạng xã hội/Product Hunt.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Kế Hoạch Ra Mắt Sản Phẩm & Cổng Sẵn Sàng (GTM Launch Plan)

## 1. Cổng Kiểm Tra Độ Sẵn Sàng (Readiness Gate)
| Hạng Mục | Tiêu Chí Kiểm Tra | Trạng Thái (Passed/Blocked) | Người Chịu Trách Nhiệm (DRI) |
| --- | --- | --- | --- |
| Kỹ thuật & Hạ tầng | Test tải, Rollback plan, APM monitoring | Passed | [Tech Lead] |
| Tiếp thị & Tài sản | Landing page live, Demo assets ready | Passed | [Marketing Lead] |
| Thanh toán & Pháp lý | Test live transaction, ToS updated | Passed | [Ops/Finance] |
| Hỗ trợ khách hàng | Help Docs published, Team briefed | Passed | [CS Lead] |

## 2. Kịch Bản Ngày Ra Mắt (Launch Day Runbook)
- **T-2 Giờ**: Kiểm tra lần cuối môi trường production, kích hoạt feature flag nội bộ.
- **T-0 (Giờ G)**: Bật tính năng cho toàn bộ người dùng, gửi email thông báo đợt 1.
- **T+2 Giờ**: Công bố trên các kênh cộng đồng và mạng xã hội.
- **T+6 Giờ**: Họp nhanh kiểm tra tải hệ thống và số lượng vé hỗ trợ.

## 3. Kế Hoạch Ứng Phó Sự Cố (Escalation Plan)
- **Sự cố tải cao / lỗi hệ thống**: [Quy trình Rollback và thông báo bảo trì]
- **Sự cố thanh toán**: [Chuyển tạm sang chế độ ghi nhận giao dịch chờ xử lý]

## 4. Checklist Đánh Giá Hậu Ra Mắt (Post-Launch Retro)
- [ ] Tổng hợp feedback của 100 người dùng đầu tiên
- [ ] Phân loại lỗi backlog theo mức độ nghiêm trọng (P0/P1/P2)
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Có tiêu chí kỹ thuật hoặc thanh toán chưa đạt (Blocked)**: Tự động cảnh báo dừng ra mắt (NO-GO Decision) cho đến khi sự cố được khắc phục hoàn toàn.
- **Lưu lượng vượt dự kiến gây quá tải**: Hướng dẫn áp dụng cơ chế xếp hàng chờ (Waitlist/Queue throttling) thay vì để sập hệ thống.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/marketingskills
  commit: b1aaa3619e747f4a836c61e03084c4a531de1262
  skill: launch
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Khung Launch Checklist, Phân chia các giai đoạn Pre-launch, Launch day và Post-launch
  changed:
    - Chuẩn hóa thuật ngữ COSA
    - Thêm cấu trúc 10 mục bắt buộc và định dạng markdown tiếng Việt
  added:
    - Bốn cổng kiểm tra sẵn sàng nghiêm ngặt (Technical, Marketing, Billing/Legal, Support)
    - Kịch bản ứng phó sự cố và leo thang khẩn cấp (Incident Escalation)
    - Giới hạn nghiêm ngặt không tự động kích hoạt deploy hoặc phát thông báo ra ngoài
  excluded:
    - Tự động gọi webhook deploy hoặc trigger CI/CD pipeline
```
