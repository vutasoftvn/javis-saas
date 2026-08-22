---
name: operations.tasks
description: Hướng dẫn phân rã công việc, thiết lập ưu tiên và theo dõi tiến độ hoàn thành.
---

# Hướng Dẫn Quản Lý Và Phân Rã Task

## 1. Tiêu Chí Tạo Task
- **Tiêu đề rõ ràng**: Bắt đầu bằng động từ hành động (ví dụ: *Soạn thảo bản đề xuất dự án X*, *Tối ưu hóa query database Y*).
- **Định rõ mức độ ưu tiên**: `low`, `medium`, `high`, `urgent`.
- **Gán Mode thực thi**: `HUMAN`, `AGENT`, hoặc `HYBRID`.

## 2. Quy Trình Của Agent
1. **Phân rã mục tiêu**: Chia nhỏ nhiệm vụ lớn thành các đơn vị công việc độc lập.
2. **Khởi tạo Task**: Gọi tool `task_create` với `workspaceId`, `title`, `priority`, `dueAt`.
3. **Theo dõi trạng thái**: Kiểm tra danh sách qua `task_list`.
4. **Cập nhật tiến độ**: Gọi tool `task_update_status` khi task chuyển sang `in_progress`, `waiting_approval` hoặc `done`.
