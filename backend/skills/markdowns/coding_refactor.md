# Hướng dẫn Kỹ năng: Lập trình Clean Architecture & Tách Pure Core

## 1. Mục tiêu
Thiết kế và tái cấu trúc mã nguồn theo mô hình Clean Architecture, cô lập 100% tầng Business Core khỏi AI/LLM SDK và sinh bản đặc tả kỹ thuật BuildSpec chuẩn hóa.

## 2. Quy trình Thực hiện
1. **Cô lập Tầng Core:** Tuyệt đối không import thư viện ngoài hay LLM SDK vào trong `core/`.
2. **Xác lập Hợp đồng Trừu tượng (Abstract Contracts):** Định nghĩa Interfaces bằng ABC và Pydantic trước khi code implementation.
3. **Soạn thảo BuildSpec:** Ghi rõ mục tiêu, danh sách file cho phép can thiệp, tiêu chuẩn nghiệm thu và bộ test cases cần chạy.
