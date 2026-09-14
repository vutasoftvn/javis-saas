import 'package:get/get.dart';
import '../controllers/strategy_controller.dart';

class StrategyBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<StrategyController>(() => StrategyController());
  }
}
