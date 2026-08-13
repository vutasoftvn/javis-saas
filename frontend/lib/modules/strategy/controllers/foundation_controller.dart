import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../../data/services/strategy_service.dart';
import '../../../data/services/auth_service.dart';

/// Controller riêng cho tab "Nền tảng" (Canvas Overview + Foundation 1-1-3 +
/// Context Builder) - tách khỏi StrategyController để không phá 3 tab cũ
/// (OKR/Phân tích/Dự án) hiện đang chạy bằng mock data.
class FoundationController extends GetxController {
  final StrategyService _service = StrategyService();
  final AuthService _authService = AuthService();

  final isLoading = false.obs;
  final isSaving = false.obs;
  final isGeneratingAi = false.obs;
  final errorMessage = RxnString();
  final role = RxnString();

  final canvases = <dynamic>[].obs;
  final selectedCanvas = Rxn<Map<String, dynamic>>();
  final currentRevision = Rxn<Map<String, dynamic>>();

  final visionController = TextEditingController();
  final missionController = TextEditingController();

  // Đúng 3 slot cố định - luôn có index 0,1,2 tương ứng slot_no 1,2,3.
  final List<TextEditingController> valueTitleControllers =
      List.generate(3, (_) => TextEditingController());
  final List<TextEditingController> valueDescriptionControllers =
      List.generate(3, (_) => TextEditingController());
  final List<TextEditingController> valueDecisionRuleControllers =
      List.generate(3, (_) => TextEditingController());

  bool get canApprove => role.value == 'admin' || role.value == 'owner';
  bool get canEdit {
    final status = currentRevision.value?['status'];
    return status == null || status == 'draft' || status == 'changes_requested';
  }

  @override
  void onInit() {
    super.onInit();
    _loadRole();
    loadCanvases();
  }

  @override
  void onClose() {
    visionController.dispose();
    missionController.dispose();
    for (final c in [...valueTitleControllers, ...valueDescriptionControllers, ...valueDecisionRuleControllers]) {
      c.dispose();
    }
    super.onClose();
  }

  Future<void> _loadRole() async {
    role.value = await _authService.getCachedRole();
  }

  Future<void> _runGuarded(Future<void> Function() action) async {
    errorMessage.value = null;
    try {
      await action();
    } on StrategyApiException catch (e) {
      errorMessage.value = e.message;
    } catch (e) {
      errorMessage.value = 'Có lỗi xảy ra: $e';
    }
  }

  Future<void> loadCanvases() async {
    isLoading.value = true;
    await _runGuarded(() async {
      final result = await _service.getCanvases();
      canvases.value = result;
      if (result.isNotEmpty) {
        final firstId = result.first['id'] ?? result.first['_id'];
        if (firstId != null) {
          await selectCanvas(firstId);
        }
      }
    });
    isLoading.value = false;
  }

