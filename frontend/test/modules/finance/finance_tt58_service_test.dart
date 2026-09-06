import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/finance/services/finance_tt58_service.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Task 11 (F6b) — trước đây `finance_tt58_service.dart` không có test tự
/// động nào; bug route bị rewrite nhầm `/finance/` → `/finance-legal/` (đã
/// gặp ở F6a, xem ghi chú `javis-saas-f6a-budget-summary-status`) và lỗi
/// công thức `ownerEquity` (thiếu cộng `retainedEarnings`) đều có thể tái
/// diễn âm thầm nếu không có test khẳng định URL thật gọi đi và giá trị
/// biến đổi B01. Client này ghi lại URL cuối cùng thực sự được gửi để chứng
/// minh không có rewrite ngầm.
class _RecordingClient extends http.BaseClient {
  _RecordingClient(this.jsonResponse);

  final Map<String, dynamic> jsonResponse;
  String? lastUrl;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    lastUrl = request.url.toString();
    final body = utf8.encode(jsonEncode(jsonResponse));
    return http.StreamedResponse(
      Stream.value(body),
      200,
      headers: {'content-type': 'application/json'},
    );
  }
}

class _FailingClient extends http.BaseClient {
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    return http.StreamedResponse(Stream.value(utf8.encode('{}')), 500);
  }
}

void main() {
  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
  });

  tearDown(() => ApiClient.client = realClient);

  test('getReport hits /finance/reports/generate (không bị rewrite sang /finance-legal/reports) và biến đổi đúng dòng B01', () async {
    final fakeClient = _RecordingClient({
      'id': '1',
      'legalEntityId': '1',
      'periodId': '1',
      'reportCode': 'B01',
      'mappingVersion': 'v2',
      'inputWatermark': 'x',
      'status': 'VERIFIED',
      'issues': [],
      'generatedAt': '2026-01-01T00:00:00Z',
      'lines': [
        {'lineCode': 'TS', 'officialCode': 'TS', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '124000000'},
        {'lineCode': 'PHAI_THU', 'officialCode': 'PHAI_THU', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '4000000'},
        {'lineCode': 'TON_KHO', 'officialCode': 'TON_KHO', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '0'},
        {'lineCode': 'NO_VAY', 'officialCode': 'NO_VAY', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '20000000'},
        {'lineCode': 'VON_GOP', 'officialCode': 'VON_GOP', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '100000000'},
        {'lineCode': 'LOI_NHUAN_GIU_LAI', 'officialCode': 'LOI_NHUAN_GIU_LAI', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '8000000'},
      ],
    });
    ApiClient.client = fakeClient;

    final result = await FinanceTT58Service().getReport('1', '1', 'B01');

    expect(fakeClient.lastUrl, contains('/finance/reports/generate'));
    expect(fakeClient.lastUrl, isNot(contains('/finance-legal/reports')));
    expect(result?['assets']['total_assets'], 128000000);
    expect(result?['assets']['inventories'], 0);
    // owner_equity = capital (VON_GOP) + retainedEarnings (LOI_NHUAN_GIU_LAI)
    // = 100_000_000 + 8_000_000 — fix đã áp dụng ở Task 9, không được thiếu
    // cộng retainedEarnings như bug cũ.
    expect(result?['capital_and_liabilities']['owner_equity'], 108000000);
    expect(result?['is_balanced'], true);
  });

  test('getReport trả về null khi backend gọi thất bại', () async {
    ApiClient.client = _FailingClient();

    final result = await FinanceTT58Service().getReport('1', '1', 'B01');

    expect(result, isNull);
  });
}
