import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../modules/legal/services/legal_service.dart';
import '../../../data/models/finance_legal_models.dart';

class LegalController extends GetxController {
  final LegalService service;
  LegalController({LegalService? service}) : service = service ?? LegalService();

  final isLoading = false.obs;
  final status = <String, dynamic>{}.obs;
  final checklist = <dynamic>[].obs;
  final obligations = <dynamic>[].obs;
  final typedChecklist = <LegalChecklistItemModel>[].obs;
  final typedObligations = <LegalObligationModel>[].obs;
  final legalSources = <Map<String, dynamic>>[].obs;
  final lastAnalysis = Rxn<Map<String, dynamic>>();

  @override
  void onInit() {
    super.onInit();
    load();
  }

  Future<void> load() async {
    isLoading.value = true;
    try {
      final statusRes = await service.getStatus();
      status.assignAll(statusRes);

      final checklistRes = await service.getChecklist();
      checklist.assignAll(checklistRes);
      typedChecklist.assignAll(checklistRes.map((e) => LegalChecklistItemModel.fromJson(Map<String, dynamic>.from(e as Map))));

      final obligationsRes = await service.getObligations();
      obligations.assignAll(obligationsRes);
      typedObligations.assignAll(obligationsRes.map((e) => LegalObligationModel.fromJson(Map<String, dynamic>.from(e as Map))));

      final sourcesRes = await service.getLegalSources();
      legalSources.assignAll(sourcesRes);
    } catch (e) {
      debugPrint('LegalController.load error: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<Map<String, dynamic>?> analyzeContract({
    required String contractText,
    String contractType = 'COMMERCIAL_SERVICE',
  }) async {
    isLoading.value = true;
    try {
      final res = await service.analyzeContract(
        contractText: contractText,
        contractType: contractType,
      );
      if (res != null) {
        lastAnalysis.value = res;
        Get.snackbar(
          'Đã rà soát hợp đồng',
          'Điểm an toàn: ${res['safety_score']}/100 - ${res['risk_level']}',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFF00E5FF),
          colorText: Colors.black,
        );
      }
      return res;
    } finally {
      isLoading.value = false;
    }
  }

  Future<bool> createChecklistItem(String title) async {
    final res = await service.createChecklistItem(title);
    if (res != null) {
      Get.snackbar(
        'Thành công',
        'Đã thêm hạng mục kiểm tra pháp lý',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      await load();
      return true;
    }
    return false;
  }
}