  Future<void> createCanvas(String name, {String? description}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final canvas = await _service.createCanvas(name, description: description);
      await loadCanvases();
      final canvasId = canvas['id']?.toString();
      if (canvasId != null && canvasId.isNotEmpty) {
        await selectCanvas(canvasId);
        // Ngay khi có tên + mô tả là đủ để AI gợi ý Foundation - không bắt người dùng
        // phải tự bấm "Tạo Revision mới" rồi "AI Gợi ý Foundation" thêm 2 bước nữa.
        await createNewRevision();
        await generateAiFoundation();
      }
      Get.snackbar(
        'Thành công',
        'Đã khởi tạo Strategy Canvas và sinh Foundation gợi ý từ AI',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    });
    isSaving.value = false;
  }

  Future<void> updateCanvas(dynamic rawCanvasId, String name, {String? description}) async {
    final canvasId = rawCanvasId?.toString();
    if (canvasId == null || canvasId.isEmpty) return;
    isSaving.value = true;
    await _runGuarded(() async {
      await _service.updateCanvas(canvasId, name: name, description: description);
      await loadCanvases();
      await selectCanvas(canvasId);
      Get.snackbar(
        'Thành công',
        'Đã cập nhật thông tin Strategy Canvas',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    });
    isSaving.value = false;
  }

  Future<void> deleteCanvas(dynamic rawCanvasId) async {
    final canvasId = rawCanvasId?.toString();
    if (canvasId == null || canvasId.isEmpty) {
      Get.snackbar(
        'Lỗi',
        'ID của Strategy Canvas không hợp lệ',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppTheme.accent,
        colorText: Colors.white,
      );
      return;
    }
    isSaving.value = true;
    await _runGuarded(() async {
      await _service.deleteCanvas(canvasId);
      selectedCanvas.value = null;
      currentRevision.value = null;
      _clearFoundationForm();
      await loadCanvases();
      Get.snackbar(
        'Thành công',
        'Đã xóa Strategy Canvas',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    });
    isSaving.value = false;
  }

  Future<void> generateAiFoundation() async {
    final canvasId = selectedCanvas.value?['id']?.toString();
    if (canvasId == null || canvasId.isEmpty) {
      Get.snackbar(
        'Thông báo',
        'Vui lòng chọn hoặc tạo Canvas trước khi sinh Foundation bằng AI',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFE11D48),
        colorText: Colors.white,
      );
      return;
    }
    isGeneratingAi.value = true;
    await _runGuarded(() async {
      final res = await _service.generateAiFoundation(canvasId);
      final foundation = res['foundation'];
      if (foundation != null) {
        visionController.text = foundation['vision'] ?? '';
        missionController.text = foundation['mission'] ?? '';
        final values = (foundation['values'] as List<dynamic>?) ?? [];
        for (int i = 0; i < 3 && i < values.length; i++) {
          valueTitleControllers[i].text = values[i]['title'] ?? '';
          valueDescriptionControllers[i].text = values[i]['description'] ?? '';
          valueDecisionRuleControllers[i].text = values[i]['decision_rule'] ?? '';
        }
      }
      Get.snackbar(
        'Hoàn thành',
        'AI đã sinh gợi ý Vision, Mission và 3 Core Values',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppTheme.surfaceDarkElevated,
        colorText: Colors.white,
      );
    });
    isGeneratingAi.value = false;
  }

  Future<void> selectCanvas(dynamic rawCanvasId) async {
    final canvasId = rawCanvasId?.toString();
    if (canvasId == null || canvasId.isEmpty) return;
    await _runGuarded(() async {
      final detail = await _service.getCanvasDetail(canvasId);
      final Map<String, dynamic> canvasData;
      if (detail.containsKey('canvas') && detail['canvas'] is Map) {
        canvasData = Map<String, dynamic>.from(detail['canvas'] as Map);
        if (detail.containsKey('active_revision')) {
          canvasData['active_revision'] = detail['active_revision'];
        }
        if (detail.containsKey('revisions')) {
          canvasData['revisions'] = detail['revisions'];
        }
      } else {
        canvasData = detail;
      }
      selectedCanvas.value = canvasData;

      final revisions = detail['revisions'] as List<dynamic>?;
      final activeRev = detail['active_revision'];
      final latest = activeRev ?? (revisions != null && revisions.isNotEmpty ? revisions.first : null);
      if (latest != null && latest['id'] != null) {
        await loadRevision(latest['id']);
      } else {
        currentRevision.value = null;
        _clearFoundationForm();
      }
    });
  }

  Future<void> createNewRevision() async {
    final canvas = selectedCanvas.value;
    if (canvas == null) return;
    final canvasId = canvas['id']?.toString();
    if (canvasId == null || canvasId.isEmpty) return;
    isSaving.value = true;
    await _runGuarded(() async {
      final baseId = canvas['active_revision']?['id']?.toString();
      final revision = await _service.createRevision(canvasId, baseRevisionId: baseId);
      await selectCanvas(canvasId);
      if (revision['id'] != null) {
        await loadRevision(revision['id']);
      }
    });
    isSaving.value = false;
  }

  Future<void> loadRevision(dynamic rawRevisionId) async {
    final revisionId = rawRevisionId?.toString();
    if (revisionId == null || revisionId.isEmpty) return;
    await _runGuarded(() async {
      final detail = await _service.getRevisionDetail(revisionId);
      currentRevision.value = detail;
      final foundation = detail['foundation'];
      visionController.text = foundation?['vision'] ?? '';
      missionController.text = foundation?['mission'] ?? '';
      final values = (foundation?['values'] as List<dynamic>?) ?? [];
      for (var slot = 1; slot <= 3; slot++) {
        final matches = values.where((v) => v['slot_no'] == slot);
        final match = matches.isNotEmpty ? matches.first : null;
        valueTitleControllers[slot - 1].text = match?['title'] ?? '';
        valueDescriptionControllers[slot - 1].text = match?['description'] ?? '';
        valueDecisionRuleControllers[slot - 1].text = match?['decision_rule'] ?? '';
      }
    });
  }

  void _clearFoundationForm() {
    visionController.clear();
    missionController.clear();
    for (final c in [...valueTitleControllers, ...valueDescriptionControllers, ...valueDecisionRuleControllers]) {
      c.clear();
    }
  }

  Future<void> saveFoundation() async {
    final revision = currentRevision.value;
    if (revision == null) return;
    isSaving.value = true;
    await _runGuarded(() async {
      final values = List.generate(3, (i) => {
            'slot_no': i + 1,
            'title': valueTitleControllers[i].text.trim(),
            'description': valueDescriptionControllers[i].text.trim(),
            'decision_rule': valueDecisionRuleControllers[i].text.trim(),
          });
      await _service.saveFoundation(
        revision['id'],
        vision: visionController.text.trim(),
        mission: missionController.text.trim(),
        values: values,
      );
      await loadRevision(revision['id']);
    });
    isSaving.value = false;
  }

  Future<void> submitReview() async {
    final revision = currentRevision.value;
    if (revision == null) return;
    isSaving.value = true;
    await _runGuarded(() async {
      await loadRevision((await _service.submitReview(revision['id']))['id']);
      await selectCanvas(selectedCanvas.value!['id']);
    });
    isSaving.value = false;
  }

  Future<void> approveRevision() async {
    final revision = currentRevision.value;
    if (revision == null) return;
    isSaving.value = true;
    await _runGuarded(() async {
      await loadRevision((await _service.approveRevision(revision['id']))['id']);
      await selectCanvas(selectedCanvas.value!['id']);
    });
    isSaving.value = false;
  }

  Future<void> requestChanges(String reason) async {
    final revision = currentRevision.value;
    if (revision == null) return;
    isSaving.value = true;
    await _runGuarded(() async {
      await loadRevision((await _service.requestChanges(revision['id'], reason))['id']);
    });
    isSaving.value = false;
  }
}
