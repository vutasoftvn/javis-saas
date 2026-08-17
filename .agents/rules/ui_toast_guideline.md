# Rule: Toast & Snackbar Guideline for Hologram Hub & Mobile

## Guideline
1. **Trang Hologram Hub (Hologram Command Center / HUD)**:
   - **KHÔNG** hiển thị toast / snackbar (`Get.snackbar`, `ScaffoldMessenger.showSnackBar`, v.v.).
   - Mọi trạng thái tương tác (kích hoạt giọng nói, nhận diện wake word, phê duyệt tác vụ, giải quyết đề xuất, v.v.) phải được phản hồi trực tiếp qua hiệu ứng Hologram Avatar, State Indicator, âm thanh hoặc thay đổi trực quan trên giao diện mà không làm gián đoạn trải nghiệm bằng toast che khuất màn hình.

2. **Giao diện Mobile (Mobile Layouts)**:
   - Hạn chế tối đa việc hiển thị toast / snackbar che khuất nội dung hoặc bàn phím trên thiết bị di động.
   - Các hành động trên màn hình Hologram / Chat Mobile cần hiển thị trạng thái inline hoặc micro-interactions thay vì pop-up toast.
