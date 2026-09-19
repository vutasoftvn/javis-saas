---
name: research-industry-trends
description: Khảo sát xu hướng ngành, tín hiệu thị trường và đo lường xung lực thảo luận thời gian thực (Market Pulse) đa kênh qua 5 góc nhìn phân tích và cửa sổ thời gian recency.
---

# Quy Trình Đo Xung Lực Thị Trường & Xu Hướng Ngành (Industry Trends & Market Pulse)

## 1. Mục Tiêu (Objective)
Đo lường nhịp đập thị trường và nhận diện các xu hướng công nghệ / kinh doanh mới nổi trong một cửa sổ thời gian xác định (7, 14, 30, 60 hoặc 90 ngày). Khác với các tài liệu canonical cố định, kỹ năng này tập trung vào **cuộc hội thoại và phản ứng thời gian thực (Current Conversation)** của cộng đồng, khách hàng và chuyên gia thông qua mô hình 5 Góc Nhìn Phân Tích (*5-Angle Analysis*).

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi cần nắm bắt phản ứng mới nhất của thị trường về một công nghệ, đối thủ hoặc giải pháp ("Mọi người đang bàn tán gì về X?").
  - Khi cần nhận diện các phàn nàn (*complaints*), lỗ hổng dịch vụ (*unmet needs*) hoặc làn sóng công nghệ mới nổi.
  - Khi chuẩn bị cập nhật chiến lược sản phẩm trong giai đoạn `P0_DISCOVERY` hoặc `P1_PROBLEM_VALIDATION`.
