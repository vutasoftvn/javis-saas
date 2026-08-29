import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/models/ai_compliance_models.dart';
import '../services/ai_compliance_service.dart';

class AiComplianceController extends GetxController {
  final AiComplianceService service;
  AiComplianceController({AiComplianceService? service})
      : service = service ?? AiComplianceService();

  final isLoading = false.obs;
  final centerData = Rxn<AiComplianceCenterData>();

  @override
  void onInit() {
    super.onInit();
    load();
  }

  Future<void> load() async {
    isLoading.value = true;
    try {
      final res = await service.getComplianceCenter();
      centerData.value = res;
    } catch (e) {
      debugPrint('AiComplianceController.load error: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<bool> suspendDeployment(String deploymentId, {required String reason}) async {
    final ok = await service.suspendDeployment(deploymentId, reason: reason);
    if (ok) {
      Get.snackbar(
        'Đã tạm đình chỉ',
        'Hệ thống AI đã chuyển sang trạng thái SUSPENDED',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
      await load();
    }
    return ok;
  }

  Future<bool> resumeDeployment(String deploymentId, {required String reason}) async {
    final ok = await service.resumeDeployment(deploymentId, reason: reason);
    if (ok) {
      Get.snackbar(
        'Đã phục hồi',
        'Hệ thống AI đã phục hồi trạng thái APPROVED_FOR_USE',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      await load();
    }
    return ok;
  }

  Future<bool> approveDeployment(String deploymentId, {required String rationale}) async {
    final ok = await service.approveDeployment(deploymentId, rationale: rationale);
    if (ok) {
      Get.snackbar(
        'Đã phê duyệt',
        'Founder đã phê duyệt triển khai AI',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      await load();
    }
    return ok;
  }

  Future<bool> reportIncident({
    required String deploymentId,
    required String severity,
    required String summary,
  }) async {
    final ok = await service.reportIncident(
      deploymentId: deploymentId,
      severity: severity,
      summary: summary,
    );
    if (ok) {
      Get.snackbar(
        'Đã ghi nhận sự cố',
        'Sự cố tuân thủ AI đã được báo cáo',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFF59E0B),
        colorText: Colors.white,
      );
      await load();
    }
    return ok;
  }
}
