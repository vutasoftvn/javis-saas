import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../services/legal_service.dart';

class LegalObligationController extends GetxController {
  final LegalService service;
  LegalObligationController({LegalService? service})
      : service = service ?? LegalService();

  final isLoading = false.obs;
  final instances = <Map<String, dynamic>>[].obs;

  @override
  void onInit() {
    super.onInit();
    loadInstances();
  }

  Future<void> loadInstances({String? status}) async {
    isLoading.value = true;
    try {
      final list = await service.getObligationInstances(status: status);
      instances.assignAll(list.map((e) => Map<String, dynamic>.from(e as Map)));
    } catch (e) {
      debugPrint('LegalObligationController.loadInstances error: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<bool> startObligation(String id) async {
    isLoading.value = true;
    try {
      final res = await service.transitionObligationInstance(
        id,
        toStatus: 'IN_PROGRESS',
        expectedFromStatus: 'OPEN',
        rationale: 'Bắt đầu triển khai nghĩa vụ',
      );
      if (res != null) {
        AppToast.success('Nghĩa vụ đã chuyển sang trạng thái Đang thực hiện', title: 'Đã cập nhật');
        await loadInstances();
        return true;
      }
      AppToast.error('Không thể chuyển trạng thái nghĩa vụ', title: 'Thao tác thất bại');
      return false;
    } catch (e) {
      AppToast.error('Lỗi khi chuyển trạng thái nghĩa vụ: $e', title: 'Thao tác thất bại');
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  Future<bool> fulfillObligationWithEvidence(
    String id, {
    required List<String> evidenceRefs,
    String? evidenceArtifactId,
    String? rationale,
  }) async {
    if (evidenceRefs.isEmpty && (evidenceArtifactId == null || evidenceArtifactId.isEmpty)) {
      AppToast.warning(
        'Bắt buộc đính kèm bằng chứng (evidence) để hoàn thành nghĩa vụ',
        title: 'Thiếu bằng chứng',
      );
      return false;
    }

    isLoading.value = true;
    try {
      final res = await service.transitionObligationInstance(
        id,
        toStatus: 'FULFILLED',
        evidenceRefs: evidenceRefs,
        evidenceArtifactId: evidenceArtifactId,
        rationale: rationale ?? 'Hoàn thành kèm tài liệu chứng minh',
      );
      if (res != null) {
        AppToast.success('Nghĩa vụ đã được đánh dấu hoàn thành', title: 'Hoàn thành nghĩa vụ');
        await loadInstances();
        return true;
      }
      AppToast.error('Máy chủ từ chối ghi nhận hoàn thành', title: 'Thao tác thất bại');
      return false;
    } catch (e) {
      AppToast.error('Lỗi hoàn thành nghĩa vụ: $e', title: 'Thao tác thất bại');
      return false;
    } finally {
      isLoading.value = false;
    }
  }
}
