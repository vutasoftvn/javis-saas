# ADR: Lựa chọn thư viện vẽ đồ thị cho Flutter (Visual Workflow Builder)

## Bối cảnh
Trong Phase 4 của dự án COSA, chúng ta cần một thư viện trên Flutter để hiển thị và chỉnh sửa đồ thị luồng công việc (Workflow Graph). Yêu cầu kỹ thuật:
- Hỗ trợ Pan & Zoom (di chuyển và phóng to/thu nhỏ canvas).
- Hỗ trợ Typed Ports (các điểm kết nối in/out cụ thể trên mỗi Node).
- Accessibility và hiệu năng tốt.
- License phù hợp cho dự án thương mại (MIT, Apache 2.0).

## Các lựa chọn đã đánh giá
1. **flutter_flowy**: 
   - Ưu điểm: Đẹp, hiện đại, dễ tuỳ biến giao diện.
   - Nhược điểm: Chưa hỗ trợ pan/zoom tốt ra ngoài vùng mặc định.
2. **graphview**: 
   - Ưu điểm: Hỗ trợ nhiều layout algorithms (BuchheimWalker, FruchtermanReingold).
   - Nhược điểm: Phù hợp để hiển thị (view-only), thiếu tương tác kéo thả.
3. **flutter_nodes**:
   - Tương đối cũ, ít được maintain.

## Quyết định
Chúng ta sẽ sử dụng **Custom Implementation** dựa trên `InteractiveViewer` và `CustomPaint` của Flutter (kết hợp các tư tưởng từ các thư viện trên) vì đồ thị workflow của chúng ta yêu cầu port logic phức tạp, kiểm tra validation port ngay khi kéo thả (Typed Connection Rejection), và cần custom UI cho Node Inspector.

## Hệ quả
- Tốn nhiều thời gian hơn ban đầu để implement drag/drop, line drawing, pan/zoom.
- Tuy nhiên, độ tuỳ biến cực cao, hoàn toàn đáp ứng được yêu cầu về Typed Ports và Diagnostics của COSA Compiler.
