/// Task 10 — nơi tập trung copy tiếng Việt hướng tới người dùng cho các màn
/// hình ĐÃ được migrate bởi plan "Frontend Trust and UX Hardening" (Hub,
/// Skill Registry). Đây KHÔNG phải một sweep toàn app — chỉ những chuỗi văn
/// bản thuộc các view mà task này thực sự chạm vào mới được đưa vào đây,
/// đúng tinh thần "migrate pages actually touched" của brief Task 10.
///
/// Quy tắc: KHÔNG đặt mã lỗi backend/system (vd. HTTP status, exception
/// class, correlation id) vào các chuỗi ở đây — người dùng chỉ thấy thông
/// điệp thân thiện; correlation id để trace lỗi phải log riêng qua
/// `debugPrint`/logger, không hiển thị trên UI (xem cách `AppToast.error`
/// trong `founder_command_center_controller.dart` đã tách log kỹ thuật khỏi
/// message hiển thị).
class AppCopy {
  AppCopy._();

  // ── Skill Registry — compact filter sheet (Task 10) ─────────────────────
  static const String skillRegistryFilterTooltip = 'Bộ lọc';
  static const String skillRegistryFilterSheetTitle = 'Lọc kỹ năng';
  static const String skillRegistryFilterStatusSection = 'Trạng thái vòng đời';
  static const String skillRegistryFilterDomainSection = 'Lĩnh vực';
  static const String skillRegistryFilterCloseButton = 'Đóng';

  // ── Hub — dockable chat panel (Task 10, commit 2) ────────────────────────
  static const String hubChatPanelTitle = 'Trao đổi cùng COSA Co-Founder';
  static const String hubChatEmptyState =
      'Hãy hỏi COSA về tiến độ kinh doanh, phản biện giả định hoặc giao Mission!';
  static const String hubChatInputHint = 'Nhập tin nhắn trao đổi với Co-Founder...';
}
