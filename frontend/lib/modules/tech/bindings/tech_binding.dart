import 'package:get/get.dart'; import '../controllers/tech_controller.dart';
class TechBinding extends Bindings { @override void dependencies() => Get.lazyPut(() => TechController()); }
