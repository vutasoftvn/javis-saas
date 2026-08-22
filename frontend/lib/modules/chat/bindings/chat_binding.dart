import 'package:get/get.dart';
import '../controllers/chat_controller.dart';
import '../services/agent_chat_service.dart';

class ChatBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<AgentChatService>(() => AgentChatService());
    Get.lazyPut<ChatController>(() => ChatController(service: Get.find<AgentChatService>()));
  }
}
