import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/controllers/mixins/governance_state_mixin.dart';
import 'package:frontend/modules/strategy/services/strategy_service.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _TestGovernanceController extends GetxController with GovernanceStateMixin {
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

  @override
  Future<void> loadProjects() async {
    // Mock implementation
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

  group('GovernanceStateMixin', () {
    group('loadCycleGovernance', () {
      test('loads cycle governance data', () async {
        ApiClient.client = MockClient((request) async {
          // Accept all requests
          return http.Response(
            jsonEncode({
              'stages': [{'id': 'stage-1'}],
              'milestones': [{'id': 'ms-1'}],
              'gate_decisions': [{'id': 'gd-1'}],
              'items': [{'id': 'stage-1'}],
              'id': 'contract-1',
            }),
            200,
          );
        });

        final controller = _TestGovernanceController();
        await controller.loadCycleGovernance('cycle-1');

        expect(controller.cycleStages, hasLength(1));
        expect(controller.milestones, hasLength(1));
        expect(controller.cycleContract.value, isNotNull);
        expect(controller.gateDecisions, hasLength(1));
      });
    });

    group('generateStandardStages', () {
      testWidgets('generates standard stages', (tester) async {
        // Get.snackbar khi thành công cần overlay thật từ GetMaterialApp.
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({'items': [{'id': 'stage-1'}]}), 200);
        });

        final controller = _TestGovernanceController();
        await controller.generateStandardStages('cycle-1');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.cycleStages, hasLength(1));
        expect(controller.isSaving.value, false);
      });
    });

    group('saveCycleContract', () {
      testWidgets('saves cycle contract', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({'id': 'contract-1'}), 200);
        });

        final controller = _TestGovernanceController();
        await controller.saveCycleContract(
          cycleId: 'cycle-1',
          successDefinition: 'Reach 1000 users',
        );
        await tester.pump(const Duration(seconds: 4));

        expect(controller.cycleContract.value, isNotNull);
        expect(controller.cycleContract.value!['id'], 'contract-1');
        expect(controller.isSaving.value, false);
      });
    });

    group('upsertCycleContract', () {
      testWidgets('upserts cycle contract', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({'id': 'contract-1'}), 200);
        });

        final controller = _TestGovernanceController();
        await controller.upsertCycleContract(
          'cycle-1',
          successDefinition: 'Test definition',
          founderCapacityPerWeek: 40,
          reservedBufferPercent: 15,
        );
        await tester.pump(const Duration(seconds: 4));

        expect(controller.cycleContract.value, isNotNull);
        expect(controller.cycleContract.value!['id'], 'contract-1');
      });
    });

    group('loadCycleCompilationStatus', () {
      test('loads compilation status for cycle', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('compilation-status')) {
            return http.Response(
              jsonEncode({'id': 'cycle-1', 'status': 'ready'}),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = _TestGovernanceController();
        await controller.loadCycleCompilationStatus('cycle-1');

        expect(controller.cycleCompilationStatus.value, isNotNull);
      });
    });

    group('compileCycle', () {
      testWidgets('compiles cycle', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({'id': 'cycle-1', 'status': 'compiled'}), 200);
        });

        final controller = _TestGovernanceController();
        await controller.compileCycle('cycle-1');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.cycleCompilationStatus.value, isNotNull);
        expect(controller.cycleCompilationStatus.value!['status'], 'compiled');
        expect(controller.isSaving.value, false);
      });
    });

    group('compileWeeklyPlan', () {
      testWidgets('compiles weekly plan', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({}), 200);
        });

        final controller = _TestGovernanceController();
        await controller.compileWeeklyPlan('plan-1');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
        expect(controller.errorMessage.value, isNull);
      });
    });

    group('createWeeklyReview', () {
      testWidgets('creates weekly review', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({}), 200);
        });

        final controller = _TestGovernanceController();
        await controller.createWeeklyReview(
          'cycle-1',
          weeklyPlanId: 'plan-1',
          executionScore: 8.5,
          outcomeScore: 7.5,
        );
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
        expect(controller.errorMessage.value, isNull);
      });
    });

    group('loadWeek13Readiness', () {
      test('loads week 13 readiness status', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('week-13-readiness')) {
            return http.Response(
              jsonEncode({'id': 'cycle-1', 'status': 'ready'}),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = _TestGovernanceController();
        await controller.loadWeek13Readiness('cycle-1');

        expect(controller.week13Readiness.value, isNotNull);
      });
    });

    group('finalizeWeek13', () {
      testWidgets('finalizes week 13', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({}), 200);
        });

        final controller = _TestGovernanceController();
        await controller.finalizeWeek13(
          'cycle-1',
          overallExecutionScore: 8.0,
          overallOutcomeScore: 7.5,
          okrAchievementRate: 0.85,
          celebrationTitle: 'Great cycle!',
        );
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
        expect(controller.errorMessage.value, isNull);
      });
    });
  });
}
