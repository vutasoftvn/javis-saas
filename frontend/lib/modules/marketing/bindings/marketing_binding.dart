import 'package:get/get.dart';
import '../controllers/marketing_controller.dart';

class MarketingBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<MarketingController>(() => MarketingController());
  }
}
