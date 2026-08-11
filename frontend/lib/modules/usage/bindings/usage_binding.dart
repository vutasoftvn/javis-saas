import 'package:get/get.dart';
import '../controllers/usage_controller.dart';

class UsageBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<UsageController>(() => UsageController());
  }
}
