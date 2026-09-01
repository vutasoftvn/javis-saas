import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/services/strategy_service_base.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class _TestStrategyService extends StrategyServiceBase {}

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

  group('StrategyServiceBase', () {
    group('getWorkspaceId', () {
      test('returns workspace_id from shared preferences', () async {
        final service = _TestStrategyService();
        final result = await service.getWorkspaceId();
        expect(result, 'workspace-1');
      });

      test('returns null when workspace_id is not set', () async {
        SharedPreferences.setMockInitialValues({});
        final service = _TestStrategyService();
        final result = await service.getWorkspaceId();
        expect(result, isNull);
      });
    });

    group('requireWorkspaceId', () {
      test('returns workspace_id when set', () async {
        final service = _TestStrategyService();
        final result = await service.requireWorkspaceId();
        expect(result, 'workspace-1');
      });

      test('throws StrategyApiException when workspace_id is missing', () async {
        SharedPreferences.setMockInitialValues({});
        final service = _TestStrategyService();
        expect(
          () => service.requireWorkspaceId(),
          throwsA(
            isA<StrategyApiException>()
                .having((e) => e.statusCode, 'statusCode', 0)
                .having((e) => e.message, 'message', contains('workspace')),
          ),
        );
      });
    });

    group('decode', () {
      test('decodes JSON response with 2xx status code', () {
        final service = _TestStrategyService();
        final response = http.Response(
          jsonEncode({'id': 'test-1', 'name': 'Test Item'}),
          200,
        );
        final result = service.decode(response);
        expect(result, isA<Map>());
        expect(result['id'], 'test-1');
        expect(result['name'], 'Test Item');
      });

      test('returns null for empty response body with 2xx status', () {
        final service = _TestStrategyService();
        final response = http.Response('', 200);
        final result = service.decode(response);
        expect(result, isNull);
      });

      test('throws StrategyApiException on error status with detail message', () {
        final service = _TestStrategyService();
        final response = http.Response(
          jsonEncode({'detail': 'Target not found'}),
          404,
        );
        expect(
          () => service.decode(response),
          throwsA(
            isA<StrategyApiException>()
                .having((e) => e.statusCode, 'statusCode', 404)
                .having((e) => e.message, 'message', contains('Target not found')),
          ),
        );
      });

      test('throws StrategyApiException on error status without detail message', () {
        final service = _TestStrategyService();
        final response = http.Response('server error', 500);
        expect(
          () => service.decode(response),
          throwsA(
            isA<StrategyApiException>()
                .having((e) => e.statusCode, 'statusCode', 500)
                .having((e) => e.message, 'message', contains('500')),
          ),
        );
      });

      test('throws StrategyApiException on error status with nested detail object', () {
        final service = _TestStrategyService();
        final response = http.Response(
          jsonEncode({'detail': {'message': 'Nested error'}}),
          409,
        );
        expect(
          () => service.decode(response),
          throwsA(
            isA<StrategyApiException>()
                .having((e) => e.statusCode, 'statusCode', 409)
                .having((e) => e.message, 'message', contains('message')),
          ),
        );
      });
    });

    group('decodeList', () {
      test('returns success with list of items when key exists', () {
        final service = _TestStrategyService();
        final response = http.Response(
          jsonEncode({
            'cycles': [
              {'id': '1', 'name': 'Cycle 1'},
              {'id': '2', 'name': 'Cycle 2'},
            ]
          }),
          200,
        );
        final result = service.decodeList(response, 'cycles');
        expect(result.items, hasLength(2));
        expect(result.items.first['id'], '1');
        expect(result.isFailure, isFalse);
        expect(result.isUnavailable, isFalse);
      });

      test('returns success with empty list for empty response body', () {
        final service = _TestStrategyService();
        final response = http.Response('', 200);
        final result = service.decodeList(response, 'cycles');
        expect(result.items, isEmpty);
        expect(result.isFailure, isFalse);
      });

      test('returns unavailable on 404 with optionalOn404=true', () {
        final service = _TestStrategyService();
        final response = http.Response('not found', 404);
        final result = service.decodeList(response, 'cycles', optionalOn404: true);
        expect(result.items, isEmpty);
        expect(result.isUnavailable, isTrue);
        expect(result.isFailure, isFalse);
      });

      test('returns failure on 404 with optionalOn404=false', () {
        final service = _TestStrategyService();
        final response = http.Response('not found', 404);
        final result = service.decodeList(response, 'cycles', optionalOn404: false);
        expect(result.items, isEmpty);
        expect(result.isUnavailable, isFalse);
        expect(result.errorMessage, contains('404'));
      });

      test('returns failure when response key is not a list', () {
        final service = _TestStrategyService();
        final response = http.Response(
          jsonEncode({'cycles': 'not a list'}),
          200,
        );
        final result = service.decodeList(response, 'cycles');
        expect(result.items, isEmpty);
        expect(result.isFailure, isTrue);
        expect(result.errorMessage, contains('định dạng'));
      });

      test('returns failure when response body is invalid JSON', () {
        final service = _TestStrategyService();
        final response = http.Response('invalid json', 200);
        final result = service.decodeList(response, 'cycles');
        expect(result.items, isEmpty);
        expect(result.isFailure, isTrue);
      });

      test('returns failure on server error', () {
        final service = _TestStrategyService();
        final response = http.Response('server error', 500);
        final result = service.decodeList(response, 'cycles');
        expect(result.items, isEmpty);
        expect(result.isFailure, isTrue);
        expect(result.errorMessage, contains('500'));
      });

      test('converts list items to Map<String, dynamic>', () {
        final service = _TestStrategyService();
        final response = http.Response(
          jsonEncode({
            'items': [
              {'id': 1, 'active': true},
            ]
          }),
          200,
        );
        final result = service.decodeList(response, 'items');
        expect(result.items.first, isA<Map<String, dynamic>>());
      });
    });
  });
}
