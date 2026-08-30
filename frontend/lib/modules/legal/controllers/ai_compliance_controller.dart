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
    final ok = await service.suspendDeployment(deploymentId, rationale: reason);
    if (ok) {
      Get.snackbar(
        'Đã tạm đình chỉ',
        'Hệ thống AI đã chuyển sang trạng thái SUSPENDED',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
      await load();
    } else {
      Get.snackbar(
        'Thao tác thất bại',
        'Máy chủ từ chối yêu cầu tạm đình chỉ',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    }
    return ok;
  }

  Future<bool> resumeDeployment(String deploymentId, {required String reason}) async {
    final ok = await service.resumeDeployment(deploymentId, rationale: reason);
    if (ok) {
      Get.snackbar(
        'Đã phục hồi',
        'Hệ thống AI đã phục hồi trạng thái APPROVED_FOR_USE',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      await load();
    } else {
      Get.snackbar(
        'Thao tác thất bại',
        'Máy chủ từ chối yêu cầu phục hồi (yêu cầu quyền Founder)',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    }
    return ok;
  }

  Future<bool> approveDeployment(
    String deploymentId, {
    required String assessmentId,
    required String rationale,
    required String expiresAt,
  }) async {
    if (assessmentId.isEmpty || expiresAt.isEmpty) {
      Get.snackbar(
        'Không thể phê duyệt',
        'Cần có đánh giá rủi ro (assessment) và thời hạn hợp lệ để phê duyệt',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
      return false;
    }
    final ok = await service.approveDeployment(
      deploymentId,
      assessmentId: assessmentId,
      rationale: rationale,
      expiresAt: expiresAt,
    );
    if (ok) {
      Get.snackbar(
        'Đã phê duyệt',
        'Founder đã phê duyệt triển khai AI',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      await load();
    } else {
      Get.snackbar(
        'Phê duyệt thất bại',
        'Máy chủ từ chối phê duyệt (yêu cầu quyền Founder và bằng chứng đầy đủ)',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    }
    return ok;
  }

  Future<bool> reportIncident({
    required String deploymentId,
    required String severity,
    required String summary,
    String incidentType = 'COMPLIANCE_BREACH',
  }) async {
    final ok = await service.reportIncident(
      deploymentId: deploymentId,
      severity: severity,
      summary: summary,
      incidentType: incidentType,
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
    } else {
      Get.snackbar(
        'Báo cáo thất bại',
        'Không thể ghi nhận sự cố tuân thủ trên máy chủ',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    }
    return ok;
  }
}
