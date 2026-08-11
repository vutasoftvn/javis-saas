import 'package:get/get.dart';
import '../../../data/services/ai_service.dart';

class UsageController extends GetxController {
  final AiService _aiService = AiService();

  final isLoading = false.obs;
  final Rxn<Map<String, dynamic>> summary = Rxn<Map<String, dynamic>>();

  @override
  void onInit() {
    super.onInit();
    loadUsage();
  }

  Future<void> loadUsage() async {
    isLoading.value = true;
    try {
      summary.value = await _aiService.getUsage();
    } finally {
      isLoading.value = false;
    }
  }

  Map<String, dynamic> get rolling30d =>
      (summary.value?['rolling_30d'] as Map<String, dynamic>?) ?? const {};

  Map<String, dynamic> get allTime =>
      (summary.value?['all_time'] as Map<String, dynamic>?) ?? const {};

  Map<String, dynamic> get byProvider =>
      (summary.value?['by_provider'] as Map<String, dynamic>?) ?? const {};
}
