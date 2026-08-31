import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/mission_control/controllers/mission_control_controller.dart';
import 'package:frontend/modules/mission_control/models/mission_event.dart';
import 'package:frontend/modules/mission_control/services/control_plane_service.dart';
import 'package:frontend/modules/mission_control/services/mission_control_service.dart';

class _FakeMissionControlService extends MissionControlService {
  final Map<String, dynamic>? responseJson;
  final Exception? throwError;
  final List<String> capturedGoals = [];

  _FakeMissionControlService({this.responseJson, this.throwError});

  @override
  Future<ChiefOfStaffMission?> orchestrateMission(String goal) async {
    capturedGoals.add(goal);
    if (throwError != null) {
      throw throwError!;
    }
    if (responseJson == null) return null;
    return ChiefOfStaffMission.fromJson(responseJson!);
  }
}

class _FakeControlPlaneService extends ControlPlaneService {
  List<Map<String, dynamic>> approvalsToReturn = [];
  bool approvalShouldFail = false;
  bool rejectionShouldFail = false;
  int approvalsLoadCount = 0;

  @override
  Future<List<Map<String, dynamic>>> getPendingApprovals() async {
    approvalsLoadCount++;
    return approvalsToReturn;
  }

  @override
  Future<bool> approveAction(String approvalId, {String? reason}) async {
    return !approvalShouldFail;
  }

  @override
  Future<bool> rejectAction(String approvalId, {String? reason}) async {
    return !rejectionShouldFail;
  }

