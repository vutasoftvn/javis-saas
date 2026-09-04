import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/models/execution_plan_model.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';

http.Response _ok(Object body) => http.Response(
      jsonEncode(body),
      200,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _planJson({String status = 'draft', List<Map<String, dynamic>>? items}) {
  return {
    'id': 'plan-1',
    'projectId': 'proj-1',
    'weeklyPlanId': 'wp-1',
    'goalText': 'Chốt 3 phỏng vấn khách hàng',
    'status': status,
    'origin': 'command_center',
    'items': items ??
        [
          {
            'id': 'it-1',
            'title': 'Soạn SOP onboarding',
            'decisionReason': 'chuẩn hoá onboarding',
            'evidenceRefs': ['n1'],
            'ownerAgentProfile': 'operations',
            'expectedCapability': 'operations.sop.draft',
            'autonomyClass': 'AUTO',
            'autonomyClassSource': 'classifier_default',
            'priority': 'high',
            'dependsOnItemIds': <String>[],
            'status': 'proposed',
            'materializedTaskId': null,
          },
        ],
  };
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    Get.testMode = true;
    Get.reset();
    original = ApiClient.client;
  });
  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  test('ExecutionPlan.fromJson + canAccept', () {
    final p = ExecutionPlan.fromJson(_planJson());
    expect(p.items.single.autonomyClass, AutonomyClass.auto);
    expect(p.canAccept, isTrue);

    final missingEvidence = ExecutionPlan.fromJson(_planJson(items: [
      {
        'id': 'x',
        'title': 't',
        'decisionReason': 'r',
        'evidenceRefs': <String>[],
        'autonomyClass': 'NEEDS_APPROVAL',
        'autonomyClassSource': 'classifier_default',
        'priority': 'medium',
        'dependsOnItemIds': <String>[],
        'status': 'proposed',
      }
    ]));
    expect(missingEvidence.canAccept, isFalse);
  });

  test('unknown autonomyClass falls back to needsApproval', () {
    expect(autonomyClassFromString('WAT'), AutonomyClass.needsApproval);
  });

  test('requestDecomposition posts weekly-goal with triggerDecomposition', () async {
    final calls = <Map<String, dynamic>>[];
    ApiClient.client = MockClient((req) async {
      if (req.method == 'POST' &&
          req.url.path == '/operations/strategy/projects/proj-1/weekly-goal') {
        calls.add(jsonDecode(req.body) as Map<String, dynamic>);
        return _ok({'weeklyPlanId': 'wp-1', 'focus': 'x', 'decompositionRequested': true});
      }
      return http.Response('{}', 404);
    });

    final c = FounderCommandCenterController();
    c.activeProjectId.value = 'proj-1';
    await c.requestDecomposition('Chốt 3 phỏng vấn khách hàng');

    expect(calls, hasLength(1));
    expect(calls.single['triggerDecomposition'], isTrue);
    expect(calls.single['focus'], 'Chốt 3 phỏng vấn khách hàng');
    expect(c.isDecomposing.value, isFalse);
  });

  test('acceptPlan removes plan optimistically and reloads', () async {
    var listCalls = 0;
    ApiClient.client = MockClient((req) async {
      if (req.method == 'POST' &&
          req.url.path == '/operations/execution-plans/plan-1/accept') {
        return _ok({'planId': 'plan-1', 'taskIds': ['t1'], 'founderOnlyTaskIds': <String>[]});
      }
      if (req.method == 'GET' && req.url.path == '/operations/execution-plans') {
        listCalls++;
        return _ok({'plans': <dynamic>[]});
      }
      return http.Response('{}', 404);
    });

    final c = FounderCommandCenterController();
    c.activeProjectId.value = 'proj-1';
    c.draftPlans.add(ExecutionPlan.fromJson(_planJson()));

    await c.acceptPlan('plan-1');
    expect(c.draftPlans, isEmpty);
    expect(listCalls, 1);
  });

  test('updatePlanItem surfaces backend 403 and reloads', () async {
    ApiClient.client = MockClient((req) async {
      if (req.method == 'PATCH' &&
          req.url.path == '/operations/execution-plans/plan-1/items/it-1') {
        return http.Response('not allowed', 403);
      }
      if (req.method == 'GET' && req.url.path == '/operations/execution-plans') {
        return _ok({'plans': [_planJson()]});
      }
      return http.Response('{}', 404);
    });

    final c = FounderCommandCenterController();
    c.activeProjectId.value = 'proj-1';
    c.draftPlans.add(ExecutionPlan.fromJson(_planJson()));

    await c.updatePlanItem('plan-1', 'it-1', autonomyClass: AutonomyClass.auto);
    // reloaded from backend (still AUTO in fixture) — no throw
    expect(c.draftPlans, hasLength(1));
  });

  test('loadFounderInbox populates FOUNDER_ONLY + blocked tasks', () async {
    ApiClient.client = MockClient((req) async {
      if (req.method == 'GET' && req.url.path == '/operations/tasks/founder-inbox') {
        return _ok({
          'tasks': [
            {'taskId': '1', 'title': 'Phỏng vấn 3 khách hàng', 'status': 'todo', 'priority': 'high', 'reason': 'founder_only'},
            {'taskId': '2', 'title': 'Gửi email chào mừng', 'status': 'blocked', 'priority': 'medium', 'reason': 'blocked'},
          ]
        });
      }
      return http.Response('{}', 404);
    });
    final c = FounderCommandCenterController();
    c.activeProjectId.value = 'proj-1';
    await c.loadFounderInbox();
    expect(c.founderInboxTasks, hasLength(2));
    expect(c.founderInboxTasks.firstWhere((t) => t.taskId == '2').isBlocked, isTrue);
  });

  test('loadDraftPlans populates from backend', () async {
    ApiClient.client = MockClient((req) async {
      if (req.method == 'GET' && req.url.path == '/operations/execution-plans') {
        expect(req.url.queryParameters['status'], 'draft');
        return _ok({'plans': [_planJson()]});
      }
      return http.Response('{}', 404);
    });
    final c = FounderCommandCenterController();
    c.activeProjectId.value = 'proj-1';
    await c.loadDraftPlans();
    expect(c.draftPlans, hasLength(1));
    expect(c.draftPlans.single.goalText, contains('phỏng vấn'));
  });
}
