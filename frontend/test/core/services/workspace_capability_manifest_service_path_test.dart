import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/core/services/workspace_capability_manifest_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Endpoint manifest đã đổi sang `:organizationId`; trước đây client chỉ thay
// `:workspaceId` nên gửi nguyên chuỗi ":organizationId", manifest luôn lỗi và
// Finance bị ẩn khỏi sidebar.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '4242'});
    await SecureStorageService.write('workspace_id', '4242');
    await SecureStorageService.write('auth_token', 'token');
  });

  test('capability manifest request fills organizationId from the active workspace', () async {
    Uri? requested;
    final httpClient = MockClient((request) async {
      requested = request.url;
      return http.Response('unavailable', 503);
    });

    await WorkspaceCapabilityManifestService(
      client: MvpRequestClient(httpClient: httpClient),
    ).fetch();

    expect(requested, isNotNull);
    expect(requested!.path, endsWith('/platform/organizations/4242/capability-manifest'));
    expect(requested!.path, isNot(contains(':organizationId')));
  });
}
