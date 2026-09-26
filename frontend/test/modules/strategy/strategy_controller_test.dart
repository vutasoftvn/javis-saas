// Task 7 (PHẠM VI MỞ RỘNG 2026-09-14) — chứng minh StrategyController thật
// sự gọi đúng OkrService methods qua ApiClient (không mock OkrService, mock
// ở tầng http như okr_service_test.dart để test cả path parse JSON→MvpObjective).
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/controllers/strategy_controller.dart';
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

  group('loadObjectives', () {
    test('calls GET /operations/objectives and parses into MvpObjective list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'GET');
        if (request.url.path == '/operations/key-results') {
          return http.Response(
            jsonEncode({
              'key_results': [
                {'id': 'kr-1', 'objectiveId': 'obj-1', 'title': 'MRR 100tr', 'targetValue': 100},
              ],
            }),
            200,
          );
        }
        expect(request.url.path, '/operations/objectives');
        return http.Response(
          jsonEncode({
            'objectives': [
              {
                'id': 'obj-1',
                'workspaceId': 'workspace-1',
                'cycleId': 'cycle-1',
                'title': 'Grow revenue',
                'status': 'draft',
                'projectIds': [],
                'createdAt': '2026-09-14T00:00:00Z',
              },
            ],
          }),
          200,
        );
      });

      final controller = StrategyController();
      await controller.loadObjectives();

      expect(controller.isLoading.value, isFalse);
      expect(controller.errorMessage.value, isNull);
      expect(controller.objectives.length, 1);
      expect(controller.objectives.single.id, 'obj-1');
      expect(controller.objectives.single.status, 'draft');
      expect(controller.keyResultsByObjective['obj-1']?.single['id'], 'kr-1');
    });

    test('sets errorMessage when the request fails', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('boom', 500);
      });

      final controller = StrategyController();
      await controller.loadObjectives();

      expect(controller.objectives, isEmpty);
      expect(controller.errorMessage.value, isNotNull);
    });
  });

  group('publish', () {
    test('calls POST /operations/objectives/:id/publish then refreshes the list', () async {
      var publishCalled = false;
      var reloadCalled = false;

      ApiClient.client = MockClient((request) async {
        if (request.method == 'POST' && request.url.path == '/operations/objectives/obj-1/publish') {
          publishCalled = true;
          return http.Response(jsonEncode({'id': 'obj-1', 'status': 'published'}), 200);
        }
        if (request.method == 'GET' && request.url.path == '/operations/objectives') {
          reloadCalled = true;
          return http.Response(jsonEncode({'objectives': []}), 200);
        }
        return http.Response('unexpected', 404);
      });

      final controller = StrategyController();
      await controller.publish('obj-1');

      expect(publishCalled, isTrue);
      expect(reloadCalled, isTrue);
    });

    test('propagates the error when publish fails, without swallowing it', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('nope', 409);
      });

      final controller = StrategyController();

      expect(() => controller.publish('obj-1'), throwsA(anything));
    });
  });

  group('createObjective', () {
    test('gửi workspaceId + projectId của Project đang chọn rồi tải lại', () async {
      Map<String, dynamic>? createdBody;
      ApiClient.client = MockClient((request) async {
        if (request.method == 'POST' && request.url.path == '/operations/objectives') {
          createdBody = jsonDecode(request.body) as Map<String, dynamic>;
          return http.Response(jsonEncode({'id': 'obj-9'}), 201);
        }
        return http.Response(jsonEncode({'objectives': [], 'key_results': []}), 200);
      });

      final controller = StrategyController(activeProjectResolver: () async => 'proj-7');
      await controller.createObjective(title: 'Có 10 khách trả tiền', why: '  ');

      expect(createdBody?['projectId'], 'proj-7');
      expect(createdBody?['title'], 'Có 10 khách trả tiền');
      expect(createdBody?.containsKey('why'), isFalse);
    });

    test('không có Project đang chọn -> báo lỗi, không gọi API', () async {
      var called = false;
      ApiClient.client = MockClient((request) async {
        called = true;
        return http.Response('{}', 200);
      });

      final controller = StrategyController(activeProjectResolver: () async => null);

      await expectLater(controller.createObjective(title: 'X'), throwsStateError);
      expect(called, isFalse);
    });
  });
}
