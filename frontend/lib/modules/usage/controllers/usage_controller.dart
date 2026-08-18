import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/ai_service.dart';
import '../../../data/services/agent_platform_service.dart';

class UsageController extends GetxController {
  final AiService _aiService = AiService();
  final AgentPlatformService _agentPlatformService = AgentPlatformService();

  final isLoading = false.obs;
  final isLoadingBudgets = false.obs;
  final isLoadingCostLedger = false.obs;

  final selectedPeriod = '30d'.obs;
  final Rxn<Map<String, dynamic>> summary = Rxn<Map<String, dynamic>>();

  // Phase B: Governance Budget & Cost Ledger
  final budgets = <Map<String, dynamic>>[].obs;
  final costLedgerEntries = <Map<String, dynamic>>[].obs;
  final costSummary = <String, dynamic>{}.obs;

  @override
  void onInit() {
    super.onInit();
    loadUsage();
    loadBudgets();
    loadCostLedger();
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

  Future<void> loadBudgets() async {
    isLoadingBudgets.value = true;
    try {
      final list = await _agentPlatformService.getBudgets();
      budgets.value = list;
    } finally {
      isLoadingBudgets.value = false;
    }
  }

  Future<void> loadCostLedger({String? billingCycle}) async {
    isLoadingCostLedger.value = true;
    try {
      final data = await _agentPlatformService.getCostLedger(billingCycle: billingCycle);
      if (data != null) {
        costSummary.value = data['summary'] ?? {};
        final recent = data['recent_entries'] as List<dynamic>? ?? [];
        costLedgerEntries.value = recent.map((e) => e as Map<String, dynamic>).toList();
      }
    } finally {
      isLoadingCostLedger.value = false;
    }
  }

  Future<void> setAgentBudget(String agentKey, double limitUsd) async {
    final res = await _agentPlatformService.setBudget(agentKey: agentKey, limitUsd: limitUsd);
    if (res != null) {
      Get.snackbar(
        'Thành công',
        'Đã cập nhật hạn mức ngân sách cho $agentKey',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.2),
        colorText: const Color(0xFF10B981),
      );
      await loadBudgets();
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
