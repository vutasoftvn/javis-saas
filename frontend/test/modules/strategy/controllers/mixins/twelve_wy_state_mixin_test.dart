import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/controllers/mixins/twelve_wy_state_mixin.dart';
import 'package:frontend/modules/strategy/services/strategy_service.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _TestTwelveWyController extends GetxController with TwelveWyStateMixin {
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
    ApiClient.client = realClient;
    Get.reset();
  });

  group('TwelveWyStateMixin', () {
    group('loadExecution', () {
      test('loads twelve week cycles, weekly plans, and commitments', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/execution/twelve-week-cycles') {
            return http.Response(
              jsonEncode({
                'cycles': [
                  {'id': 'cycle-1', 'week_no': 1},
                ]
              }),
              200,
            );
          }
          if (request.url.path == '/execution/weekly-plans') {
            return http.Response(
              jsonEncode({
                'plans': [
                  {'id': 'plan-1', 'week_no': 1},
                ]
              }),
              200,
            );
          }
          if (request.url.path == '/execution/weekly-commitments') {
            return http.Response(
              jsonEncode({
                'commitments': [
                  {'id': 'commit-1', 'weekly_plan_id': 'plan-1'},
                ]
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        });

        final controller = _TestTwelveWyController();
        await controller.loadExecution();

        expect(controller.twelveWeekCycles.value, hasLength(1));
        expect(controller.weeklyPlans.value, hasLength(1));
        expect(controller.weeklyCommitments.value, hasLength(1));
      });

      test('handles error in cycle loading', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/execution/twelve-week-cycles') {
            return http.Response('error', 500);
          }
          return http.Response(jsonEncode({'plans': [], 'commitments': []}), 200);
        });

        final controller = _TestTwelveWyController();
        await controller.loadExecution();

        expect(controller.twelveWeekCycles.value, isEmpty);
      });
    });

    group('getCommitmentsForPlan', () {
      test('returns commitments for specific plan', () {
        final controller = _TestTwelveWyController();
        controller.weeklyCommitments.value = [
          {'id': 'commit-1', 'weekly_plan_id': 'plan-1'},
          {'id': 'commit-2', 'weekly_plan_id': 'plan-1'},
          {'id': 'commit-3', 'weekly_plan_id': 'plan-2'},
        ];

        final commitments = controller.getCommitmentsForPlan('plan-1');

        expect(commitments, hasLength(2));
        expect(commitments.first['id'], 'commit-1');
      });

      test('returns empty list when no commitments match', () {
        final controller = _TestTwelveWyController();
        controller.weeklyCommitments.value = [
          {'id': 'commit-1', 'weekly_plan_id': 'plan-1'},
        ];

        final commitments = controller.getCommitmentsForPlan('plan-2');

        expect(commitments, isEmpty);
      });
    });

    group('createWeeklyPlan', () {
      test('creates weekly plan with focus', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/execution/weekly-plans' && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['week_no'], 1);
            expect(body['focus'], 'Build MVP');
            return http.Response(jsonEncode({}), 200);
          }
          return http.Response(
            jsonEncode({'cycles': [], 'plans': [], 'commitments': []}),
            200,
          );
        });

        final controller = _TestTwelveWyController();
        await controller.createWeeklyPlan(1, 'Build MVP');

        expect(controller.isSaving.value, false);
      });
    });

    group('createWeeklyCommitment', () {
      test('creates weekly commitment for plan', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/execution/weekly-commitments' && request.method == 'POST') {
            final body = jsonDecode(request.body);
            expect(body['weekly_plan_id'], 'plan-1');
            expect(body['title'], 'Code backend API');
            return http.Response(jsonEncode({}), 200);
          }
          return http.Response(
            jsonEncode({'cycles': [], 'plans': [], 'commitments': []}),
            200,
          );
        });

        final controller = _TestTwelveWyController();
        await controller.createWeeklyCommitment('plan-1', 'Code backend API');

        expect(controller.isSaving.value, false);
      });
    });

    group('toggleCommitmentStatus', () {
      test('toggles status from todo to done', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/execution/weekly-commitments/commit-1' && request.method == 'PUT') {
            final body = jsonDecode(request.body);
            expect(body['status'], 'done');
            return http.Response(jsonEncode({}), 200);
          }
          return http.Response(
            jsonEncode({'cycles': [], 'plans': [], 'commitments': []}),
            200,
          );
        });

        final controller = _TestTwelveWyController();
        await controller.toggleCommitmentStatus('commit-1', 'todo');

        expect(controller.isSaving.value, false);
      });

      test('toggles status from done to todo', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/execution/weekly-commitments/commit-1' && request.method == 'PUT') {
            final body = jsonDecode(request.body);
            expect(body['status'], 'todo');
            return http.Response(jsonEncode({}), 200);
          }
          return http.Response(
            jsonEncode({'cycles': [], 'plans': [], 'commitments': []}),
            200,
          );
        });

        final controller = _TestTwelveWyController();
        await controller.toggleCommitmentStatus('commit-1', 'done');

        expect(controller.isSaving.value, false);
      });
    });

    group('deleteWeeklyCommitment', () {
      test('deletes commitment', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/execution/weekly-commitments/commit-1' && request.method == 'DELETE') {
            return http.Response('{}', 200);
          }
          return http.Response(
            jsonEncode({'cycles': [], 'plans': [], 'commitments': []}),
            200,
          );
        });

        final controller = _TestTwelveWyController();
        await controller.deleteWeeklyCommitment('commit-1');

        expect(controller.isSaving.value, false);
      });
    });

    group('updateWeeklyMission', () {
      test('updates weekly mission with outcome score', () async {
        ApiClient.client = MockClient((request) async {
          if (request.url.path == '/execution/weekly-plans/plan-1/mission' && request.method == 'PUT') {
            final body = jsonDecode(request.body);
            expect(body['mission'], 'Complete API endpoints');
            expect(body['outcome_score'], 8.5);
            return http.Response(jsonEncode({}), 200);
          }
          return http.Response(
            jsonEncode({'cycles': [], 'plans': [], 'commitments': []}),
            200,
          );
        });

        final controller = _TestTwelveWyController();
        await controller.updateWeeklyMission('plan-1', mission: 'Complete API endpoints', outcomeScore: 8.5);

        expect(controller.isSaving.value, false);
      });
    });
  });
}
