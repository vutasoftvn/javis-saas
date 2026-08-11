import 'package:get/get.dart';

class SettingsController extends GetxController {
  final isLoading = false.obs;

  @override
  void onInit() {
    super.onInit();
    loadData();
  }

  Future<void> loadData() async {
    isLoading.value = true;
    try {
      // Load data
    } finally {
      isLoading.value = false;
    }
  }
}
