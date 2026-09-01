import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/finance/services/finance_service.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Task 6 (Truthful MVP Hardening) — `updateProfileMode`/`activateProfile`
/// chưa có backend mutation route thật (`/finance-legal/accounting-profiles`
/// chỉ hỗ trợ create/get). Trước đây `updateProfile` âm thầm gọi lại
/// `createProfile`, còn `activateProfile` trả một Map hard-code coi như đã
/// kích hoạt — cả hai đều là "false success" không có HTTP mutation đứng sau.
/// Client này ghi lại mọi request thực sự đi ra để chứng minh không request
/// nào được gửi trong nhánh unavailable.
class _RecordingClient extends http.BaseClient {
  final List<http.BaseRequest> requests = [];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    requests.add(request);
    return http.StreamedResponse(Stream.value(const []), 200);
  }
}

void main() {
  late http.Client realClient;
  late _RecordingClient mockClient;
  late FinanceService service;

  setUp(() {
    realClient = ApiClient.client;
    mockClient = _RecordingClient();
    ApiClient.client = mockClient;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
    service = FinanceService();
  });

  tearDown(() => ApiClient.client = realClient);

  test('activate profile never reports active without an HTTP mutation', () async {
    final result = await service.activateProfile('profile-1');

    expect(result, isA<ActionUnavailable<Map<String, dynamic>>>());
    expect(mockClient.requests, isEmpty);
  });

  test('update profile mode never mutates without an HTTP mutation route', () async {
    final result = await service.updateProfile('TT58_MODE_2');

    expect(result, isA<ActionUnavailable<Map<String, dynamic>>>());
    expect(mockClient.requests, isEmpty);
  });
}
