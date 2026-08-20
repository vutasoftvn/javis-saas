# COSA Phase 4: Visual Workflow Compiler and Runtime

Tài liệu này mô tả chi tiết kiến trúc và các ràng buộc của hệ thống Visual Workflow trong COSA.

## 1. Tổng quan kiến trúc (Architecture)

Mô hình biên dịch Workflow mới đảm bảo rằng:
1. **Frontend (Flutter)** chỉ là giao diện authoring (kéo thả) và không có bất kỳ thẩm quyền nào đối với tính hợp lệ của workflow. Graph JSON sinh ra từ Flutter được coi là **untrusted** (không đáng tin cậy).
2. **Backend Compiler** nhận Graph JSON và biên dịch nó dựa trên `NodeRegistry`. Registry này hợp nhất các node `core` và các node từ `Extension Registry`.
3. Quá trình chạy (Runtime) sử dụng **ToolInvocationService** (được xây dựng ở Phase 3) cho tất cả các node thực thi Tool, kế thừa hoàn toàn các cơ chế an toàn như Timeout, Governance Policy Gate và Output Safety.

## 2. Vòng đời của Workflow (Persistence Lifecycle)

Một phiên bản (WorkflowVersion) giờ đây có một vòng đời (state) khắt khe:
- **draft**: Bản nháp, có thể liên tục được chỉnh sửa bởi tác giả. Sử dụng cơ chế khóa lạc quan (optimistic concurrency) thông qua `revision_token` để tránh ghi đè.
- **validated**: Bản nháp đã vượt qua Compiler thành công (không có unreachable node, missing entry, rủi ro thiếu approval).
- **published**: Phiên bản đã sẵn sàng để chạy (run). Khi chuyển sang published, graph bị đóng băng (immutable). Không thể sửa đổi một published version.
- **archived**: Phiên bản đã bị lưu trữ. Không thể tạo run mới, nhưng lịch sử run cũ vẫn được giữ lại.

## 3. Trình biên dịch (Deterministic Compiler)

`compiler.py` thực hiện các bước sau:
1. Kiểm tra node đầu vào (`entry_node_id`) hợp lệ.
2. Dùng thuật toán DFS quét toàn bộ các node để đảm bảo mọi node đều có thể truy cập được (reachable). Bất kỳ unreachable node nào cũng sẽ trả về diagnostic warning.
3. Kiểm tra tính tương thích của Port Schema (đầu ra của node này phải khớp với đầu vào của node kia).
4. Phân tích rủi ro: Nếu một `ToolNodeDefinition` có `risk_level="high"`, Compiler bắt buộc phải có một `ApprovalNodeDefinition` đứng trước nó trong đường dẫn thực thi. Nếu không, trả về lỗi.

## 4. Giao diện Authoring trên Flutter

- Sử dụng thư viện đồ thị tự code (`InteractiveViewer` + `CustomPaint`) thay vì dùng các package có sẵn, nhằm đáp ứng các yêu cầu kiểm soát port typing nghiêm ngặt và custom Inspector UI.
- Node Inspector hiển thị metadata từ server (không phải từ client tự bịa ra). Nếu server báo lỗi (diagnostics), UI sẽ render icon Warning để người dùng sửa đổi trước khi Publish.
