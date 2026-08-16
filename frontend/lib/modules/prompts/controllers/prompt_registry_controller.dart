import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../data/services/auth_service.dart';
import '../../../data/services/prompt_registry_service.dart';

class PromptRegistryController extends GetxController {
  PromptRegistryController({
    PromptRegistryService? service,
    Future<String?> Function()? roleLoader,
  })  : _service = service ?? PromptRegistryService(),
        _roleLoader = roleLoader ?? AuthService().getCachedRole;

  final PromptRegistryService _service;
  final Future<String?> Function() _roleLoader;

  final prompts = <Map<String, dynamic>>[].obs;
  final isLoading = false.obs;
  final isOwner = false.obs;

  @override
  void onInit() {
    super.onInit();
    loadRole();
    loadPrompts();
  }

  Future<void> loadRole() async {
    final role = await _roleLoader();
    isOwner.value = role == 'owner';
  }

  Future<void> loadPrompts() async {
    isLoading.value = true;
    try {
      final data = await _service.listPrompts();
      prompts.assignAll(data);
    } catch (e) {
      debugPrint('Error loading prompts: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<Map<String, dynamic>> loadDetail(String domain, String name) {
    return _service.getPrompt(domain, name);
  }

  Future<void> savePrompt(String domain, String name, String content) async {
    try {
      await _service.updatePrompt(domain, name, content);
      await loadPrompts();
      Get.snackbar(
        'Đã lưu',
        'Prompt "$domain/$name" đã được cập nhật',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Lỗi lưu prompt',
        '$e',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    }
  }

  Future<void> resetPrompt(String domain, String name) async {
    try {
      await _service.resetPrompt(domain, name);
      await loadPrompts();
      Get.snackbar(
        'Đã đặt lại mặc định',
        'Prompt "$domain/$name" đã trở về nội dung mặc định',
        backgroundColor: const Color(0xFF00E5FF).withValues(alpha: 0.8),
        colorText: Colors.black,
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Lỗi đặt lại prompt',
        '$e',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    }
  }
}
