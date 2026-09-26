import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/finance/services/finance_service.dart';

http.Response _json(Object body) =>
    http.Response(jsonEncode(body), 200, headers: {'content-type': 'application/json'});

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
    await SecureStorageService.write('workspace_id', '1001');
  });

  tearDown(() => ApiClient.client = http.Client());

  test('getDocuments đọc /finance/accounting-documents và thêm key tab cần', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/finance/accounting-documents');
      return _json({
        'documents': [
          {'id': 'd1', 'number': 'PT001', 'documentType': 'RECEIPT', 'documentDate': '2026-09-01', 'status': 'DRAFT'},
        ],
      });
    });

    final docs = await FinanceService().getDocuments();

    final doc = docs.single as Map<String, dynamic>;
    expect(doc['document_no'], 'PT001');
    expect(doc['document_type'], 'RECEIPT');
    expect(doc['document_date'], '2026-09-01');
  });

  test('getExceptions dùng API liệt kê theo workspace', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/finance-legal/workspaces/1001/exceptions');
      return _json({
        'exceptions': [
          {
            'id': 'e1',
            'exceptionType': 'UNUSUAL_AMOUNT',
            'severity': 'WARNING',
            'status': 'OPEN',
            'transactionId': 't9',
            'details': null,
          },
        ],
      });
    });

    final exceptions = await FinanceService().getExceptions();

    final e = exceptions.single as Map<String, dynamic>;
    expect(e['title'], 'UNUSUAL_AMOUNT · WARNING · OPEN');
    expect(e['description'], 'Giao dịch #t9');
  });

  test('getPeriods thêm start_date/end_date cho tab Kỳ kế toán', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/finance-legal/accounting-periods');
      return _json({
        'periods': [
          {'id': 'p1', 'startDate': '2026-09-01', 'endDate': '2026-09-30', 'status': 'OPEN'},
        ],
      });
    });

    final p = (await FinanceService().getPeriods()).single as Map<String, dynamic>;

    expect(p['start_date'], '2026-09-01');
    expect(p['end_date'], '2026-09-30');
  });

  test('getBooks/getReports không gọi route không tồn tại', () async {
    ApiClient.client = MockClient((request) async => fail('unexpected ${request.url}'));

    expect(await FinanceService().getBooks(), isEmpty);
    expect(await FinanceService().getReports(), isEmpty);
  });
}
