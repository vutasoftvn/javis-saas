import 'package:get/get.dart';
import '../controllers/plugins_controller.dart';

class PluginsBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<PluginsController>(
      () => PluginsController(),
    );
  }
}
