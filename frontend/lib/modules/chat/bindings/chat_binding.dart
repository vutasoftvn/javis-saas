import 'package:get/get.dart';
import '../../../core/services/voice_service.dart';
import '../controllers/chat_controller.dart';

class ChatBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<ChatController>(() => ChatController(voiceService: VoiceService()));
  }
}
