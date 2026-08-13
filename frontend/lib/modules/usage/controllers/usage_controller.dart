import 'package:get/get.dart';
import '../../../data/services/ai_service.dart';

class UsageController extends GetxController {
  final AiService _aiService = AiService();

  final isLoading = false.obs;
  final selectedPeriod = '30d'.obs;
  final Rxn<Map<String, dynamic>> summary = Rxn<Map<String, dynamic>>();

  @override
  void onInit() {
    super.onInit();
    loadUsage();
  }

  Future<void> loadUsage({String? period}) async {
    final p = period ?? selectedPeriod.value;
    isLoading.value = true;
    try {
      summary.value = await _aiService.getUsage(period: p);
    } finally {
      isLoading.value = false;
    }
  }

  void setPeriod(String period) {
    if (selectedPeriod.value == period) return;
    selectedPeriod.value = period;
    loadUsage(period: period);
  }

  Future<bool> saveCustomOpenRouterKey(String apiKey) async {
    isLoading.value = true;
    try {
      final ok = await _aiService.saveOpenRouterKey(apiKey: apiKey);
      if (ok) {
        await loadUsage();
      }
      return ok;
    } finally {
      isLoading.value = false;
    }
  }

  Future<bool> removeCustomOpenRouterKey() async {
    isLoading.value = true;
    try {
      final ok = await _aiService.deleteOpenRouterKey();
      if (ok) {
        await loadUsage();
      }
      return ok;
    } finally {
      isLoading.value = false;
    }
  }

  Map<String, dynamic> get today =>
      (summary.value?['today'] as Map<String, dynamic>?) ?? const {};


  Map<String, dynamic> get week7d =>
      (summary.value?['week_7d'] as Map<String, dynamic>?) ?? const {};

  Map<String, dynamic> get rolling30d =>
      (summary.value?['rolling_30d'] as Map<String, dynamic>?) ?? const {};

  Map<String, dynamic> get allTime =>
      (summary.value?['all_time'] as Map<String, dynamic>?) ?? const {};

  Map<String, dynamic> get currentPeriodSummary =>
      (summary.value?['current_period_summary'] as Map<String, dynamic>?) ?? const {};


  Map<String, dynamic> get byProvider =>
      (summary.value?['by_provider'] as Map<String, dynamic>?) ?? const {};

  Map<String, dynamic> get openRouterKeyInfo =>
      (summary.value?['openrouter_key_info'] as Map<String, dynamic>?) ?? const {};

  Map<String, dynamic> get openRouterStats =>
      (byProvider['openrouter'] as Map<String, dynamic>?) ?? const {};

  Map<String, dynamic> get openRouterModels =>
      (openRouterStats['models'] as Map<String, dynamic>?) ?? const {};
}

