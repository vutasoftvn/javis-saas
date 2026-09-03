import 'package:get/get.dart';
import '../controllers/organization_controller.dart';

class OrganizationBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<OrganizationController>(() => OrganizationController());
  }
}
