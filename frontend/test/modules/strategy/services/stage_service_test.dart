import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/models/stage_model.dart';
import 'package:frontend/modules/strategy/services/stage_service.dart';
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

  group('StageService', () {
    group('listStagePolicies', () {
      test('returns stage policies list on success', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.path, '/operations/strategy/stage-policies');
          return http.Response(
            jsonEncode([
              {'stage': 'P0', 'name': 'Discovery'},
              {'stage': 'P1', 'name': 'Problem Validation'},
            ]),
            200,
          );
        });

        final result = await StageService().listStagePolicies();
        expect(result, hasLength(2));
        expect(result.first['stage'], 'P0');
      });

      test('handles response with policies key', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response(
            jsonEncode({
              'policies': [
                {'stage': 'P2', 'name': 'Solution Validation'},
              ]
            }),
            200,
          );
        });

        final result = await StageService().listStagePolicies();
        expect(result, hasLength(1));
        expect(result.first['stage'], 'P2');
      });

      test('includes query parameters when provided', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.queryParameters['workspaceId'], 'workspace-1');
          expect(request.url.queryParameters['stageKey'], 'P0');
          return http.Response(jsonEncode([]), 200);
        });

        await StageService().listStagePolicies(workspaceId: 'workspace-1', stageKey: 'P0');
      });

      test('returns empty list on error', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('server error', 500);
        });

        final result = await StageService().listStagePolicies();
        expect(result, isEmpty);
      });

      test('returns empty list on network error', () async {
        ApiClient.client = MockClient((_) async {
          throw const SocketException('offline');
        });

        final result = await StageService().listStagePolicies();
        expect(result, isEmpty);
      });
    });

    group('applyStageTransition', () {
      test('applies stage transition with required parameters', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/operations/strategy/projects/100/stage');
          final body = jsonDecode(request.body);
          expect(body['toStage'], 'P2');
          expect(body['reason'], isNotEmpty);
          return http.Response(
            jsonEncode({'id': 'transition-1', 'status': 'approved'}),
            200,
          );
        });

        final result = await StageService().applyStageTransition(
          projectId: 100,
          toStage: 'P2',
        );
        expect(result, isNotNull);
        expect(result!['id'], 'transition-1');
      });

      test('sends custom reason when provided', () async {
        ApiClient.client = MockClient((request) async {
          final body = jsonDecode(request.body);
          expect(body['reason'], 'Validation complete');
          return http.Response(jsonEncode({'id': 'transition-1'}), 201);
        });

        await StageService().applyStageTransition(
          projectId: 100,
          toStage: 'P2',
          reason: 'Validation complete',
        );
      });

      test('includes override approval ref when override is true', () async {
        ApiClient.client = MockClient((request) async {
          final body = jsonDecode(request.body);
          expect(body['override'], isTrue);
          expect(body['overrideApprovalRef'], 'approval-123');
          return http.Response(jsonEncode({'id': 'transition-1'}), 200);
        });

        await StageService().applyStageTransition(
          projectId: 100,
          toStage: 'P2',
          override: true,
          overrideApprovalRef: 'approval-123',
        );
      });

      test('converts projectId to string', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.path, '/operations/strategy/projects/200/stage');
          return http.Response(jsonEncode({'id': 'transition-1'}), 200);
        });

        await StageService().applyStageTransition(
          projectId: 200,
          toStage: 'P1',
        );
      });

      test('returns null on non-2xx status', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('error', 400);
        });

        final result = await StageService().applyStageTransition(
          projectId: 100,
          toStage: 'P1',
        );
        expect(result, isNull);
      });

      test('returns null on network error', () async {
        ApiClient.client = MockClient((_) async {
          throw const SocketException('offline');
        });

        final result = await StageService().applyStageTransition(
          projectId: 100,
          toStage: 'P1',
        );
        expect(result, isNull);
      });
    });

    group('listStageTransitions', () {
      test('returns list of transitions', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.path, '/operations/strategy/stage-transitions');
          return http.Response(
            jsonEncode([
              {'id': 't1', 'from_stage': 'P0', 'to_stage': 'P1'},
            ]),
            200,
          );
        });

        final result = await StageService().listStageTransitions();
        expect(result, hasLength(1));
        expect(result.first['id'], 't1');
      });

      test('handles response with transitions key', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response(
            jsonEncode({
              'transitions': [
                {'id': 't1', 'from_stage': 'P1', 'to_stage': 'P2'},
              ]
            }),
            200,
          );
        });

        final result = await StageService().listStageTransitions();
        expect(result, hasLength(1));
      });

      test('includes query parameters', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.queryParameters['workspaceId'], 'ws-1');
          expect(request.url.queryParameters['projectId'], 'proj-1');
          return http.Response(jsonEncode([]), 200);
        });

        await StageService().listStageTransitions(workspaceId: 'ws-1', projectId: 'proj-1');
      });

      test('returns empty list on error', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('error', 500);
        });

        final result = await StageService().listStageTransitions();
        expect(result, isEmpty);
      });
    });

    group('getStageContext', () {
      test('returns stage context on success', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.path, '/operations/strategy/stage-context');
          final body = jsonEncode({
            'workspace_id': 1,
            'company_stage': 'P2',
            'company_values': ['Innovation', 'Integrity'],
            'project_stage': 'P2_SOLUTION_VALIDATION',
            'critical_constraints': [],
            'exit_criteria': {},
            'stage_metadata': {},
            'stage': 'P2_SOLUTION_VALIDATION',
            'stage_name_vi': 'Policy',
            'code': 'P2',
            'primary_goal': 'Validate solution',
            'primary_questions': [],
            'required_entities': [],
            'primary_metrics': [],
            'deemphasized_tools': [],
            'recommended_methods': [],
            'optional_lenses': [],
            'priority_agents': [],
            'review_cadence': 'weekly',
          });
          return http.Response(body, 200);
        });

        final result = await StageService().getStageContext();
        expect(result, isNotNull);
        expect(result!.companyStage, 'P2');
      });

      test('includes projectId parameter when provided', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.queryParameters['projectId'], '100');
          final body = jsonEncode({
            'workspace_id': 1,
            'company_stage': 'P1',
            'company_values': [],
            'project_stage': 'P1_PROBLEM_VALIDATION',
            'critical_constraints': [],
            'exit_criteria': {},
            'stage_metadata': {},
            'stage': 'P1_PROBLEM_VALIDATION',
            'stage_name_vi': 'Policy',
            'code': 'P1',
            'primary_goal': 'Validate problem',
            'primary_questions': [],
            'required_entities': [],
            'primary_metrics': [],
            'deemphasized_tools': [],
            'recommended_methods': [],
            'optional_lenses': [],
            'priority_agents': [],
            'review_cadence': 'weekly',
          });
          return http.Response(body, 200);
        });

        await StageService().getStageContext(projectId: 100);
      });

      test('returns null on error', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('error', 500);
        });

        final result = await StageService().getStageContext();
        expect(result, isNull);
      });
    });

    group('getStagePolicy', () {
      test('returns stage policy on success', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.url.path, '/operations/strategy/stage-policies');
          expect(request.url.queryParameters['stageKey'], 'P2_SOLUTION_VALIDATION');
          final body = jsonEncode({
            'stage': 'P2_SOLUTION_VALIDATION',
            'stage_name_vi': 'Policy',
            'code': 'P2',
            'primary_goal': 'Validate solution',
            'primary_questions': [],
            'required_entities': [],
            'primary_metrics': [],
            'deemphasized_tools': [],
            'recommended_methods': [],
            'optional_lenses': [],
            'priority_agents': [],
            'review_cadence': 'weekly',
          });
          return http.Response(body, 200);
        });

        final result = await StageService().getStagePolicy(ProjectStage.p2SolutionValidation);
        expect(result, isNotNull);
        expect(result!.code, 'P2');
      });

      test('returns null on error', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('error', 404);
        });

        final result = await StageService().getStagePolicy(ProjectStage.p0Discovery);
        expect(result, isNull);
      });
    });

    group('listAllStages', () {
      test('delegates to listStagePolicies', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response(
            jsonEncode([
              {'stage': 'P0', 'name': 'Discovery'},
            ]),
            200,
          );
        });

        final result = await StageService().listAllStages();
        expect(result, hasLength(1));
      });
    });

    group('updateProjectStage', () {
      test('sends PATCH with all optional fields', () async {
        ApiClient.client = MockClient((request) async {
          expect(request.method, 'PATCH');
          expect(request.url.path, '/operations/strategy/projects/100/stage');
          final body = jsonDecode(request.body);
          expect(body['project_stage'], 'P2_SOLUTION_VALIDATION');
          expect(body['stage_goal'], 'MVP ready');
          expect(body['critical_constraints'], ['Budget']);
          expect(body['exit_criteria'], {'users': 100});
          expect(body['stage_metadata'], {'version': 1});
          final respBody = jsonEncode({
            'workspace_id': 1,
            'company_stage': 'P2',
            'company_values': [],
            'project_stage': 'P2_SOLUTION_VALIDATION',
            'critical_constraints': [],
            'exit_criteria': {},
            'stage_metadata': {},
            'stage': 'P2_SOLUTION_VALIDATION',
            'stage_name_vi': 'Policy',
            'code': 'P2',
            'primary_goal': 'Validate solution',
            'primary_questions': [],
            'required_entities': [],
            'primary_metrics': [],
            'deemphasized_tools': [],
            'recommended_methods': [],
            'optional_lenses': [],
            'priority_agents': [],
            'review_cadence': 'weekly',
          });
          return http.Response(respBody, 200);
        });

        final result = await StageService().updateProjectStage(
          100,
          projectStage: ProjectStage.p2SolutionValidation,
          stageGoal: 'MVP ready',
          criticalConstraints: ['Budget'],
          exitCriteria: {'users': 100},
          stageMetadata: {'version': 1},
        );
        expect(result, isNotNull);
      });

      test('returns null on error', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('error', 400);
        });

        final result = await StageService().updateProjectStage(100);
        expect(result, isNull);
      });
    });
  });
}
