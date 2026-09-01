import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../models/mission_event.dart';
import '../services/mission_control_service.dart';
import '../../../modules/mission_control/services/control_plane_service.dart';

class MissionControlController extends GetxController {
  MissionControlController({MissionControlService? service, ControlPlaneService? controlPlaneService})
    : _service = service ?? MissionControlService(),
      _controlPlaneService = controlPlaneService ?? ControlPlaneService();

  final MissionControlService _service;
  final ControlPlaneService _controlPlaneService;

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
    final list = await _controlPlaneService.getPendingApprovals();
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
    final ok = await _controlPlaneService.approveAction(approvalId);
    if (ok) {
      pendingApprovals.removeWhere(
        (item) => (item['id'] ?? '').toString() == approvalId,
      );
      AppToast.success('Đã phê duyệt hành động của agent');
    }
  }

  Future<void> reject(String approvalId, {String? reason}) async {
    final ok = await _controlPlaneService.rejectAction(approvalId, reason: reason);
    if (ok) {
      pendingApprovals.removeWhere(
        (item) => (item['id'] ?? '').toString() == approvalId,
      );
      AppToast.warning(
        'Đã từ chối hành động của agent',
        title: 'Đã từ chối',
      );
    }
  }
}
