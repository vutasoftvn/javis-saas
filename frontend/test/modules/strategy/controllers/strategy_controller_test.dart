import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/controllers/strategy_controller.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
    // Get.testMode chặn snackbar/dialog thật sự cố tìm overlay context (không có trong unit test).
    Get.testMode = true;
  });

  tearDown(() {
    Get.closeAllSnackbars();
    ApiClient.client = realClient;
    Get.reset();
  });

  group('StrategyController', () {
    group('Initialization', () {
      test('initializes with default observable states', () {
        final controller = StrategyController();
        expect(controller.isLoading.value, false);
        expect(controller.isSaving.value, false);
        expect(controller.isGeneratingAi.value, false);
        expect(controller.errorMessage.value, isNull);
        expect(controller.projects, isEmpty);
        expect(controller.initiatives, isEmpty);
        expect(controller.activeProjectId.value, isNull);
      });
    });

    group('runGuarded', () {
      test('sets error message on exception', () async {
        final controller = StrategyController();
        await controller.runGuarded(() async {
          throw Exception('Test error');
        });

        expect(controller.errorMessage.value, contains('Test error'));
      });

      test('clears error message on success', () async {
        final controller = StrategyController();
        controller.errorMessage.value = 'Old error';

        await controller.runGuarded(() async {
          // No error
        });

        expect(controller.errorMessage.value, isNull);
      });
    });

    group('loadAllData', () {
      test('loads OKRs, execution, and projects concurrently', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/okrs/cycles') {
            return http.Response(jsonEncode({'cycles': []}), 200);
          }
          if (request.url.path == '/okrs/objectives') {
            return http.Response(jsonEncode({'objectives': []}), 200);
          }
          if (request.url.path == '/okrs/key-results') {
            return http.Response(jsonEncode({'key_results': []}), 200);
          }
          if (request.url.path == '/execution/twelve-week-cycles') {
            return http.Response(jsonEncode({'cycles': []}), 200);
          }
          if (request.url.path == '/execution/weekly-plans') {
            return http.Response(jsonEncode({'plans': []}), 200);
          }
          if (request.url.path == '/execution/weekly-commitments') {
            return http.Response(jsonEncode({'commitments': []}), 200);
          }
          if (request.url.path == '/strategy/projects') {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path == '/strategy/initiatives') {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path == '/strategy/portfolios') {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = StrategyController();
        await controller.loadAllData();

        expect(controller.isLoading.value, false);
      });

      test('sets isLoading to true then false', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({'cycles': [], 'items': []}), 200);
        });

        final controller = StrategyController();
        final loadingStates = <bool>[];
        controller.isLoading.listen((value) => loadingStates.add(value));

        await controller.loadAllData();

        expect(loadingStates.contains(true), isTrue);
        expect(controller.isLoading.value, false);
      });
    });

    group('loadProjects', () {
      test('loads projects and initiatives', () async {
        ApiClient.client = MockClient((request) async {
          // getProjects() gọi /operations/projects, decode key 'projects' — không phải
          // /strategy/projects với key 'items' (nhầm ở lần viết test trước).
          if (request.url.path == '/operations/projects') {
            return http.Response(
              jsonEncode({
                'projects': [
                  {'id': 'proj-1', 'title': 'Project 1'},
                ]
              }),
              200,
            );
          }
          if (request.url.path == '/strategy/initiatives') {
            return http.Response(
              jsonEncode({
                'initiatives': [
                  {'id': 'init-1', 'title': 'Initiative 1'},
                ]
              }),
              200,
            );
          }
          if (request.url.path == '/strategy/portfolios') {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path.contains('portfolio-necessity')) {
            return http.Response(jsonEncode({}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = StrategyController();
        await controller.loadProjects();

        expect(controller.projects, hasLength(1));
        expect(controller.initiatives, hasLength(1));
      });
    });

    group('createProject', () {
      testWidgets('creates project with all parameters', (tester) async {
        // createProject() luôn gọi Get.snackbar khi thành công (showSnackbar: true),
        // Get.snackbar cần overlay thật từ GetMaterialApp — không có thì null-check crash.
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/operations/projects' && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['title'], 'New Project');
            expect(body['description'], 'Test project');
            return http.Response(
              jsonEncode({'id': 'proj-1', 'title': 'New Project'}),
              200,
            );
          }
          if (request.url.path == '/operations/projects') {
            return http.Response(jsonEncode({'projects': []}), 200);
          }
          if (request.url.path == '/strategy/initiatives') {
            return http.Response(jsonEncode({'initiatives': []}), 200);
          }
          if (request.url.path == '/strategy/portfolios') {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path.contains('portfolio-necessity')) {
            return http.Response(jsonEncode({}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = StrategyController();
        final id = await controller.createProject(
          title: 'New Project',
          description: 'Test project',
        );
        await tester.pump(const Duration(seconds: 4));

        expect(id, 'proj-1');
        expect(controller.isSaving.value, false);
      });

      test('returns null on creation error', () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('error', 400);
        });

        final controller = StrategyController();
        final id = await controller.createProject(title: 'New Project');

        expect(id, isNull);
      });
    });

    group('deleteProject', () {
      test('deletes project and reloads list', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/strategy/projects/proj-1' && request.method == 'DELETE') {
            return http.Response('{}', 200);
          }
          if (request.url.path == '/strategy/projects') {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path == '/strategy/initiatives') {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path == '/strategy/portfolios') {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path.contains('portfolio-necessity')) {
            return http.Response(jsonEncode({}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = StrategyController();
        await controller.deleteProject('proj-1');

        expect(controller.isSaving.value, false);
      });
    });

    group('generateAiOkrs', () {
      test('generates OKRs with specified counts', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('okrs:generate') && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['objectives_count'], 3);
            expect(body['key_results_per_objective_count'], 4);
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path == '/okrs/cycles') {
            return http.Response(jsonEncode({'cycles': []}), 200);
          }
          if (request.url.path == '/okrs/objectives') {
            return http.Response(jsonEncode({'objectives': []}), 200);
          }
          if (request.url.path == '/okrs/key-results') {
            return http.Response(jsonEncode({'key_results': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = StrategyController();
        await controller.generateAiOkrs(
          objectivesCount: 3,
          krsPerObjectiveCount: 4,
        );

        expect(controller.isGeneratingAi.value, false);
      });
    });

    group('Mixin Integration', () {
      test('controller has access to OKR mixin state', () {
        final controller = StrategyController();
        expect(controller.okrCycles, isNotNull);
        expect(controller.objectives, isNotNull);
        expect(controller.keyResults, isNotNull);
      });

      test('controller has access to twelve week mixin state', () {
        final controller = StrategyController();
        expect(controller.twelveWeekCycles, isNotNull);
        expect(controller.weeklyPlans, isNotNull);
        expect(controller.weeklyCommitments, isNotNull);
      });

      test('controller has access to governance mixin state', () {
        final controller = StrategyController();
        expect(controller.cycleStages, isNotNull);
        expect(controller.milestones, isNotNull);
        expect(controller.cycleContract, isNotNull);
      });

      test('controller has access to portfolio mixin state', () {
        final controller = StrategyController();
        expect(controller.portfolios, isNotNull);
        expect(controller.selectedPortfolioId, isNotNull);
        expect(controller.currentPortfolioProjects, isNotNull);
      });
    });
  });
}
