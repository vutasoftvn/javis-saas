import 'package:get/get.dart';
import '../../../data/services/agents_service.dart';
import '../../../data/services/control_plane_service.dart';
import 'package:flutter/material.dart';

class AgentsController extends GetxController {
  final AgentsService _agentsService = AgentsService();
  final ControlPlaneService _controlPlaneService = ControlPlaneService();
  
  final isLoading = false.obs;
  final agents = <Map<String, dynamic>>[].obs;

  final isLoadingActivity = false.obs;
  final activityEvents = <Map<String, dynamic>>[].obs;

  @override
  void onInit() {
    super.onInit();
    loadAgents();
    loadActivity();
  }

  Future<void> loadAgents() async {
    isLoading.value = true;
    try {
      final data = await _agentsService.getAgents();
      agents.value = data.cast<Map<String, dynamic>>();
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> loadActivity() async {
    isLoadingActivity.value = true;
    try {
      final runs = await _controlPlaneService.listRuns(limit: 5);
      final List<Map<String, dynamic>> allEvents = [];
      for (final r in runs) {
        final runId = r['id']?.toString() ?? r['id_str']?.toString();
        if (runId != null) {
          final evs = await _controlPlaneService.getRunEvents(runId);
          allEvents.addAll(evs);
        }
      }
      activityEvents.value = allEvents;
    } catch (_) {
    } finally {
      isLoadingActivity.value = false;
    }
  }

  Future<void> createAgent(Map<String, dynamic> data) async {
    final result = await _agentsService.createAgent(data);
    if (result != null) {
      agents.insert(0, result);
      Get.snackbar('Thành công', 'Đã tạo Agent mới', backgroundColor: Colors.green.withValues(alpha: 0.1), colorText: Colors.green);
    } else {
      Get.snackbar('Lỗi', 'Không thể tạo Agent', backgroundColor: Colors.red.withValues(alpha: 0.1), colorText: Colors.red);
    }
  }

  Future<void> updateAgent(String id, Map<String, dynamic> data) async {
    final result = await _agentsService.updateAgent(id, data);
    if (result != null) {
      final index = agents.indexWhere((a) => a['id'] == id);
      if (index >= 0) {
        agents[index] = result;
      }
      Get.snackbar('Thành công', 'Đã cập nhật Agent', backgroundColor: Colors.green.withValues(alpha: 0.1), colorText: Colors.green);
    } else {
      Get.snackbar('Lỗi', 'Không thể cập nhật Agent', backgroundColor: Colors.red.withValues(alpha: 0.1), colorText: Colors.red);
    }
  }

  Future<void> deleteAgent(String id) async {
    final success = await _agentsService.deleteAgent(id);
    if (success) {
      agents.removeWhere((a) => a['id'] == id);
      Get.snackbar('Thành công', 'Đã xóa Agent', backgroundColor: Colors.green.withValues(alpha: 0.1), colorText: Colors.green);
    } else {
      Get.snackbar('Lỗi', 'Không thể xóa Agent', backgroundColor: Colors.red.withValues(alpha: 0.1), colorText: Colors.red);
    }
  }
}
