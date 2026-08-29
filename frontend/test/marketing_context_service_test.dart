import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/marketing/services/marketing_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test-token-jwt',
      'workspace_id': '351550739880456242',
    });
  });

  tearDown(() {
    ApiClient.client = http.Client();
  });

  group('ApiClient Endpoint Normalization for Marketing Context', () {
    test('normalizes /marketing/context to /commercial/marketing-context', () {
      final uri1 = ApiClient.resolveUri('/marketing/context');
      expect(uri1.path, '/commercial/marketing-context');

      final uri2 = ApiClient.resolveUri('/marketing/context/product-marketing');
      expect(uri2.path, '/commercial/marketing-context/product-marketing');

      final uri3 = ApiClient.resolveUri('/api/v1/marketing/context/customer-research');
      expect(uri3.path, '/commercial/marketing-context/customer-research');
    });
  });

  group('MarketingService Canonical Context Endpoints', () {
    test('getMarketingContext fetches /commercial/marketing-context with workspace header', () async {
      String? capturedPath;
      String? capturedAuth;
      String? capturedWorkspace;

      ApiClient.client = MockClient((request) async {
        capturedPath = request.url.path;
        capturedAuth = request.headers['Authorization'];
        capturedWorkspace = request.headers['X-Workspace-Id'];

        final responsePayload = {
          'id': 'ctx-100',
          'workspaceId': '351550739880456242',
          'revision': 1,
          'status': 'draft',
          'productMarketing': {
            'category': 'AI SaaS Platform',
            'positioningStatement': 'Positioning statement test',
            'alternatives': [],
            'differentiators': [],
            'brandVoice': {},
          },
          'icpSegments': [],
          'customerResearchThemes': [],
          'customerLanguage': [],
          'evidence': [],
          'offerArchitecture': {},
          'twelveWeekPlan': {},
          'createdAt': '2026-08-28T09:00:00.000Z',
          'updatedAt': '2026-08-28T09:00:00.000Z',
        };

        return http.Response(jsonEncode(responsePayload), 200, headers: {'content-type': 'application/json'});
      });

      final service = MarketingService();
      final result = await service.getMarketingContext();

      expect(capturedPath, '/commercial/marketing-context');
      expect(capturedAuth, 'Bearer test-token-jwt');
      expect(capturedWorkspace, '351550739880456242');
      expect(result, isNotNull);
      expect(result!['revision'], 1);
      expect(result['status'], 'draft');
      expect(result['product_marketing']['category'], 'AI SaaS Platform');
    });

    test('updateProductMarketing sends PATCH to /commercial/marketing-context/product-marketing with expectedRevision', () async {
      String? capturedPath;
      String? capturedMethod;
      Map<String, dynamic>? capturedBody;

      ApiClient.client = MockClient((request) async {
        capturedPath = request.url.path;
        capturedMethod = request.method;
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;

        return http.Response(
          jsonEncode({
            'id': 'ctx-100',
            'revision': 2,
            'status': 'draft',
            'productMarketing': capturedBody,
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = MarketingService();
      final updated = await service.updateProductMarketing(
        {
          'category': 'Updated Category',
          'positioningStatement': 'New Statement',
        },
        expectedRevision: 1,
      );

      expect(capturedPath, '/commercial/marketing-context/product-marketing');
      expect(capturedMethod, 'PATCH');
      expect(capturedBody!['expectedRevision'], 1);
      expect(capturedBody!['category'], 'Updated Category');
      expect(updated['revision'], 2);
    });

    test('updateCustomerResearch sends PATCH to /commercial/marketing-context/customer-research', () async {
      String? capturedPath;
      String? capturedMethod;

      ApiClient.client = MockClient((request) async {
        capturedPath = request.url.path;
        capturedMethod = request.method;

        return http.Response(
          jsonEncode({
            'id': 'ctx-100',
            'revision': 3,
            'status': 'draft',
            'icpSegments': [{'segment': 'Founders'}],
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = MarketingService();
      final updated = await service.updateCustomerResearch(
        {
          'icpSegments': [{'segment': 'Founders'}],
        },
        expectedRevision: 2,
      );

      expect(capturedPath, '/commercial/marketing-context/customer-research');
      expect(capturedMethod, 'PATCH');
      expect(updated['revision'], 3);
    });

    test('submitMarketingContextForReview sends POST to submit-review', () async {
      String? capturedPath;

      ApiClient.client = MockClient((request) async {
        capturedPath = request.url.path;
        return http.Response(
          jsonEncode({
            'id': 'ctx-100',
            'revision': 4,
            'status': 'review_required',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = MarketingService();
      final result = await service.submitMarketingContextForReview(expectedRevision: 3);

      expect(capturedPath, '/commercial/marketing-context/submit-review');
      expect(result['status'], 'review_required');
      expect(result['revision'], 4);
    });

    test('approveMarketingContext sends POST to approve', () async {
      String? capturedPath;

      ApiClient.client = MockClient((request) async {
        capturedPath = request.url.path;
        return http.Response(
          jsonEncode({
            'id': 'ctx-100',
            'revision': 5,
            'status': 'approved',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = MarketingService();
      final result = await service.approveMarketingContext(expectedRevision: 4);

      expect(capturedPath, '/commercial/marketing-context/approve');
      expect(result['status'], 'approved');
      expect(result['revision'], 5);
    });
  });

  group('MarketingService Typed Exception Mapping', () {
    test('maps 401/403 to MarketingAuthException', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'message': 'user không thuộc workspace'}),
          403,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = MarketingService();
      expect(
        () => service.getMarketingContext(),
        throwsA(isA<MarketingAuthException>().having((e) => e.statusCode, 'statusCode', 403)),
      );
    });

    test('maps 404 to MarketingNotFoundException', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'message': 'resource not found'}),
          404,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = MarketingService();
      expect(
        () => service.getMarketingContext(),
        throwsA(isA<MarketingNotFoundException>().having((e) => e.statusCode, 'statusCode', 404)),
      );
    });

    test('maps 409 / aborted to MarketingConflictException', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'message': 'revision conflict: expected revision 1 but current is 2'}),
          409,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = MarketingService();
      expect(
        () => service.updateProductMarketing({'category': 'conflict'}, expectedRevision: 1),
        throwsA(isA<MarketingConflictException>()),
      );
    });

    test('maps malformed 200 JSON to MarketingParseException', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('not valid json {;;', 200);
      });

      final service = MarketingService();
      expect(
        () => service.getMarketingContext(),
        throwsA(isA<MarketingParseException>()),
      );
    });
  });
}
