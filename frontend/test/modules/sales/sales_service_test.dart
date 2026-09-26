import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/sales/services/sales_service.dart';

http.Response _json(Object body, [int status = 200]) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json'});

SalesService _service(Future<http.Response> Function(http.Request) handler) =>
    SalesService(client: MvpRequestClient(httpClient: MockClient(handler)));

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('listAccounts gọi /commercial/workspaces/:workspaceId/accounts', () async {
    final service = _service((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/commercial/workspaces/1001/accounts');
      return _json({
        'accounts': [
          {'id': 'a1', 'name': 'Acme'},
        ],
      });
    });

    final result = await service.listAccounts();

    expect((result as ApiSuccess<List<Map<String, dynamic>>>).data.single['name'], 'Acme');
  });

  test('listLeads gửi workspaceId qua query', () async {
    final service = _service((request) async {
      expect(request.url.path, '/commercial/leads');
      expect(request.url.queryParameters['workspaceId'], '1001');
      return _json({'leads': <Object>[]});
    });

    expect(await service.listLeads(), isA<ApiSuccess<List<Map<String, dynamic>>>>());
  });

  test('createContact / createLead mang workspaceId + projectId trong body', () async {
    final bodies = <Map<String, dynamic>>[];
    final service = _service((request) async {
      bodies.add(jsonDecode(request.body) as Map<String, dynamic>);
      return _json({'id': 'x'}, 201);
    });

    await service.createContact(name: 'Alice', email: 'alice@example.com', projectId: 'proj-123');
    await service.createLead(name: 'Bob', company: 'Acme Corp', projectId: 'proj-123');

    for (final body in bodies) {
      expect(body['workspaceId'], '1001');
      expect(body['projectId'], 'proj-123');
    }
    expect(bodies.first.containsKey('phone'), isFalse);
  });

  test('updateOpportunityStage POST stage với id trong path', () async {
    final service = _service((request) async {
      expect(request.url.path, '/commercial/opportunities/opp-1/stage');
      expect(jsonDecode(request.body), {'stage': 'WON'});
      return _json({'id': 'opp-1', 'stage': 'WON'});
    });

    final result = await service.updateOpportunityStage('opp-1', 'WON');

    expect((result as ApiSuccess<Map<String, dynamic>>).data['stage'], 'WON');
  });

  test('lỗi backend trả ApiFailure thay vì danh sách rỗng giả', () async {
    final service = _service((_) async => _json({'message': 'boom'}, 500));

    expect(await service.listOpportunities(), isA<ApiFailure<List<Map<String, dynamic>>>>());
  });
}
