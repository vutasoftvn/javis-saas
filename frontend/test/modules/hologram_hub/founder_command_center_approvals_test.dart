// Fix-review (2026-09-02, final review I-1) — chứng minh
// `FounderCommandCenterController` không còn coi 404/route-không-tồn-tại của
// approvals là "không có approval nào đang chờ". Trước fix, controller gọi
// `ApprovalsService` (route cũ `/agent/approvals`, không được mount trong
// `apps/cosa/api/app.py` ⇒ luôn 404) và nuốt lỗi thành `[]` — không cách nào
// phân biệt được với "workspace thật sự không có approval nào".
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test_token',
      'workspace_id': 'ws_123',
    });
  });

  test(
    'loadDashboardData surfaces a 404 on /agent/workforce/approvals as unavailable, '
    'not a silent empty list',
    () async {
      final mockClient = MockClient((request) async {
        if (request.url.path.contains('/agent/workforce/approvals')) {
          return http.Response(jsonEncode({'error': 'not found'}), 404);
        }
        // Mọi endpoint khác trong loadDashboardData: trả lỗi xác định để
        // test chỉ tập trung vào tín hiệu approvals.
        return http.Response(jsonEncode({'error': 'not found'}), 404);
      });

      final controller = FounderCommandCenterController(
        workforceMvpService: WorkforceMvpService(
          client: MvpRequestClient(httpClient: mockClient),
        ),
      );

      await controller.loadDashboardData();

      expect(controller.pendingApprovals, isEmpty);
      expect(
        controller.approvalsState.value,
        WorkforceLoadState.unavailable,
        reason:
            '404 trên route approvals canonical phải là trạng thái "không tải '
            'được", không phải "đã tải, rỗng"',
      );
    },
  );

  test(
    'loadDashboardData loads pending approvals from the canonical '
    '/agent/workforce/approvals route on success',
    () async {
      final mockClient = MockClient((request) async {
        if (request.url.path.contains('/agent/workforce/approvals')) {
          return http.Response(
            jsonEncode({
              'data': [
                {
                  'approval_id': 'appr-1',
                  'run_id': 'run-1',
                  'action': 'send_email',
                  'subject': 'Sales Agent',
                  'status': 'PENDING',
                  'risk_level': 'high',
                  'required_role': 'admin',
                  'policy_id': 'policy-1',
                  'created_at': '2026-09-01T00:00:00Z',
                },
              ],
              'meta': {
                'data_state': 'populated',
                'observed_at': '2026-09-01T00:00:00Z',
              },
            }),
            200,
          );
        }
        return http.Response(jsonEncode({'error': 'not found'}), 404);
      });

      final controller = FounderCommandCenterController(
        workforceMvpService: WorkforceMvpService(
          client: MvpRequestClient(httpClient: mockClient),
        ),
      );

      await controller.loadDashboardData();

      expect(controller.approvalsState.value, WorkforceLoadState.loaded);
      expect(controller.pendingApprovals, hasLength(1));
      expect(controller.pendingApprovals.first['id'], 'appr-1');
    },
  );
}
