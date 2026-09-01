import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
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
      AppToast.warning(
        'Hệ thống AI đã chuyển sang trạng thái SUSPENDED',
        title: 'Đã tạm đình chỉ',
      );
      await load();
    } else {
      AppToast.error(
        'Máy chủ từ chối yêu cầu tạm đình chỉ',
        title: 'Thao tác thất bại',
      );
    }
    return ok;
  }

  Future<bool> resumeDeployment(String deploymentId, {required String reason}) async {
    final ok = await service.resumeDeployment(deploymentId, rationale: reason);
    if (ok) {
      AppToast.success(
        'Hệ thống AI đã phục hồi trạng thái APPROVED_FOR_USE',
        title: 'Đã phục hồi',
      );
      await load();
    } else {
      AppToast.error(
        'Máy chủ từ chối yêu cầu phục hồi (yêu cầu quyền Founder)',
        title: 'Thao tác thất bại',
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
      AppToast.warning(
        'Cần có đánh giá rủi ro (assessment) và thời hạn hợp lệ để phê duyệt',
        title: 'Không thể phê duyệt',
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
      AppToast.success(
        'Founder đã phê duyệt triển khai AI',
        title: 'Đã phê duyệt',
      );
      await load();
    } else {
      AppToast.error(
        'Máy chủ từ chối phê duyệt (yêu cầu quyền Founder và bằng chứng đầy đủ)',
        title: 'Phê duyệt thất bại',
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
      AppToast.warning(
        'Sự cố tuân thủ AI đã được báo cáo',
        title: 'Đã ghi nhận sự cố',
      );
      await load();
    } else {
      AppToast.error(
        'Không thể ghi nhận sự cố tuân thủ trên máy chủ',
        title: 'Báo cáo thất bại',
      );
    }
    return ok;
  }
}
