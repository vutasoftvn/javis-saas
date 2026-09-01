import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/controllers/mixins/okr_state_mixin.dart';
import 'package:frontend/modules/strategy/services/strategy_service.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _TestOkrController extends GetxController with OkrStateMixin {
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

  group('OkrStateMixin', () {
    group('loadOkrs', () {
      test('loads OKR cycles, objectives, and key results', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/okrs/cycles') {
            return http.Response(
              jsonEncode({
                'cycles': [
                  {'id': 'cycle-1', 'name': 'Q1 2026'},
                ]
              }),
              200,
            );
          }
          if (request.url.path == '/okrs/objectives') {
            return http.Response(
              jsonEncode({
                'objectives': [
                  {'id': 'obj-1', 'title': 'Objective 1'},
                ]
              }),
              200,
            );
          }
          if (request.url.path == '/okrs/key-results') {
            return http.Response(
              jsonEncode({
                'key_results': [
                  {'id': 'kr-1', 'objective_id': 'obj-1'},
                ]
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = _TestOkrController();
        await controller.loadOkrs();

        expect(controller.okrCycles, hasLength(1));
        expect(controller.objectives, hasLength(1));
        expect(controller.keyResults, hasLength(1));
      });

      test('sets selectedCycleId to first cycle if not set', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/okrs/cycles') {
            return http.Response(
              jsonEncode({
                'cycles': [
                  {'id': 'cycle-1', 'name': 'Q1'},
                  {'id': 'cycle-2', 'name': 'Q2'},
                ]
              }),
              200,
            );
          }
          return http.Response(jsonEncode({'objectives': [], 'key_results': []}), 200);
        });

        final controller = _TestOkrController();
        await controller.loadOkrs();

        expect(controller.selectedCycleId.value, 'cycle-1');
      });

      test('does not override selectedCycleId if already set', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/okrs/cycles') {
            return http.Response(
              jsonEncode({
                'cycles': [
                  {'id': 'cycle-1', 'name': 'Q1'},
                  {'id': 'cycle-2', 'name': 'Q2'},
                ]
              }),
              200,
            );
          }
          return http.Response(jsonEncode({'objectives': [], 'key_results': []}), 200);
        });

        final controller = _TestOkrController();
        controller.selectedCycleId.value = 'cycle-2';
        await controller.loadOkrs();

        expect(controller.selectedCycleId.value, 'cycle-2');
      });
    });

    group('getKeyResultsForObjective', () {
      test('returns key results for specific objective', () {
        final controller = _TestOkrController();
        controller.keyResults.value = [
          {'id': 'kr-1', 'objective_id': 'obj-1'},
          {'id': 'kr-2', 'objective_id': 'obj-1'},
          {'id': 'kr-3', 'objective_id': 'obj-2'},
        ];

        final results = controller.getKeyResultsForObjective('obj-1');

        expect(results, hasLength(2));
        expect(results.first['id'], 'kr-1');
      });

      test('returns empty list when no key results match', () {
        final controller = _TestOkrController();
        controller.keyResults.value = [
          {'id': 'kr-1', 'objective_id': 'obj-1'},
        ];

        final results = controller.getKeyResultsForObjective('obj-2');

        expect(results, isEmpty);
      });
    });

    group('calculateObjectiveProgress', () {
      test('calculates average progress from key results', () {
        final controller = _TestOkrController();
        controller.keyResults.value = [
          {
            'id': 'kr-1',
            'objective_id': 'obj-1',
            'baseline_value': 0.0,
            'target_value': 100.0,
            'current_value': 50.0,
          },
          {
            'id': 'kr-2',
            'objective_id': 'obj-1',
            'baseline_value': 0.0,
            'target_value': 100.0,
            'current_value': 100.0,
          },
        ];

        final progress = controller.calculateObjectiveProgress('obj-1');

        expect(progress, closeTo(0.75, 0.01)); // (0.5 + 1.0) / 2 = 0.75
      });

      test('returns 0 when no key results', () {
        final controller = _TestOkrController();
        final progress = controller.calculateObjectiveProgress('obj-1');
        expect(progress, 0.0);
      });

      test('clamps progress to 0-1 range', () {
        final controller = _TestOkrController();
        controller.keyResults.value = [
          {
            'id': 'kr-1',
            'objective_id': 'obj-1',
            'baseline_value': 0.0,
            'target_value': 100.0,
            'current_value': 150.0, // Over 100%
          },
        ];

        final progress = controller.calculateObjectiveProgress('obj-1');

        expect(progress, closeTo(1.0, 0.01));
      });
    });

    group('toggleObjectiveExpanded', () {
      test('expands objective when not expanded', () {
        final controller = _TestOkrController();
        controller.expandedObjectiveId.value = null;

        controller.toggleObjectiveExpanded('obj-1');

        expect(controller.expandedObjectiveId.value, 'obj-1');
      });

      test('collapses objective when already expanded', () {
        final controller = _TestOkrController();
        controller.expandedObjectiveId.value = 'obj-1';

        controller.toggleObjectiveExpanded('obj-1');

        expect(controller.expandedObjectiveId.value, isNull);
      });

      test('switches to different objective', () {
        final controller = _TestOkrController();
        controller.expandedObjectiveId.value = 'obj-1';

        controller.toggleObjectiveExpanded('obj-2');

        expect(controller.expandedObjectiveId.value, 'obj-2');
      });
    });

    group('createObjective', () {
      testWidgets('creates objective', (tester) async {
        // Get.snackbar khi thành công cần overlay thật từ GetMaterialApp.
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({'cycles': [], 'objectives': [], 'key_results': []}), 200);
        });

        final controller = _TestOkrController();
        controller.selectedCycleId.value = 'cycle-1';
        await controller.createObjective('New Objective');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
        expect(controller.errorMessage.value, isNull);
      });
    });

    group('createKeyResult', () {
      testWidgets('creates key result', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({'cycles': [], 'objectives': [], 'key_results': []}), 200);
        });

        final controller = _TestOkrController();
        await controller.createKeyResult(
          objectiveId: 'obj-1',
          title: 'KR 1',
          baselineValue: 0,
          targetValue: 100,
          currentValue: 0,
          unit: 'units',
        );
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
        expect(controller.errorMessage.value, isNull);
      });
    });

    group('updateKeyResult', () {
      testWidgets('updates key result', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({'cycles': [], 'objectives': [], 'key_results': []}), 200);
        });

        final controller = _TestOkrController();
        await controller.updateKeyResult('kr-1', currentValue: 75);
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
        expect(controller.errorMessage.value, isNull);
      });
    });

    group('deleteKeyResult', () {
      testWidgets('deletes key result', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({'cycles': [], 'objectives': [], 'key_results': []}), 200);
        });

        final controller = _TestOkrController();
        await controller.deleteKeyResult('kr-1');
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
        expect(controller.errorMessage.value, isNull);
      });
    });

    group('checkinKeyResult', () {
      testWidgets('check-ins key result', (tester) async {
        await tester.pumpWidget(GetMaterialApp(home: Container()));

        ApiClient.client = MockClient((request) async {
          return http.Response(jsonEncode({'cycles': [], 'objectives': [], 'key_results': []}), 200);
        });

        final controller = _TestOkrController();
        await controller.checkinKeyResult('kr-1', 42.5);
        await tester.pump(const Duration(seconds: 4));

        expect(controller.isSaving.value, false);
        expect(controller.errorMessage.value, isNull);
      });
    });
  });
}
