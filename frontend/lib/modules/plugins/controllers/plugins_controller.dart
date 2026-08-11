import 'package:get/get.dart';
import '../../../data/services/plugins_service.dart';
import 'package:flutter/material.dart';

class PluginsController extends GetxController {
  final PluginsService _pluginsService = PluginsService();
  
  final isLoading = false.obs;
  final plugins = <Map<String, dynamic>>[].obs;

  @override
  void onInit() {
    super.onInit();
    loadPlugins();
  }

  Future<void> loadPlugins() async {
    isLoading.value = true;
    try {
      final data = await _pluginsService.getPlugins();
      plugins.value = data.cast<Map<String, dynamic>>();
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> enablePlugin(String id) async {
    final success = await _pluginsService.enablePlugin(id);
    if (success) {
      Get.snackbar('Thành công', 'Đã bật Plugin', backgroundColor: Colors.green.withValues(alpha: 0.1), colorText: Colors.green);
    } else {
      Get.snackbar('Lỗi', 'Không thể bật Plugin (chỉ Owner mới có quyền)', backgroundColor: Colors.red.withValues(alpha: 0.1), colorText: Colors.red);
    }
  }

  Future<void> disablePlugin(String id) async {
    final success = await _pluginsService.disablePlugin(id);
    if (success) {
      Get.snackbar('Thành công', 'Đã tắt Plugin', backgroundColor: Colors.green.withValues(alpha: 0.1), colorText: Colors.green);
    } else {
      Get.snackbar('Lỗi', 'Không thể tắt Plugin', backgroundColor: Colors.red.withValues(alpha: 0.1), colorText: Colors.red);
    }
  }
}
