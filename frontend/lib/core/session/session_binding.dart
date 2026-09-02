/// Task 4 — đảm bảo `SessionController` luôn tồn tại (permanent, một
/// instance duy nhất toàn app) trước khi bất kỳ trang nào cần
/// `Get.find<SessionController>()`. `main.dart` tự `Get.put` sớm trong
/// bootstrap; binding này chỉ là lưới an toàn thứ hai (vd. hot-restart khiến
/// GetX container mất instance permanent) — guard bằng `isRegistered` để
/// không tạo thêm instance thứ hai đè lên state đã có.
library;

import 'package:get/get.dart';

import 'session_controller.dart';

class SessionBinding extends Bindings {
  @override
  void dependencies() {
    if (!Get.isRegistered<SessionController>()) {
      Get.put(SessionController(), permanent: true);
    }
  }
}