- **Khi nào KHÔNG dùng**:
  - Khi cần thẩm định tài chính hoặc pháp lý một công ty cụ thể (dùng `research.dossier`).
  - Khi cần tính toán quy mô tổng thể thị trường bằng số liệu định lượng (dùng `research.market-sizing`).
  - Khi tối ưu hóa bài viết LinkedIn hữu cơ (dùng `marketing.linkedin-presence`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Đề tài cụ thể cần khảo sát (từ chối các đề tài quá mơ hồ như "AI", bắt buộc thu hẹp vào góc độ rõ ràng).
- Cửa sổ thời gian khảo sát (`recency_window_days`: 7, 14, 30, 60, hoặc 90 ngày; mặc định 30 ngày).
- Góc nhìn trọng tâm mong muốn (*Angle*).

## 4. Các Bước Tất Định (Deterministic Steps)

```
┌────────────────────────────────────────────────────────┐
│ 1. XÁC ĐỊNH GÓC NHÌN TRỌNG TÂM (5-ANGLE SELECTION)     │
│    • Trend      • Sentiment   • Problems               │
│    • Opportunities            • Comparison             │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. CẤU HÌNH CỬA SỔ THỜI GIAN (RECENCY WINDOW)          │
│    • 7 ngày (Tin nóng)   • 30 ngày (Thảo luận tháng)   │
│    • 90 ngày (Dịch chuyển nhận thức dài hạn)           │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. QUÉT ĐA KÊNH & LỌC TÍN HIỆU                         │
│    • Diễn đàn kỹ thuật (HN, Reddit, Dev.to)            │
│    • Báo chí công nghệ & Báo cáo ngành mới xuất bản    │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. TỔNG HỢP & ĐO ĐỘ HỘI TỤ (PULSE SYNTHESIS)           │
│    • Mật độ đề cập (Buzz Volume) & Cảm xúc chủ đạo     │
│    • Điểm đau nổi cộm & Cơ hội thị trường              │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 5. XUẤT BÁO CÁO KÈM 3-COUNT AUDIT                      │
└────────────────────────────────────────────────────────┘
```

1. **Thu Hẹp Đề Tài & Chọn Góc Nhìn Trọng Tâm (5 Angles)**:
   - *1. Trend (Xu hướng)*: Những gì đang tăng tốc hoặc thoái trào.
   - *2. Sentiment (Cảm xúc)*: Thái độ của cộng đồng (hào hứng, hoài nghi, thất vọng hay trung lập).
   - *3. Problems (Vấn đề & Điểm nghẽn)*: Những phàn nàn, lỗi kỹ thuật, chi phí đắt đỏ của các giải pháp hiện hành.
   - *4. Opportunities (Cơ hội)*: Nhu cầu chưa được đáp ứng, các tính năng người dùng liên tục yêu cầu (*feature requests*).
   - *5. Comparison (So sánh giải pháp)*: Người dùng đang so sánh sản phẩm A với B như thế nào, lý do chuyển đổi (*switching reasons*).
2. **Thiết Lập Cửa Sổ Thời Gian (Recency Window)**:
   - Áp dụng bộ lọc thời gian nghiêm ngặt: 7 ngày cho các sự kiện breaking news; 30 ngày cho khảo sát xu hướng tháng; 90 ngày cho dịch chuyển nhận thức.
   - Loại bỏ các bài viết đã lỗi thời ngoài khung thời gian.
3. **Quét Tín Hiệu Đa Kênh**:
   - Sử dụng `web.search` với các cú pháp tìm kiếm có giới hạn thời gian và tên miền diễn đàn/cộng đồng kỹ thuật.
   - Thu thập trích dẫn nguyên văn (*verbatim quotes*) phản ánh ý kiến thật của người dùng.
4. **Phân Tích Tổng Hợp & Đối Chiếu Mẫu Hình**:
   - Nhận diện các điểm đồng thuận giữa các nhóm đối tượng khác nhau (ví dụ: các lập trình viên trên HN đồng tình với các chuyên gia trên Reddit).
   - Phân biệt giữa "tiếng ồn tiếp thị" (marketing noise của nhà bán hàng) với "tiếng nói người dùng thật" (organic user voice).
5. **Đóng Gói Báo Cáo Xung Lực**:
   - Trình bày kết quả theo cấu trúc mạch lạc kèm trích dẫn nguồn có kiểm chứng và bảng kiểm toán Three-Count.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `web.search`: Truy vấn tin tức, bài viết chuyên môn và thảo luận cộng đồng trên internet.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- **Tính thời sự (Recency Enforcement)**: Bắt buộc ghi rõ ngày công bố của từng nguồn dẫn chứng. Nguồn tin vượt quá cửa sổ thời gian phải được gắn nhãn `[Historical Context]`.
- **Trích dẫn có liên kết**: Mọi nhận định về xu hướng hay cảm xúc phải trích dẫn URL cụ thể.
- **Three-Count Audit bắt buộc**: Thống kê số lượng truy vấn đã gửi, số bài viết tiếp nhận, và số trích dẫn đưa vào bài.

## 7. Safe Fallback (Khi Tìm Kiếm Web Bị Giới Hạn)
- Nếu công cụ tìm kiếm không khả dụng, agent thông báo rõ và chuyển sang phân tích dựa trên tài liệu thị trường có sẵn trong kho lưu trữ dự án.
- Gắn nhãn `[Static Knowledge - Not Live Pulse]` để tránh người dùng hiểu lầm là dữ liệu thời gian thực.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Xung Lực Thị Trường (Market Pulse Brief)

## 1. Tổng Quan Xung Lực (Pulse Overview)
- **Chủ đề**: [Đề tài cụ thể được khảo sát]
- **Cửa sổ thời gian**: [7 / 14 / 30 / 60 / 90] ngày (Từ YYYY-MM-DD đến YYYY-MM-DD)
- **Góc nhìn trọng tâm**: [Trend / Sentiment / Problems / Opportunities / Comparison]
- **Tóm tắt cốt lõi (TL;DR)**: [2-3 câu tổng kết làn sóng dư luận chính]

## 2. Phân Tích Chuyên Sâu Theo Góc Nhìn
### 2.1 [Góc nhìn chính, ví dụ: Những điểm đau nổi cộm (Problems)]
- **Điểm đau 1**: [Mô tả vấn đề người dùng đang phàn nàn nhiều nhất]
  - *Ý kiến thực tế*: "[Trích dẫn nguyên văn phát biểu]"
  - *Dẫn chứng*: [[Reddit/Forum/Tech Article](https://example.com)] - Ngày: [YYYY-MM-DD]
- **Điểm đau 2**: ...

### 2.2 Đánh Giá Cảm Xúc & Phản Ứng Thị Trường (Sentiment Pulse)
- **Tỷ lệ cảm xúc ước tính**: XX% Tích cực | XX% Trung lập / Thận trọng | XX% Tiêu cực / Hoài nghi
- **Lý do dẫn dắt cảm xúc**: [Nguyên nhân sâu xa tạo nên phản ứng này]

## 3. Cơ Hội Đột Phá Cho Sản Phẩm (Emerging Opportunities)
- [Những nhu cầu bị bỏ ngỏ mà các giải pháp hiện tại chưa đáp ứng được]
- [Gợi ý góc định vị sản phẩm hoặc tính năng đón đầu xu hướng]

## 4. Danh Mục Nguồn Dẫn Chứng & Kiểm Toán Truy Vấn
| Kênh | Nguồn | Tiêu đề bài viết / thảo luận | Ngày |
| :--- | :--- | :--- | :--- |
| Tech Press | [TechCrunch](https://...) | [Tiêu đề] | YYYY-MM-DD |
| Community | [Reddit](https://...) | [Tiêu đề thảo luận] | YYYY-MM-DD |

---
**Kiểm toán vết truy vấn (Three-Count Audit):**
- Queries Sent: XX | Sources Received: XX | Sources Cited: XX
- Khung thời gian tuân thủ: 100% trong vòng XX ngày.
```

## 9. Xử Lý Lỗi & Phòng Vệ An Toàn (Security & Edge Cases)
- **Chống thiên lệch từ bot/chiến dịch seeding**: Một số chủ đề bị thao túng bởi bot hoặc bài PR trả tiền. Agent cần đối chiếu chéo nhiều nguồn độc lập, cảnh báo `[Suspected PR / Astroturfing Campaign]` nếu các phát ngôn có cấu trúc từ ngữ giống hệt nhau.
- **Chống suy diễn từ tập mẫu quá nhỏ**: Nếu một nhận xét chỉ xuất hiện trong 1 bình luận đơn lẻ, bắt buộc gắn nhãn `[Single Comment - Weak Signal]`.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: research/skills/pulse
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Mô hình 5 góc nhìn phân tích (Trend, Sentiment, Problems, Opportunities, Comparison)
    - Cơ chế kiểm soát cửa sổ thời gian recency (7-90 ngày)
    - Kỷ luật tìm kiếm đa kênh và trích dẫn bằng chứng verbatim
    - Three-Count Audit Tracking
  changed:
    - Nâng cấp phiên bản lên 1.2.0
    - Bản địa hóa sang tiếng Việt và tích hợp chuẩn cấu trúc 10 mục của COSA
    - Hợp nhất với skillpack research.industry-trends hiện hữu của COSA
  added:
    - Cơ chế phát hiện chiến dịch PR seeding / astroturfing
    - Rào chắn cảnh báo phát ngôn đơn lẻ Weak Signal
  excluded:
    - Các script tự động thao tác browser phụ thuộc bên ngoài
```
