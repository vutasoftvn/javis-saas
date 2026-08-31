import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/services/strategy_service.dart';
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

  group('canvases', () {
    test('getCanvases returns the canvases list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/canvases');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'canvases': [
              {'id': 'canvas-1', 'name': 'Q1 Strategy'},
            ],
          }),
          200,
        );
      });

      final result = await StrategyService().getCanvases();

      expect(result.items, hasLength(1));
      expect(result.items.first['name'], 'Q1 Strategy');
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNull);
    });

    // Trước đây 404/500/lỗi mạng đều bị `_decodeList` gộp thành `[]`, khiến
    // UI không phân biệt được "chưa có canvas" với "gọi API thất bại". Giờ
    // getCanvases() trả StrategyListResult để expose đúng 3 trạng thái.
    test('getCanvases exposes a failure with a message on a 500', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final result = await StrategyService().getCanvases();

      expect(result.items, isEmpty);
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNotEmpty);
    });

    // Không có endpoint list nào trong service này được xác nhận là "optional
    // theo thiết kế" (xem strategy_list_result.dart) — nên một 404 trên
    // canvases vẫn là lỗi thật (failure), không phải unavailable.
    test('getCanvases exposes a failure (not unavailable) on a 404', () async {
      ApiClient.client = MockClient((request) async => http.Response('missing', 404));

      final result = await StrategyService().getCanvases();

      expect(result.items, isEmpty);
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getCanvases exposes a failure on malformed JSON', () async {
      ApiClient.client = MockClient(
        (request) async => http.Response('not json', 200, headers: {'content-type': 'application/json'}),
      );

      final result = await StrategyService().getCanvases();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getCanvases exposes a failure with a message on a transport error', () async {
      ApiClient.client = MockClient((_) async => throw const SocketException('offline'));

      final result = await StrategyService().getCanvases();

      expect(result.items, isEmpty);
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNotEmpty);
    });

    test('createCanvas posts name/description and decodes the created canvas', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/canvases');
        expect(jsonDecode(request.body), {'name': 'New Canvas', 'description': 'desc'});
        return http.Response(jsonEncode({'id': 'canvas-2', 'name': 'New Canvas'}), 200);
      });

      final canvas = await StrategyService().createCanvas('New Canvas', description: 'desc');

      expect(canvas['id'], 'canvas-2');
    });

    test('createCanvas throws StrategyApiException with the backend detail on failure', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Tên canvas đã tồn tại'}),
          409,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      expect(
        () => StrategyService().createCanvas('Dup'),
        throwsA(
          isA<StrategyApiException>()
              .having((e) => e.statusCode, 'statusCode', 409)
              .having((e) => e.message, 'message', 'Tên canvas đã tồn tại'),
        ),
      );
    });

    test('getCanvasDetail throws when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      expect(
        () => StrategyService().getCanvasDetail('canvas-1'),
        throwsA(isA<StrategyApiException>()),
      );
    });
  });

  group('revisions', () {
    test('approveRevision posts an optional note', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/revisions/rev-1/approve');
        expect(jsonDecode(request.body), {'note': 'looks good'});
        return http.Response(jsonEncode({'id': 'rev-1', 'status': 'approved'}), 200);
      });

      final rev = await StrategyService().approveRevision('rev-1', note: 'looks good');

      expect(rev['status'], 'approved');
    });
  });

  group('OKRs', () {
    test('getObjectives filters by cycle when provided', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.query, 'workspace_id=workspace-1&cycle_id=cycle-1');
        return http.Response(jsonEncode({'objectives': []}), 200);
      });

      await StrategyService().getObjectives(cycleId: 'cycle-1');
    });

    test('createKeyResult fills in numeric defaults', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['baseline_value'], 0.0);
        expect(body['target_value'], 100.0);
        expect(body['unit'], '%');
        return http.Response(jsonEncode({'id': 'kr-1'}), 200);
      });

      await StrategyService().createKeyResult(objectiveId: 'obj-1');
    });
  });

  group('projects', () {
    test('getProjects preserves a network failure instead of an empty success', () async {
      ApiClient.client = MockClient((request) async => throw Exception('network down'));

      final result = await StrategyService().getProjects();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getProjects exposes a failure on a 403', () async {
      ApiClient.client = MockClient(
        (request) async => http.Response(
          jsonEncode({'detail': 'Không có quyền'}),
          403,
          headers: {'content-type': 'application/json; charset=utf-8'},
        ),
      );

      final result = await StrategyService().getProjects();

      expect(result.items, isEmpty);
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, 'Không có quyền');
    });

    test('deleteProject calls DELETE on the project endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/operations/projects/project-1');
        return http.Response('', 204);
      });

      await StrategyService().deleteProject('project-1');
    });

    test('createProject calls POST on the operations projects endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/projects');
        final body = jsonDecode(request.body);
        expect(body['title'], 'Test Project');
        expect(body['lifecycleStage'], 'P1_PROBLEM_VALIDATION');
        return http.Response(jsonEncode({'id': 'proj-123', 'title': 'Test Project'}), 200);
      });

      final res = await StrategyService().createProject(
        title: 'Test Project',
        projectStage: 'P1_PROBLEM_VALIDATION',
      );
      expect(res['id'], 'proj-123');
    });
  });
}
