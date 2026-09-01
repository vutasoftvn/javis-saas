import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/network/api_result.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../modules/workforce/models/workforce_mvp_models.dart';
import '../../../modules/workforce/services/workforce_mvp_service.dart';
import '../models/mission_event.dart';
import '../services/mission_control_service.dart';

class MissionControlController extends GetxController {
  MissionControlController({
    MissionControlService? service,
    WorkforceMvpService? workforceMvpService,
  })  : _service = service ?? MissionControlService(),
        _workforceMvpService = workforceMvpService ?? WorkforceMvpService();

  final MissionControlService _service;
  final WorkforceMvpService _workforceMvpService;

  final currentMission = Rxn<ChiefOfStaffMission>();
  final events = <MissionEvent>[].obs;
  final pendingApprovals = <WorkforceApproval>[].obs;
  // Task 3 — lỗi tải approvals gần nhất; 404/5xx không được coi ngầm là danh
  // sách rỗng, UI có thể đọc field này để hiển thị trạng thái không tải được
  // thay vì hiển thị "không có approval nào đang chờ" một cách sai sự thật.
  final approvalsLoadError = Rxn<String>();
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
    final result = await _workforceMvpService.listApprovals();
    result.when(
      success: (data, _) {
        approvalsLoadError.value = null;
        pendingApprovals.assignAll(data);
      },
      failure: (failure) {
        approvalsLoadError.value = failure.message;
      },
    );
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
    final result = await _workforceMvpService.decideApproval(approvalId, approved: true);
    if (result is ApiSuccess<WorkforceApprovalDecision>) {
      pendingApprovals.removeWhere((item) => item.approvalId == approvalId);
      AppToast.success('Đã phê duyệt hành động của agent');
    }
  }

  Future<void> reject(String approvalId, {String? reason}) async {
    final result = await _workforceMvpService.decideApproval(
      approvalId,
      approved: false,
      reason: reason,
    );
    if (result is ApiSuccess<WorkforceApprovalDecision>) {
      pendingApprovals.removeWhere((item) => item.approvalId == approvalId);
      AppToast.warning(
        'Đã từ chối hành động của agent',
        title: 'Đã từ chối',
      );
    }
  }
}
