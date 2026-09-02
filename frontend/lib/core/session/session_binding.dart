/// Task 4/5 — đảm bảo `SessionController` VÀ `RemoteAccessController` luôn
/// tồn tại (permanent, một instance duy nhất toàn app) trước khi bất kỳ
/// trang nào cần `Get.find<...>()`. `main.dart` tự `Get.put(SessionController)`
/// sớm trong bootstrap; binding này chỉ là lưới an toàn thứ hai (vd.
/// hot-restart khiến GetX container mất instance permanent) — guard bằng
/// `isRegistered` để không tạo thêm instance thứ hai đè lên state đã có.
///
/// `RemoteAccessController` PHẢI được đăng ký ở đây (không chỉ trong test):
/// trước Task 5, không nơi nào trong app thật gọi `Get.put(RemoteAccessController())`,
/// nên nhánh `if (Get.isRegistered<RemoteAccessController>())` trong
/// `SessionController._commit`/`logout` luôn false — `RuntimeAppChrome`
/// (banner offline/degraded) sẽ không bao giờ nhận cập nhật trong app thật
/// nếu thiếu dòng này.
library;

import 'package:get/get.dart';

import '../../modules/remote_access/controllers/remote_access_controller.dart';
import 'session_controller.dart';

class SessionBinding extends Bindings {
  @override
  void dependencies() {
    if (!Get.isRegistered<SessionController>()) {
      Get.put(SessionController(), permanent: true);
    }
    if (!Get.isRegistered<RemoteAccessController>()) {
      Get.put(RemoteAccessController(), permanent: true);
    }
  }
}
