import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/controllers/mixins/portfolio_state_mixin.dart';
import 'package:frontend/modules/strategy/services/strategy_service.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _TestPortfolioController extends GetxController with PortfolioStateMixin {
  final StrategyService _strategyService = StrategyService();

  @override
  StrategyService get strategyService => _strategyService;

  @override
  final isSaving = false.obs;

  @override
  final errorMessage = RxnString();

  @override
  Future<void> runGuarded(Future<void> Function() action, {bool showSnackbar = false}) async {
    try {
      await action();
    } catch (e) {
      errorMessage.value = e.toString();
    }
  }
}

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

  group('PortfolioStateMixin', () {
    group('detectPortfolioNecessity', () {
      test('detects if portfolio is necessary', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('portfolio-necessity')) {
            return http.Response(
              jsonEncode({'required': true, 'reason': 'Multiple projects'}),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.detectPortfolioNecessity();

        expect(controller.portfolioDetection.value, isNotNull);
      });
    });

    group('loadPortfolios', () {
      test('loads portfolios', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/strategy/portfolios') {
            return http.Response(
              jsonEncode({
                'portfolios': [
                  {'id': 'port-1', 'name': 'Portfolio 1'},
                  {'id': 'port-2', 'name': 'Portfolio 2'},
                ]
              }),
              200,
            );
          }
          // Accept all other portfolio queries as success with empty results
          return http.Response(jsonEncode({'projects': [], 'matrix': [], 'tows': [], 'synergies': [], 'dependencies': [], 'options': [], 'cycles': []}), 200);
        });

        final controller = _TestPortfolioController();
        await controller.loadPortfolios();

        expect(controller.portfolios, hasLength(2));
      });
    });

    group('selectPortfolio', () {
      test('selects portfolio', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/strategy/portfolios/port-1/projects') {
            return http.Response(jsonEncode({'projects': [{'id': 'proj-1'}]}), 200);
          }
          // Accept all other portfolio queries
          return http.Response(jsonEncode({'matrix': [], 'tows': [], 'synergies': [], 'dependencies': [], 'options': [], 'cycles': []}), 200);
        });

        final controller = _TestPortfolioController();
        await controller.selectPortfolio('port-1');

        expect(controller.selectedPortfolioId.value, 'port-1');
      });
    });

    group('addProjectToPortfolio', () {
      testWidgets('adds project to portfolio', (tester) async {
        // Get.snackbar khi thành công cần overlay thật từ GetMaterialApp.
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('add-project') && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['project_id'], 'proj-1');
            expect(body['strategic_priority'], 'core');
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('portfolio-projects')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path.contains('impact-matrix')) {
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('tows')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path.contains('synergies')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path.contains('dependencies')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path.contains('options')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          if (request.url.path.contains('cycles')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.addProjectToPortfolio('port-1', projectId: 'proj-1');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
      });
    });

    group('loadPortfolioAdvancedData', () {
      test('loads TOWS, synergies, dependencies, and options', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/strategy/portfolios/port-1/tows') {
            // decodeList dùng key 'tows_options', không phải 'tows'.
            return http.Response(jsonEncode({'tows_options': [{'id': 'tow-1'}]}), 200);
          }
          if (request.url.path == '/strategy/portfolios/port-1/synergies') {
            return http.Response(jsonEncode({'synergies': [{'id': 'syn-1'}]}), 200);
          }
          if (request.url.path == '/strategy/portfolios/port-1/dependencies') {
            return http.Response(jsonEncode({'dependencies': [{'id': 'dep-1'}]}), 200);
          }
          if (request.url.path == '/strategy/portfolios/port-1/options') {
            return http.Response(jsonEncode({'options': [{'id': 'opt-1'}]}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.loadPortfolioAdvancedData('port-1');

        expect(controller.currentPortfolioTows, hasLength(1));
        expect(controller.currentPortfolioSynergies, hasLength(1));
        expect(controller.currentPortfolioDependencies, hasLength(1));
        expect(controller.currentPortfolioOptions, hasLength(1));
      });
    });

    group('addPortfolioTowsOption', () {
      testWidgets('adds TOWS option and reloads', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('tows') && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['quadrant'], 'SO');
            expect(body['title'], 'New option');
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('tows')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.addPortfolioTowsOption('port-1', quadrant: 'SO', title: 'New option');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
      });
    });

    group('addPortfolioSynergy', () {
      testWidgets('adds synergy between projects', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('synergies') && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['source_project_id'], 'proj-1');
            expect(body['target_project_id'], 'proj-2');
            expect(body['synergy_type'], 'revenue-sharing');
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('synergies')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.addPortfolioSynergy(
          'port-1',
          sourceProjectId: 'proj-1',
          targetProjectId: 'proj-2',
          synergyType: 'revenue-sharing',
          description: 'Share revenue',
        );
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
      });
    });

    group('deletePortfolioSynergy', () {
      testWidgets('deletes synergy', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('synergies') && request.method == 'DELETE') {
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('synergies')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.deletePortfolioSynergy('port-1', 'syn-1');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
      });
    });

    group('addPortfolioDependency', () {
      testWidgets('adds dependency between projects', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('dependencies') && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['predecessor_project_id'], 'proj-1');
            expect(body['successor_project_id'], 'proj-2');
            expect(body['dependency_type'], 'blocks');
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('dependencies')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.addPortfolioDependency(
          'port-1',
          predecessorProjectId: 'proj-1',
          successorProjectId: 'proj-2',
          dependencyType: 'blocks',
        );
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
      });
    });

    group('createPortfolioOption', () {
      testWidgets('creates portfolio option', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('options') && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['title'], 'New Option');
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('options')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.createPortfolioOption('port-1', title: 'New Option');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
      });
    });

    group('updatePortfolioOptionStatus', () {
      testWidgets('updates option status', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('options') && request.method == 'PUT') {
            final body = jsonDecode(request.body);
            expect(body['status'], 'approved');
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('options')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.updatePortfolioOptionStatus('port-1', 'opt-1', 'approved');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
      });
    });

    group('Founder Profile Methods', () {
      test('loadFounderProfile loads profile', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('founder-profile')) {
            return http.Response(
              jsonEncode({'id': 'founder-1', 'weekly_capacity_hours': 40}),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.loadFounderProfile();

        expect(controller.founderProfile.value, isNotNull);
      });

      testWidgets('updateFounderProfile updates profile', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('founder-profile') && request.method == 'PUT') {
            return http.Response(
              jsonEncode({'id': 'founder-1', 'weekly_capacity_hours': 50}),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.updateFounderProfile(weeklyCapacityHours: 50);
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
      });
    });

    group('Portfolio Cycle Methods', () {
      test('loadPortfolioCycles loads cycles', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/strategy/portfolios/port-1/cycles') {
            return http.Response(
              jsonEncode({'cycles': [{'id': 'cycle-1', 'title': 'Cycle 1'}]}),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.loadPortfolioCycles('port-1');

        expect(controller.currentPortfolioCycles, hasLength(1));
      });

      testWidgets('createPortfolioCycle creates new cycle', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('cycles') && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['title'], 'New Cycle');
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('cycles')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.createPortfolioCycle('port-1', title: 'New Cycle');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
      });
    });

    group('CEO Next Actions Methods', () {
      test('loadCeoNextActions loads actions', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/strategy/ceo/next-actions') {
            return http.Response(
              jsonEncode({'next_actions': [{'id': 'action-1', 'title': 'Action 1'}]}),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.loadCeoNextActions();

        expect(controller.ceoNextActions, hasLength(1));
      });

      testWidgets('updateNextActionStatus updates action status', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('next-actions') && request.method == 'PUT') {
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('next-actions')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.updateNextActionStatus('action-1', 'done');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
      });
    });

    group('Model Profile Methods', () {
      test('loadModelProfiles loads profiles', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/strategy/model-profiles') {
            return http.Response(
              jsonEncode({'profiles': [{'id': 'profile-1', 'display_name': 'GPT-4'}]}),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.loadModelProfiles();

        expect(controller.modelProfiles, hasLength(1));
      });

      testWidgets('updateModelProfile updates profile', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('model-profiles') && request.method == 'PUT') {
            return http.Response(jsonEncode({}), 200);
          }
          if (request.url.path.contains('model-profiles')) {
            return http.Response(jsonEncode({'items': []}), 200);
          }
          return http.Response('{}', 200);
        });

        final controller = _TestPortfolioController();
        await controller.updateModelProfile('profile-1', displayName: 'GPT-4 Turbo');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
      });
    });
  });
}
