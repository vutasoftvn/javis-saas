import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../models/mission_event.dart';
import '../services/mission_control_service.dart';

class MissionControlController extends GetxController {
  MissionControlController({MissionControlService? service})
    : _service = service ?? MissionControlService();

  final MissionControlService _service;

  final currentMission = Rxn<ChiefOfStaffMission>();
  final events = <MissionEvent>[].obs;
  final pendingApprovals = <dynamic>[].obs;
  final isOrchestrating = false.obs;
  final goalInputController = TextEditingController();

  @override
  void onInit() {
    super.onInit();
    loadApprovals();
  }

  @override
  void onClose() {
    goalInputController.dispose();
    super.onClose();
  }

  Future<void> loadApprovals() async {
    final list = await _service.getPendingApprovals();
    pendingApprovals.assignAll(list);
  }

  Future<void> runMission({String? customGoal}) async {
    final goal = customGoal ?? goalInputController.text.trim();
    if (goal.isEmpty) return;

    isOrchestrating.value = true;
    events.clear();

    // Add immediate local timeline entry
    events.add(
      MissionEvent(
        eventId: 'local_1',
        runId: 'pending',
        agentKey: 'chief_of_staff',
        eventType: 'mission_started',
        timestamp: DateTime.now().toIso8601String(),
        data: {'goal': goal},
      ),
    );

    try {
      final mission = await _service.orchestrateMission(goal);
      if (mission != null) {
        currentMission.value = mission;
        events.add(
          MissionEvent(
            eventId: 'local_completed',
            runId: mission.missionId,
            agentKey: 'chief_of_staff',
            eventType: 'mission_completed',
            timestamp: DateTime.now().toIso8601String(),
            data: {'status': 'completed'},
          ),
        );
      }
    } finally {
      isOrchestrating.value = false;
      await loadApprovals();
    }
  }

  Future<void> approve(String approvalId) async {
    final ok = await _service.approveAction(approvalId);
    if (ok) {
      pendingApprovals.removeWhere(
        (item) => (item['id'] ?? '').toString() == approvalId,
      );
      Get.snackbar(
        'Thành công',
        'Đã phê duyệt hành động của agent',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.green.withValues(alpha: 0.8),
        colorText: Colors.white,
      );
    }
  }

  Future<void> reject(String approvalId, {String? reason}) async {
    final ok = await _service.rejectAction(approvalId, reason: reason);
    if (ok) {
      pendingApprovals.removeWhere(
        (item) => (item['id'] ?? '').toString() == approvalId,
      );
      Get.snackbar(
        'Đã từ chối',
        'Đã từ chối hành động của agent',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.orange.withValues(alpha: 0.8),
        colorText: Colors.white,
      );
    }
  }
}
