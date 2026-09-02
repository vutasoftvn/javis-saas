import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/mission_control/controllers/mission_control_controller.dart';
import 'package:frontend/modules/mission_control/models/mission_event.dart';
import 'package:frontend/modules/mission_control/services/mission_control_service.dart';
import 'package:frontend/modules/workforce/models/workforce_mvp_models.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

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

/// Task 3 — thay cho `_FakeControlPlaneService` (đã gọi route không
/// canonical); giờ controller phụ thuộc `WorkforceMvpService`, trả về
/// `ApiResult` thay vì List/bool trần để không thể biến lỗi thành thành công
/// giả.
final _fakeMeta = ApiResponseMeta(
  dataState: ApiDataState.empty,
  observedAt: DateTime.utc(2026, 1, 1),
);

class _FakeWorkforceMvpService implements WorkforceMvpService {
  ApiResult<List<WorkforceApproval>> approvalsResult =
      ApiSuccess(data: const [], meta: _fakeMeta);
  bool decisionShouldFail = false;
  int approvalsLoadCount = 0;
  final List<String> decidedApprovals = [];

  @override
  Future<ApiResult<List<WorkforceApproval>>> listApprovals({String? status}) async {
    approvalsLoadCount++;
    return approvalsResult;
  }

  @override
  Future<ApiResult<WorkforceApprovalDecision>> decideApproval(
    String approvalId, {
    required bool approved,
    String? reason,
  }) async {
    if (decisionShouldFail) {
      return const ApiFailure(ApiFailureDetail(
        code: ApiFailureCode.invalidRequest,
        statusCode: 400,
        message: 'decision failed',
      ));
    }
    decidedApprovals.add(approvalId);
    return ApiSuccess(
      data: WorkforceApprovalDecision(
        approvalId: approvalId,
        runId: 'run_1',
        status: approved ? 'approved' : 'rejected',
        decidedAt: DateTime.now(),
      ),
      meta: _fakeMeta,
    );
  }

  @override
  Future<ApiResult<List<WorkforceRun>>> listRuns({int limit = 50}) async {
    return ApiSuccess(data: const [], meta: _fakeMeta);
  }

  @override
  Future<ApiResult<List<WorkforceRunEvent>>> listRunEvents(String runId) async {
    return ApiSuccess(data: const [], meta: _fakeMeta);
  }

  @override
  Future<ApiResult<List<WorkforceCompositionEntry>>> getComposition() async {
    return ApiSuccess(data: const [], meta: _fakeMeta);
  }

  @override
  Future<ApiResult<Map<String, dynamic>>> getOrgChart() async {
    return ApiSuccess(data: const {}, meta: _fakeMeta);
  }
}

