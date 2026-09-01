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

  group('CanvasService - Canvas Management', () {
    test('getCanvases returns canvases list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/canvases');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'canvases': [
              {
                'id': 'canvas-1',
                'name': 'Business Model Canvas',
                'description': 'BMC for main product',
              },
            ],
          }),
          200,
        );
      });

      final result = await CanvasService().getCanvases();

      expect(result.items, hasLength(1));
      expect(result.items.first['name'], 'Business Model Canvas');
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNull);
    });

    test('getCanvases returns failure on 500', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final result = await CanvasService().getCanvases();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getCanvases returns failure on network error', () async {
      ApiClient.client = MockClient((_) async => throw const SocketException('offline'));

      final result = await CanvasService().getCanvases();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getCanvases returns failure when workspace_id missing', () async {
      SharedPreferences.setMockInitialValues({});

      final result = await CanvasService().getCanvases();

      expect(result.items, isEmpty);
      expect(result.errorMessage, contains('workspace'));
    });

    test('getCanvasDetail returns canvas details', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/canvases/canvas-1');
        return http.Response(
          jsonEncode({
            'id': 'canvas-1',
            'name': 'BMC',
            'description': 'Business Model Canvas',
            'sections': {},
          }),
          200,
        );
      });

      final result = await CanvasService().getCanvasDetail('canvas-1');

      expect(result['name'], 'BMC');
      expect(result.containsKey('sections'), true);
    });

    test('getCanvasDetail throws exception on error', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Canvas not found'}),
          404,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      expect(
        () => CanvasService().getCanvasDetail('canvas-1'),
        throwsA(isA<StrategyApiException>().having((e) => e.statusCode, 'statusCode', 404)),
      );
    });

    test('createCanvas posts name and description', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/canvases');
        final body = jsonDecode(request.body);
        expect(body['name'], 'New Canvas');
        expect(body['description'], 'Strategic canvas');
        return http.Response(
          jsonEncode({'id': 'canvas-2', 'name': 'New Canvas'}),
          201,
        );
      });

      final result = await CanvasService().createCanvas(
        'New Canvas',
        description: 'Strategic canvas',
      );

      expect(result['id'], 'canvas-2');
    });

    test('createCanvas posts only name if description is null', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body.containsKey('name'), true);
        expect(body.containsKey('description'), false);
        return http.Response(jsonEncode({'id': 'canvas-2'}), 201);
      });

      await CanvasService().createCanvas('Canvas Only');
    });

    test('updateCanvas puts name and description', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/strategy/canvases/canvas-1');
        final body = jsonDecode(request.body);
        expect(body['name'], 'Updated Canvas');
        return http.Response(
          jsonEncode({'id': 'canvas-1', 'name': 'Updated Canvas'}),
          200,
        );
      });

      final result = await CanvasService().updateCanvas('canvas-1', name: 'Updated Canvas');

      expect(result['name'], 'Updated Canvas');
    });

    test('deleteCanvas calls DELETE endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/strategy/canvases/canvas-1');
        return http.Response('', 204);
      });

      await CanvasService().deleteCanvas('canvas-1');
    });
  });

  group('CanvasService - AI Foundation Generation', () {
    test('generateAiFoundation posts generation request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/canvases/canvas-1/generate-ai-foundation');
        return http.Response(
          jsonEncode({
            'foundation': {
              'vision': 'Transform the industry',
              'mission': 'Build the best product',
            },
          }),
          200,
        );
      });

      final result = await CanvasService().generateAiFoundation('canvas-1');

      expect(result.containsKey('foundation'), true);
    });

    test('generateAiFoundation throws exception on error', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Unable to generate'}),
          500,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      expect(
        () => CanvasService().generateAiFoundation('canvas-1'),
        throwsA(isA<StrategyApiException>()),
      );
    });
  });

  group('CanvasService - Revisions', () {
    test('createRevision posts optional base_revision_id', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/canvases/canvas-1/revisions');
        final body = jsonDecode(request.body);
        expect(body['base_revision_id'], 'rev-1');
        return http.Response(
          jsonEncode({'id': 'rev-2', 'canvas_id': 'canvas-1'}),
          201,
        );
      });

      final result = await CanvasService().createRevision(
        'canvas-1',
        baseRevisionId: 'rev-1',
      );

      expect(result['id'], 'rev-2');
    });

    test('createRevision omits base_revision_id if null', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body.containsKey('base_revision_id'), false);
        return http.Response(jsonEncode({'id': 'rev-1'}), 201);
      });

      await CanvasService().createRevision('canvas-1');
    });

    test('getRevisionDetail returns revision data', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/strategy/revisions/rev-1');
        return http.Response(
          jsonEncode({'id': 'rev-1', 'status': 'draft', 'content': {}}),
          200,
        );
      });

      final result = await CanvasService().getRevisionDetail('rev-1');

      expect(result['id'], 'rev-1');
      expect(result['status'], 'draft');
    });

    test('submitReview posts review submission', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/revisions/rev-1/submit-review');
        return http.Response(
          jsonEncode({'id': 'rev-1', 'status': 'under_review'}),
          200,
        );
      });

      final result = await CanvasService().submitReview('rev-1');

      expect(result['status'], 'under_review');
    });

    test('approveRevision posts approval with optional note', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/revisions/rev-1/approve');
        final body = jsonDecode(request.body);
        expect(body['note'], 'Looks good!');
        return http.Response(
          jsonEncode({'id': 'rev-1', 'status': 'approved'}),
          200,
        );
      });

      final result = await CanvasService().approveRevision(
        'rev-1',
        note: 'Looks good!',
      );

      expect(result['status'], 'approved');
    });

    test('requestChanges posts rejection with reason', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/strategy/revisions/rev-1/request-changes');
        final body = jsonDecode(request.body);
        expect(body['reason'], 'Need clarification on mission');
        return http.Response(
          jsonEncode({'id': 'rev-1', 'status': 'changes_requested'}),
          200,
        );
      });

      final result = await CanvasService().requestChanges(
        'rev-1',
        'Need clarification on mission',
      );

      expect(result['status'], 'changes_requested');
    });
  });

  group('CanvasService - Foundation Editing', () {
    test('saveFoundation puts vision, mission, and values', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/strategy/revisions/rev-1/foundation');
        final body = jsonDecode(request.body);
        expect(body['vision'], 'Be the market leader');
        expect(body['mission'], 'Build innovative solutions');
        expect(body['values'], isA<List>());
        return http.Response(
          jsonEncode({
            'id': 'rev-1',
            'vision': 'Be the market leader',
            'mission': 'Build innovative solutions',
          }),
          200,
        );
      });

      final result = await CanvasService().saveFoundation(
        'rev-1',
        vision: 'Be the market leader',
        mission: 'Build innovative solutions',
        values: [
          {'name': 'Innovation', 'description': 'Continuous improvement'},
          {'name': 'Integrity', 'description': 'Honest dealings'},
        ],
      );

      expect(result['vision'], 'Be the market leader');
      expect(result['mission'], 'Build innovative solutions');
    });

    test('saveFoundation requires all three parameters', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body.containsKey('vision'), true);
        expect(body.containsKey('mission'), true);
        expect(body.containsKey('values'), true);
        return http.Response(jsonEncode({'id': 'rev-1'}), 200);
      });

      await CanvasService().saveFoundation(
        'rev-1',
        vision: 'Vision statement',
        mission: 'Mission statement',
        values: [],
      );
    });

    test('saveFoundation throws exception on error', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Validation failed'}),
          400,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      expect(
        () => CanvasService().saveFoundation(
          'rev-1',
          vision: 'Test',
          mission: 'Test',
          values: [],
        ),
        throwsA(isA<StrategyApiException>().having((e) => e.statusCode, 'statusCode', 400)),
      );
    });
  });

  group('CanvasService - Error Handling', () {
    test('createCanvas throws StrategyApiException on 409 duplicate', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Canvas with this name already exists'}),
          409,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      expect(
        () => CanvasService().createCanvas('Duplicate Name'),
        throwsA(
          isA<StrategyApiException>()
              .having((e) => e.statusCode, 'statusCode', 409)
              .having((e) => e.message, 'message', 'Canvas with this name already exists'),
        ),
      );
    });

    test('getCanvasDetail throws exception on 404', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Canvas not found'}),
          404,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      expect(
        () => CanvasService().getCanvasDetail('nonexistent'),
        throwsA(isA<StrategyApiException>()),
      );
    });

    test('decode falls back to status code message on malformed error', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('plain text error', 500);
      });

      expect(
        () => CanvasService().createCanvas('Test'),
        throwsA(isA<StrategyApiException>().having(
          (e) => e.message,
          'message',
          contains('500'),
        )),
      );
    });
  });
}
