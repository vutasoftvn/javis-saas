import 'package:get/get.dart';
import '../controllers/skill_registry_controller.dart';

class SkillRegistryBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<SkillRegistryController>(() => SkillRegistryController());
  }
}
