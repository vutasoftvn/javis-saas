import 'package:get/get.dart';
import '../controllers/chatbots_controller.dart';

class ChatbotsBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<ChatbotsController>(
      () => ChatbotsController(),
    );
  }
}
