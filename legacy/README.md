# Legacy Archive (Thế hệ Kiến trúc 1 & 2)

Thư mục này lưu trữ các module và logic cũ của COSA/Javis SaaS trước khi chuyển đổi sang **AI Agent OS Master Architecture** và **Encore Business Services**.

## Cấu trúc lưu trữ:
- **`business/`**: Chứa `business/` và `business_core/` (Đã chuyển đổi sang `services/` - 4 cluster Encore TS).
- **`agent_runtime/`**: Chứa `cosa_core/`, `workforce/`, `agent_runtime/` (Đã chuẩn hóa sang `agentos/`).
- **`domains/`**: Chứa `founder_os/`, `regulations/` (Đã sáp nhập vào `services/operations` và `services/finance-legal`).
- **`platform/`**: Chứa `platform_core/`, `core/` (Đã chuyển đổi sang `services/identity` và `agentos/core`).
- **`entrypoints/`**: Chứa các file runner cũ (`worker_main.py`, `central_main.py`, `full_main.py`).
