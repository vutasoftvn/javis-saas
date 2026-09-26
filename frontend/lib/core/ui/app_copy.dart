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
library;

import 'package:get/get.dart';

class AppCopy {
  AppCopy._();

  // ── Skill Registry — compact filter sheet (Task 10) ─────────────────────
  static String get skillRegistryFilterTooltip =>
      Get.locale?.languageCode == 'en' ? 'Filters' : 'Bộ lọc';
  static String get skillRegistryFilterSheetTitle =>
      Get.locale?.languageCode == 'en' ? 'Filter Skills' : 'Lọc kỹ năng';
  static String get skillRegistryFilterStatusSection =>
      Get.locale?.languageCode == 'en' ? 'Lifecycle Status' : 'Trạng thái vòng đời';
  static String get skillRegistryFilterDomainSection =>
      Get.locale?.languageCode == 'en' ? 'Domain' : 'Lĩnh vực';
  static String get skillRegistryFilterCloseButton =>
      Get.locale?.languageCode == 'en' ? 'Close' : 'Đóng';

  // ── Hub — dockable chat panel (Task 10, commit 2) ────────────────────────
  static String get hubChatPanelTitle =>
      Get.locale?.languageCode == 'en'
          ? 'Collaborate with COSA Co-Founder'
          : 'Trao đổi cùng COSA Co-Founder';
  static String get hubChatEmptyState =>
      Get.locale?.languageCode == 'en'
          ? 'Ask COSA about business progress, debate assumptions, or assign Missions!'
          : 'Hãy hỏi COSA về tiến độ kinh doanh, phản biện giả định hoặc giao Mission!';
  static String get hubChatInputHint =>
      Get.locale?.languageCode == 'en'
          ? 'Enter message for Co-Founder...'
          : 'Nhập tin nhắn trao đổi với Co-Founder...';
  static String get hubChatNewChatTooltip =>
      Get.locale?.languageCode == 'en'
          ? 'New Chat'
          : 'Tạo mới chat';
}
