import 'package:get/get.dart';
import '../controllers/branding_controller.dart';

class BrandingBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<BrandingController>(
      () => BrandingController(),
    );
  }
}
