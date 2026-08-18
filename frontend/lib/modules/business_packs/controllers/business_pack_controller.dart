import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/business_pack_service.dart';

class BusinessPackController extends GetxController {
  final BusinessPackService _service = BusinessPackService();

  final RxBool isLoading = false.obs;
  final RxList<Map<String, dynamic>> packs = <Map<String, dynamic>>[].obs;
  final Rx<Map<String, dynamic>?> selectedPack = Rx<Map<String, dynamic>?>(null);
  final RxString selectedCategory = 'all'.obs;
  final RxString searchQuery = ''.obs;

  // Asset detail & override state
  final Rx<Map<String, dynamic>?> activeAsset = Rx<Map<String, dynamic>?>(null);
  final RxString activeAssetType = ''.obs; // 'template', 'sop', 'capability'
  final RxBool isResolvingAsset = false.obs;

  // Legal sources linked to current pack
  final RxList<Map<String, dynamic>> legalSources = <Map<String, dynamic>>[].obs;
  final RxBool isLoadingLegal = false.obs;

  @override
  void onInit() {
    super.onInit();
    loadPacks();
  }

  Future<void> loadPacks() async {
    try {
      isLoading.value = true;
      final result = await _service.listPacks();
      packs.assignAll(result);
      if (packs.isNotEmpty && selectedPack.value == null) {
        selectPack(packs.first['id'] ?? packs.first['name']);
      }
    } catch (e) {
      Get.snackbar(
        'Lỗi nạp Knowledge Packs',
        e.toString(),
        backgroundColor: Colors.red.withValues(alpha: 0.8),
        colorText: Colors.white,
      );
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> selectPack(String packId) async {
    try {
      isLoading.value = true;
      final details = await _service.getPackDetails(packId);
      if (details != null) {
        selectedPack.value = details;
        loadLegalSources(packId);
      }
    } catch (e) {
      debugPrint('Error selecting pack: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> loadLegalSources(String packId) async {
    try {
      isLoadingLegal.value = true;
      final sources = await _service.resolveLegalSources(packId);
      legalSources.assignAll(sources);
    } catch (e) {
      debugPrint('Error loading legal sources: $e');
    } finally {
      isLoadingLegal.value = false;
    }
  }

  Future<void> viewTemplate(String packId, String templateId) async {
    try {
      isResolvingAsset.value = true;
      activeAssetType.value = 'template';
      final bundle = await _service.resolveTemplate(packId, templateId);
      activeAsset.value = bundle;
    } catch (e) {
      debugPrint('Error resolving template: $e');
    } finally {
      isResolvingAsset.value = false;
    }
  }

  Future<void> viewSOP(String packId, String sopId) async {
    try {
      isResolvingAsset.value = true;
      activeAssetType.value = 'sop';
      final sop = await _service.resolveSOP(packId, sopId);
      activeAsset.value = sop;
    } catch (e) {
      debugPrint('Error resolving SOP: $e');
    } finally {
      isResolvingAsset.value = false;
    }
  }

  Future<bool> saveOverride({
    required String packId,
    required String assetId,
    required String assetType,
    Map<String, dynamic>? contentOverride,
    String? bodyOverride,
    String? notes,
  }) async {
    try {
      final res = await _service.createOrUpdateOverride(
        packId: packId,
        assetId: assetId,
        assetType: assetType,
        contentOverride: contentOverride,
        bodyOverride: bodyOverride,
        notes: notes,
      );
      if (res != null) {
        Get.snackbar(
          'Thành công',
          'Đã lưu tùy biến cho doanh nghiệp',
          backgroundColor: const Color(0xFF10B981),
          colorText: Colors.white,
        );
        // Refresh details
        await selectPack(packId);
        return true;
      }
    } catch (e) {
      Get.snackbar(
        'Lỗi',
        'Không thể lưu tùy biến: $e',
        backgroundColor: Colors.red.withValues(alpha: 0.8),
        colorText: Colors.white,
      );
    }
    return false;
  }

  Future<bool> resetAssetToFactory(String packId, String assetId) async {
    try {
      final success = await _service.resetToFactory(packId, assetId);
      if (success) {
        Get.snackbar(
          'Đã khôi phục',
          'Tài sản đã được hoàn nguyên về bản gốc Factory Default',
          backgroundColor: const Color(0xFF3B82F6),
          colorText: Colors.white,
        );
        await selectPack(packId);
        return true;
      }
    } catch (e) {
      Get.snackbar(
        'Lỗi',
        'Không thể khôi phục: $e',
        backgroundColor: Colors.red.withValues(alpha: 0.8),
        colorText: Colors.white,
      );
    }
    return false;
  }

  Future<Map<String, dynamic>?> checkUpdates(String packId) async {
    return await _service.checkForUpdates(packId);
  }

  Future<String?> generateDiff(String packId, String oldContent, String newContent) async {
    return await _service.generateDiff(
      packId: packId,
      oldContent: oldContent,
      newContent: newContent,
    );
  }

  Future<bool> resolveConflict({
    required String packId,
    required String assetId,
    required String resolution,
    String? mergedBody,
  }) async {
    final res = await _service.resolveConflict(
      packId: packId,
      assetId: assetId,
      resolution: resolution,
      mergedBody: mergedBody,
    );
    if (res != null && res['status'] != 'error') {
      Get.snackbar(
        'Đã cập nhật',
        'Giải quyết xung đột thành công theo chiến lược: $resolution',
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      await selectPack(packId);
      return true;
    }
    return false;
  }
}
