import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/strategy_service.dart';
import 'package:frontend/modules/strategy/controllers/project_orchestration_controller.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  test('generating a roadmap draft does not activate a stage', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/api/v1/strategy/projects/100/mvp-roadmap:generate');
      return http.Response(
        jsonEncode({
          'stages': [
            {'title': 'Validate demand', 'hypothesis': 'SMEs will pre-commit', 'scope': ['interview'], 'exit_criteria': ['10 LOIs']},
            {'title': 'Build MVP', 'hypothesis': 'A thin slice converts pilots', 'scope': ['ship core'], 'exit_criteria': ['3 pilots']},
            {'title': 'Scale acquisition', 'hypothesis': 'Paid channels compound', 'scope': ['run ads'], 'exit_criteria': ['CAC under target']},
          ],
        }),
        200,
      );
    });

    final controller = ProjectOrchestrationController(service: StrategyService());
    await controller.generateRoadmap('100');

    expect(controller.roadmapDraft.value?['stages'], hasLength(3));
    expect(controller.activeStage.value, isNull);
    expect(controller.stages, isEmpty);
  });

  test('confirming a roadmap populates stages but never sets an active stage', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'stages': [
            {'id': 's1', 'sequence_no': 1, 'title': 'Stage 1', 'status': 'CONFIRMED'},
            {'id': 's2', 'sequence_no': 2, 'title': 'Stage 2', 'status': 'CONFIRMED'},
          ],
        }),
        200,
      );
    });

    final controller = ProjectOrchestrationController(service: StrategyService());
    await controller.confirmRoadmap('100');

    expect(controller.stages, hasLength(2));
    expect(controller.stages.every((s) => s['status'] == 'CONFIRMED'), isTrue);
    expect(controller.activeStage.value, isNull);
  });

  test('activateStage requires a planned stage before calling the API', () async {
    var requestCount = 0;
    ApiClient.client = MockClient((request) async {
      requestCount++;
      return http.Response('{}', 200);
    });

    final controller = ProjectOrchestrationController(service: StrategyService());
    await controller.activateStage('100', 's1');

    expect(requestCount, 0);
    expect(controller.errorMessage.value, isNotNull);
  });

  test('activateStage sends the approved plan and sets activeStage on success', () async {
    ApiClient.client = MockClient((request) async {
      if (request.url.path.endsWith(':plan')) {
        return http.Response(
          jsonEncode({
            'objectives': [
              {'title': 'Validate demand', 'key_results': [
                {'title': '10 LOIs'},
                {'title': '20 interviews'},
              ]},
            ],
            'weekly_focus': List.generate(12, (i) => 'Week ${i + 1}'),
          }),
          200,
        );
      }
      expect(request.url.path, '/api/v1/strategy/projects/100/stages/s1:activate');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['weekly_focus'], hasLength(12));
      return http.Response(
        jsonEncode({
          'stage': {'id': 's1', 'status': 'ACTIVE', 'title': 'Stage 1'},
          'okr_cycle_id': 'cycle-1',
          'weekly_plan_count': 12,
        }),
        200,
      );
    });

    final controller = ProjectOrchestrationController(service: StrategyService());
    await controller.planStage('100', 's1');
    await controller.activateStage('100', 's1');

    expect(controller.activeStage.value?['status'], 'ACTIVE');
  });

  test('a service assessment requiring professional review is surfaced to the founder', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'assessments': [
            {
              'id': 'a1',
              'disposition': 'REQUIRED',
              'reason': 'Regulated domain',
              'risk_level': 'REGULATED',
              'execution_mode': 'MANUAL',
              'professional_review_required': true,
              'status': 'DRAFT',
            },
          ],
        }),
        200,
      );
    });

    final controller = ProjectOrchestrationController(service: StrategyService());
    await controller.generateServiceAssessment('100', 's1');

    expect(controller.serviceAssessments, hasLength(1));
    expect(controller.serviceAssessments.first['professional_review_required'], isTrue);
  });

  test('loadStages fetches existing stages and sets active stage if present', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/api/v1/strategy/projects/100/stages');
      return http.Response(
        jsonEncode({
          'stages': [
            {'id': 's1', 'sequence_no': 1, 'title': 'Stage 1', 'status': 'ACTIVE'},
            {'id': 's2', 'sequence_no': 2, 'title': 'Stage 2', 'status': 'CONFIRMED'},
          ],
        }),
        200,
      );
    });

    final controller = ProjectOrchestrationController(service: StrategyService());
    await controller.loadStages('100');

    expect(controller.stages, hasLength(2));
    expect(controller.stages.first['title'], 'Stage 1');
    expect(controller.activeStage.value?['id'], 's1');
  });
}
