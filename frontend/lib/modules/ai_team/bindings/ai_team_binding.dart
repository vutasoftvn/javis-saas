import 'package:get/get.dart';
import '../controllers/ai_team_controller.dart';

class AiTeamBinding extends Bindings {
  @override
  void dependencies() => Get.lazyPut(() => AiTeamController());
}
