import 'package:get/get.dart';
import '../../../data/services/admin_service.dart';

class DiagnosticsController extends GetxController {
  final AdminService _adminService = AdminService();
  
  final isLoading = false.obs;
  final diagnosticsData = Rxn<Map<String, dynamic>>();

  @override
  void onInit() {
    super.onInit();
    loadData();
  }

  Future<void> loadData() async {
    isLoading.value = true;
    try {
      diagnosticsData.value = await _adminService.getDiagnostics();
    } finally {
      isLoading.value = false;
    }
  }
}