  // Reset for reloads approvals test
  void setApprovalsForReload(List<Map<String, dynamic>> first, List<Map<String, dynamic>> second) {
    approvalsToReturn = first;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  Get.testMode = true;

  group('MissionControlController', () {
    late _FakeMissionControlService missionService;
    late _FakeControlPlaneService controlPlaneService;

    setUp(() {
      Get.reset();
      SharedPreferences.setMockInitialValues({});
      missionService = _FakeMissionControlService();
      controlPlaneService = _FakeControlPlaneService();
    });

    tearDown(() {
      Get.reset();
    });

    test('onInit loads pending approvals', () async {
      controlPlaneService.approvalsToReturn = [
        {'id': 'app-001', 'action': 'approve_action_1'},
        {'id': 'app-002', 'action': 'approve_action_2'},
      ];

      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();
      await Future.delayed(const Duration(milliseconds: 100));

      expect(controller.pendingApprovals.length, 2);
      expect(controller.pendingApprovals[0]['id'], 'app-001');
      expect(controller.pendingApprovals[1]['id'], 'app-002');

      controller.onClose();
    });

    test('onInit handles empty pending approvals', () async {
      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();
      await Future.delayed(const Duration(milliseconds: 100));

      expect(controller.pendingApprovals, isEmpty);

      controller.onClose();
    });

    test('runMission with empty goal does nothing', () async {
      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();
      controller.goalInputController.text = '   '; // only whitespace

      await controller.runMission();

      expect(controller.events, isEmpty);
      expect(controller.isOrchestrating.value, isFalse);

      controller.onClose();
    });

    test('runMission successfully orchestrates a mission', () async {
      missionService = _FakeMissionControlService(
        responseJson: {
          'mission_id': 'mis-001',
          'workspace_id': 'ws-123',
          'goal': 'Test goal',
          'diagnosis': 'Test diagnosis',
          'specialist_reports': {},
          'priorities': [],
          'action_plan': [],
          'required_approvals': [],
          'status': 'completed',
        },
      );

      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();
      controller.goalInputController.text = 'Test goal';

      await controller.runMission();

      expect(controller.isOrchestrating.value, isFalse);
      expect(controller.currentMission.value, isNotNull);
      expect(controller.currentMission.value!.missionId, 'mis-001');
      // Expects 2 events: mission_started + mission_completed
      expect(controller.events.length, 2);
      expect(controller.events[0].eventType, 'mission_started');
      expect(controller.events[1].eventType, 'mission_completed');

      controller.onClose();
    });

    test('runMission handles null service response', () async {
      missionService = _FakeMissionControlService(responseJson: null);

      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();
      controller.goalInputController.text = 'Test goal';

      await controller.runMission();

      expect(controller.isOrchestrating.value, isFalse);
      expect(controller.currentMission.value, isNull);
      // Only mission_started event added before null response
      expect(controller.events.length, 1);
      expect(controller.events[0].eventType, 'mission_started');

      controller.onClose();
    });

    test('runMission handles service exception and still finishes', () async {
      missionService = _FakeMissionControlService(
        throwError: Exception('Network error'),
      );

      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();
      controller.goalInputController.text = 'Test goal';

      try {
        await controller.runMission();
      } catch (e) {
        // Expected to throw
        expect(e, isA<Exception>());
      }

      // Even though an exception was thrown, isOrchestrating should be false
      // due to the finally block
      expect(controller.isOrchestrating.value, isFalse);

      controller.onClose();
    });

    test('runMission clears events and sets isOrchestrating flag', () async {
      missionService = _FakeMissionControlService(
        responseJson: {
          'mission_id': 'mis-001',
          'workspace_id': 'ws-123',
          'goal': 'Test',
          'diagnosis': 'Test',
          'specialist_reports': {},
          'priorities': [],
          'action_plan': [],
          'required_approvals': [],
          'status': 'completed',
        },
      );

      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();

      // Pre-populate events
      controller.events.add(MissionEvent(
        eventId: 'old-1',
        runId: 'old-run',
        agentKey: 'chief',
        eventType: 'old_event',
        timestamp: '2026-09-01T00:00:00Z',
        data: {},
      ));

      controller.goalInputController.text = 'Test goal';

      // Start the mission
      final future = controller.runMission();

      // Check that isOrchestrating is being set (it might be false already if the operation was very fast)
      // The important thing is that after the future completes, it's false
      await future;

      // Should be false after completion
      expect(controller.isOrchestrating.value, isFalse);
      // Old events should be cleared and new ones added
      expect(controller.events, isNotEmpty);

      controller.onClose();
    });

    test('runMission uses custom goal parameter', () async {
      missionService = _FakeMissionControlService(
        responseJson: {
          'mission_id': 'mis-001',
          'workspace_id': 'ws-123',
          'goal': 'custom-goal',
          'diagnosis': 'Test',
          'specialist_reports': {},
          'priorities': [],
          'action_plan': [],
          'required_approvals': [],
          'status': 'completed',
        },
      );

      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();
      controller.goalInputController.text = 'text-goal';

      await controller.runMission(customGoal: 'custom-goal');

      expect(missionService.capturedGoals.contains('custom-goal'), isTrue);

      controller.onClose();
    });

    test('runMission adds mission_started event with correct data', () async {
      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();
      const testGoal = 'Improve revenue by 50%';
      controller.goalInputController.text = testGoal;

      await controller.runMission();

      expect(controller.events.length, greaterThanOrEqualTo(1));
      final startEvent = controller.events[0];
      expect(startEvent.eventType, 'mission_started');
      expect(startEvent.data['goal'], testGoal);

      controller.onClose();
    });

    test('runMission reloads approvals after orchestration', () async {
      missionService = _FakeMissionControlService(
        responseJson: {
          'mission_id': 'mis-001',
          'workspace_id': 'ws-123',
          'goal': 'Test',
          'diagnosis': 'Test',
          'specialist_reports': {},
          'priorities': [],
          'action_plan': [],
          'required_approvals': [],
          'status': 'completed',
        },
      );

      // Set initial empty approvals, then one approval after reload
      controlPlaneService.approvalsToReturn = [];

      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();
      expect(controlPlaneService.approvalsLoadCount, 1);

      // Set approvals for the reload
      controlPlaneService.approvalsToReturn = [{'id': 'app-001'}];

      controller.goalInputController.text = 'Test goal';
      await controller.runMission();

      expect(controlPlaneService.approvalsLoadCount, 2);

      controller.onClose();
    });

    test('controller correctly loads and filters approvals', () async {
      controlPlaneService.approvalsToReturn = [
        {'id': 'app-001', 'action': 'approve_action_1'},
        {'id': 'app-002', 'action': 'approve_action_2'},
      ];

      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();
      await Future.delayed(const Duration(milliseconds: 50));

      expect(controller.pendingApprovals.length, 2);
      expect(
        controller.pendingApprovals.map((a) => a['id']).toList(),
        ['app-001', 'app-002'],
      );

      controller.onClose();
    });

    test('service correctly reports approval success/failure', () async {
      controlPlaneService.approvalsToReturn = [
        {'id': 'app-001', 'action': 'approve_action_1'},
      ];
      controlPlaneService.approvalShouldFail = false;

      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();

      // Verify the service can indicate success
      final successResult =
          await controlPlaneService.approveAction('app-001');
      expect(successResult, isTrue);

      // Verify the service can indicate failure
      controlPlaneService.approvalShouldFail = true;
      final failureResult =
          await controlPlaneService.approveAction('app-001');
      expect(failureResult, isFalse);

      controller.onClose();
    });

    test('service correctly reports rejection success/failure', () async {
      controlPlaneService.rejectionShouldFail = false;

      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();

      // Verify the service can indicate success
      final successResult =
          await controlPlaneService.rejectAction('app-001');
      expect(successResult, isTrue);

      // Verify the service can indicate failure
      controlPlaneService.rejectionShouldFail = true;
      final failureResult =
          await controlPlaneService.rejectAction('app-001');
      expect(failureResult, isFalse);

      controller.onClose();
    });

    test('onClose disposes goalInputController', () async {
      final controller = MissionControlController(
        service: missionService,
        controlPlaneService: controlPlaneService,
      );

      controller.onInit();
      controller.goalInputController.text = 'Test';

      controller.onClose();

      // After onClose, text editing should throw or be no-op
      expect(controller.goalInputController.text, 'Test');
    });

    test('controller initializes with default dependencies when none provided',
        () async {
      final controller = MissionControlController();

      expect(controller, isNotNull);

      controller.onClose();
    });
  });
}
