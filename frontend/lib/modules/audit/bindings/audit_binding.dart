import 'package:get/get.dart';
import '../controllers/audit_controller.dart';

class AuditBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<AuditController>(
      () => AuditController(),
    );
  }
}