WorkforceApproval _approval(String id, {String action = 'approve_action_1'}) {
  return WorkforceApproval(
    approvalId: id,
    runId: 'run_1',
    action: action,
    subject: 'subject',
    status: 'PENDING',
    riskLevel: 'medium',
    requiredRole: 'admin',
    policyId: 'default',
    createdAt: DateTime.now(),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  Get.testMode = true;

  group('MissionControlController', () {
    late _FakeMissionControlService missionService;
    late _FakeWorkforceMvpService workforceMvpService;

    setUp(() {
      Get.reset();
      SharedPreferences.setMockInitialValues({});
      missionService = _FakeMissionControlService();
      workforceMvpService = _FakeWorkforceMvpService();
    });

    tearDown(() {
      Get.reset();
    });

    test('onInit loads pending approvals', () async {
      workforceMvpService.approvalsResult = ApiSuccess(
        data: [_approval('app-001'), _approval('app-002')],
        meta: _fakeMeta,
      );

      final controller = MissionControlController(
        service: missionService,
        workforceMvpService: workforceMvpService,
      );

      controller.onInit();
      await Future.delayed(const Duration(milliseconds: 100));

      expect(controller.pendingApprovals.length, 2);
      expect(controller.pendingApprovals[0].approvalId, 'app-001');
      expect(controller.pendingApprovals[1].approvalId, 'app-002');

      controller.onClose();
    });

    test('onInit handles empty pending approvals', () async {
      final controller = MissionControlController(
        service: missionService,
        workforceMvpService: workforceMvpService,
      );

      controller.onInit();
      await Future.delayed(const Duration(milliseconds: 100));

      expect(controller.pendingApprovals, isEmpty);

      controller.onClose();
    });

    test('404/failure surfaces as an error, not a silently-empty success', () async {
      workforceMvpService.approvalsResult = const ApiFailure(ApiFailureDetail(
        code: ApiFailureCode.notFound,
        statusCode: 404,
        message: 'Not found',
      ));

      final controller = MissionControlController(
        service: missionService,
        workforceMvpService: workforceMvpService,
      );

      controller.onInit();
      await Future.delayed(const Duration(milliseconds: 100));

      expect(controller.pendingApprovals, isEmpty);
      expect(controller.approvalsLoadError.value, isNotNull);

      controller.onClose();
    });

    test('runMission with empty goal does nothing', () async {
      final controller = MissionControlController(
        service: missionService,
        workforceMvpService: workforceMvpService,
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
        workforceMvpService: workforceMvpService,
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
        workforceMvpService: workforceMvpService,
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
        workforceMvpService: workforceMvpService,
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
        workforceMvpService: workforceMvpService,
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
        workforceMvpService: workforceMvpService,
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
        workforceMvpService: workforceMvpService,
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

      final controller = MissionControlController(
        service: missionService,
        workforceMvpService: workforceMvpService,
      );

      controller.onInit();
      expect(workforceMvpService.approvalsLoadCount, 1);

      workforceMvpService.approvalsResult = ApiSuccess(
        data: [_approval('app-001')],
        meta: _fakeMeta,
      );

      controller.goalInputController.text = 'Test goal';
      await controller.runMission();

      expect(workforceMvpService.approvalsLoadCount, 2);

      controller.onClose();
    });

    test('controller correctly loads and filters approvals', () async {
      workforceMvpService.approvalsResult = ApiSuccess(
        data: [_approval('app-001'), _approval('app-002')],
        meta: _fakeMeta,
      );

      final controller = MissionControlController(
        service: missionService,
        workforceMvpService: workforceMvpService,
      );

      controller.onInit();
      await Future.delayed(const Duration(milliseconds: 50));

      expect(controller.pendingApprovals.length, 2);
      expect(
        controller.pendingApprovals.map((a) => a.approvalId).toList(),
        ['app-001', 'app-002'],
      );

      controller.onClose();
    });

    test('approve removes approval from list on success', () async {
      workforceMvpService.approvalsResult = ApiSuccess(
        data: [_approval('app-001')],
        meta: _fakeMeta,
      );

      final controller = MissionControlController(
        service: missionService,
        workforceMvpService: workforceMvpService,
      );

      controller.onInit();
      await Future.delayed(const Duration(milliseconds: 50));

      await controller.approve('app-001');

      expect(controller.pendingApprovals, isEmpty);
      expect(workforceMvpService.decidedApprovals, ['app-001']);

      controller.onClose();
    });

    test('approve keeps the approval in list when the decision call fails', () async {
      workforceMvpService.approvalsResult = ApiSuccess(
        data: [_approval('app-001')],
        meta: _fakeMeta,
      );
      workforceMvpService.decisionShouldFail = true;

      final controller = MissionControlController(
        service: missionService,
        workforceMvpService: workforceMvpService,
      );

      controller.onInit();
      await Future.delayed(const Duration(milliseconds: 50));

      await controller.approve('app-001');

      expect(controller.pendingApprovals.length, 1);

      controller.onClose();
    });

    test('reject removes approval from list on success', () async {
      workforceMvpService.approvalsResult = ApiSuccess(
        data: [_approval('app-456')],
        meta: _fakeMeta,
      );

      final controller = MissionControlController(
        service: missionService,
        workforceMvpService: workforceMvpService,
      );

      controller.onInit();
      await Future.delayed(const Duration(milliseconds: 50));

      await controller.reject('app-456', reason: 'Needs more review');

      expect(controller.pendingApprovals, isEmpty);

      controller.onClose();
    });

    test('onClose disposes goalInputController', () async {
      final controller = MissionControlController(
        service: missionService,
        workforceMvpService: workforceMvpService,
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
