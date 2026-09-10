import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/sales/services/sales_service.dart';
import 'package:frontend/modules/finance/services/finance_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'workspace_id': '1001',
    });
    await SecureStorageService.write('auth_token', 'test-token');
    await SecureStorageService.write('workspace_id', '1001');
  });

  tearDown(() {
    ApiClient.client = http.Client();
  });

  group('SalesService project context propagation', () {
    test('createContact passes projectId in request body', () async {
      http.Request? capturedRequest;
      ApiClient.client = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({'id': 'contact-1', 'name': 'Alice', 'projectId': 'proj-123'}),
          201,
          headers: {'content-type': 'application/json'},
        );
      });

      final salesService = SalesService();
      final result = await salesService.createContact(
        {'name': 'Alice', 'email': 'alice@example.com'},
        projectId: 'proj-123',
      );

      expect(result, isNotNull);
      expect(capturedRequest, isNotNull);
      final body = jsonDecode(capturedRequest!.body) as Map<String, dynamic>;
      expect(body['projectId'], 'proj-123');
      expect(body['workspaceId'], '1001');
    });

    test('createLead passes projectId in request body', () async {
      http.Request? capturedRequest;
      ApiClient.client = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({'id': 'lead-1', 'name': 'Bob', 'projectId': 'proj-123'}),
          201,
          headers: {'content-type': 'application/json'},
        );
      });

      final salesService = SalesService();
      final result = await salesService.createLead(
        {'name': 'Bob', 'company': 'Acme Corp'},
        projectId: 'proj-123',
      );

      expect(result, isNotNull);
      expect(capturedRequest, isNotNull);
      final body = jsonDecode(capturedRequest!.body) as Map<String, dynamic>;
      expect(body['projectId'], 'proj-123');
      expect(body['workspaceId'], '1001');
    });

    test('getLeads passes projectId in query params', () async {
      http.Request? capturedRequest;
      ApiClient.client = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({'leads': []}),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final salesService = SalesService();
      await salesService.getLeads(projectId: 'proj-123');

      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.url.queryParameters['projectId'], 'proj-123');
      expect(capturedRequest!.url.queryParameters['workspace_id'], '1001');
    });

    test('createOpportunity passes projectId in request body', () async {
      http.Request? capturedRequest;
      ApiClient.client = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({'id': 'opp-1', 'title': 'Deal 1', 'projectId': 'proj-123'}),
          201,
          headers: {'content-type': 'application/json'},
        );
      });

      final salesService = SalesService();
      final result = await salesService.createOpportunity(
        {'title': 'Deal 1', 'amount': 10000},
        projectId: 'proj-123',
      );

      expect(result, isNotNull);
      expect(capturedRequest, isNotNull);
      final body = jsonDecode(capturedRequest!.body) as Map<String, dynamic>;
      expect(body['projectId'], 'proj-123');
      expect(body['workspaceId'], '1001');
    });
  });

  group('FinanceService project context propagation', () {
    test('recordTransaction passes projectId in request body', () async {
      http.Request? capturedRequest;
      ApiClient.client = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({'id': 'tx-1', 'amount': '5000000', 'projectId': 'proj-123'}),
          201,
          headers: {'content-type': 'application/json'},
        );
      });

      final financeService = FinanceService();
      final result = await financeService.recordTransaction(
        {
          'transactionDate': '2026-09-10',
          'description': 'Dev equipment',
          'amount': '5000000',
          'direction': 'EXPENSE',
        },
        projectId: 'proj-123',
      );

      expect(result, isNotNull);
      expect(capturedRequest, isNotNull);
      final body = jsonDecode(capturedRequest!.body) as Map<String, dynamic>;
      expect(body['projectId'], 'proj-123');
      expect(body['workspaceId'], '1001');
    });

    test('getTransactions passes projectId in query params', () async {
      http.Request? capturedRequest;
      ApiClient.client = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({'transactions': []}),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final financeService = FinanceService();
      await financeService.getTransactions(projectId: 'proj-123');

      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.url.queryParameters['projectId'], 'proj-123');
      expect(capturedRequest!.url.queryParameters['workspaceId'], '1001');
    });
  });
}
