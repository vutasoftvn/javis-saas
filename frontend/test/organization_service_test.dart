import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/organization/services/organization_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Spec 2026-09-25 §7 — Organization API typed: đúng route mới, body camelCase,
// và lỗi 401/403/404/422 thành ApiFailure rõ ràng thay vì null.

OrganizationService _serviceWith(MockClient client) =>
    OrganizationService(client: MvpRequestClient(httpClient: client));

http.Response _json(Object body, int status) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json'});

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '4242'});
    await SecureStorageService.write('auth_token', 'token');
  });

  group('getOverview', () {
    test('calls the organization overview route and decodes the DTO', () async {
      final service = _serviceWith(MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/operations/organizations/4242/overview');
        expect(request.headers['X-Workspace-Id'], '4242');
        return _json({
          'organizationId': '4242',
          'name': 'COSA Global',
          'lifecycleStage': 'W0_IDEA',
          'viewerRole': 'founder',
          'canManageWorkforce': true,
          'humanMemberCount': 2,
          'aiMemberCount': 3,
        }, 200);
      }));

      final result = await service.getOverview();

      expect(result.isSuccess, isTrue);
      expect(result.dataOrNull?.name, 'COSA Global');
      expect(result.dataOrNull?.aiMemberCount, 3);
    });

    test('never calls the removed /org/* routes', () async {
      final service = _serviceWith(MockClient((request) async {
        expect(request.url.path.startsWith('/org/'), isFalse);
        return _json({}, 200);
      }));
      await service.getOverview();
      await service.listWorkforce();
    });

    for (final entry in {
      401: ApiFailureCode.unauthenticated,
      403: ApiFailureCode.forbidden,
      404: ApiFailureCode.notFound,
    }.entries) {
      test('maps HTTP ${entry.key} to ${entry.value}', () async {
        final service = _serviceWith(MockClient((request) async => _json({'code': 'x', 'message': 'nope'}, entry.key)));
        final result = await service.getOverview();
        expect(result.isFailure, isTrue);
        expect(result.failureOrNull?.code, entry.value);
      });
    }

    test('reports a missing organization context instead of returning null', () async {
      SharedPreferences.setMockInitialValues({});
      final service = _serviceWith(MockClient((request) async {
        fail('should not call the API without an organization id');
      }));
      final result = await service.getOverview();
      expect(result.failureOrNull?.code, ApiFailureCode.invalidRequest);
    });
  });

  group('listWorkforce', () {
    test('decodes members including the workspace agent reference', () async {
      final service = _serviceWith(MockClient((request) async {
        expect(request.url.path, '/operations/organizations/4242/workforce');
        return _json({
          'organizationId': '4242',
          'members': [
            {
              'id': '1',
              'memberType': 'AI_AGENT',
              'roleTitle': 'Ops Agent',
              'managerMemberId': null,
              'status': 'active',
              'workspaceAgentId': '77',
            },
          ],
        }, 200);
      }));

      final result = await service.listWorkforce();

      expect(result.dataOrNull?.members.single.isAi, isTrue);
      expect(result.dataOrNull?.members.single.workspaceAgentId, '77');
    });

    test('treats a malformed payload as malformedResponse', () async {
      final service = _serviceWith(MockClient((request) async => _json({'members': 'oops'}, 200)));
      final result = await service.listWorkforce();
      expect(result.failureOrNull?.code, ApiFailureCode.malformedResponse);
    });
  });

  group('placeAiWorkforce', () {
    test('posts only server-owned references in camelCase', () async {
      final service = _serviceWith(MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/organizations/4242/ai-workforce');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body, {
          'workspaceAgentId': '77',
          'roleTitle': 'Growth Lead',
          'idempotencyKey': 'k-1',
        });
        return _json({
          'member': {
            'id': '901',
            'memberType': 'AI_AGENT',
            'roleTitle': 'Growth Lead',
            'managerMemberId': null,
            'status': 'active',
            'workspaceAgentId': '77',
          },
        }, 200);
      }));

      final result = await service.placeAiWorkforce(
        workspaceAgentId: '77',
        roleTitle: 'Growth Lead',
        idempotencyKey: 'k-1',
      );

      expect(result.dataOrNull?.id, '901');
    });

    test('maps a 400 validation error to invalidRequest', () async {
      final service = _serviceWith(MockClient((request) async => _json({'code': 'invalid_argument', 'message': 'roleTitle is required'}, 400)));
      final result = await service.placeAiWorkforce(
        workspaceAgentId: '77',
        roleTitle: '',
        idempotencyKey: 'k-2',
      );
      expect(result.failureOrNull?.code, ApiFailureCode.invalidRequest);
    });

    test('does not report success without a durable member id', () async {
      final service = _serviceWith(MockClient((request) async => _json({'member': {'id': ''}}, 200)));
      final result = await service.placeAiWorkforce(
        workspaceAgentId: '77',
        roleTitle: 'Growth Lead',
        idempotencyKey: 'k-3',
      );
      expect(result.isSuccess, isFalse);
    });
  });
}
