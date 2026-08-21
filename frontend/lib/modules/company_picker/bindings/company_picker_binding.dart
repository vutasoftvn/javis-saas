import 'package:get/get.dart';
import '../controllers/company_picker_controller.dart';

class CompanyPickerBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<CompanyPickerController>(() => CompanyPickerController());
  }
}
