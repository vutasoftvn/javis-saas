---
name: google-search
description: >-
  Tìm kiếm thông tin trên internet qua Google Search và Web Research.
  Kích hoạt khi cần tra cứu tài liệu, tin tức, dữ liệu thị trường hoặc kiểm tra thông tin trực tuyến.
---

# Google Search & Web Research Skill

Skill này hướng dẫn quy trình tìm kiếm và tổng hợp thông tin từ internet.

## Chức năng chính
1. **Google Search (`google.search`)**: Tra cứu từ khóa, truy vấn câu hỏi và lấy danh sách kết quả (tiêu đề, URL, snippet).
2. **Web Content Extractor (`web.extract`)**: Đọc và trích xuất nội dung bài viết chi tiết từ URL mà không bị lẫn mã HTML thừa (header/footer/ads).
3. **Tổng hợp & Trích dẫn**: Tổng hợp kết quả tìm kiếm kèm đường link nguồn rõ ràng, trung thực.

## Các nhà cung cấp hỗ trợ (Search Providers)
- **Google Custom Search JSON API**: Cần biến môi trường `GOOGLE_SEARCH_API_KEY` và `GOOGLE_CSE_ID`.
- **SerpApi**: Cần biến môi trường `SERPAPI_API_KEY`.
- **Tavily API**: Cần biến môi trường `TAVILY_API_KEY`.
- **Zero-config Fallback**: Tự động fallback sang DuckDuckGo/Web crawler khi chưa cấu hình API key để đảm bảo tác vụ không bị gián đoạn.

## Quy trình làm việc chuẩn (Standard Workflow)
1. Xác định rõ mục tiêu tìm kiếm (từ khóa chính xác, ngôn ngữ, phạm vi).
2. Gọi `google.search(query="...", num_results=5)`.
3. Nếu cần thông tin chuyên sâu từ một nguồn bài viết cụ thể, gọi `web.extract(url="...")`.
4. Trình bày câu trả lời cấu trúc rõ ràng: Tóm tắt thông tin, các điểm cốt lõi, trích dẫn liên kết nguồn.
