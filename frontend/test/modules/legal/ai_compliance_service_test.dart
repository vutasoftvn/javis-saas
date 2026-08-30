import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/legal/services/ai_compliance_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'ws_123',
      'local_session_token': 'test_token_456',
    });
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  test('approve uses the ai-compliance route and required body', () async {
    String? lastPath;
    Map<String, dynamic>? lastBody;
    Map<String, String>? lastHeaders;
    final expiry = '2027-01-01T00:00:00Z';

    ApiClient.client = MockClient((request) async {
      lastPath = request.url.path;
      lastHeaders = request.headers;
      lastBody = jsonDecode(request.body) as Map<String, dynamic>;
      // Assert X-Workspace-Id header is present and query param is NOT appended as replacement header
      expect(request.headers['X-Workspace-Id'], 'ws_123');
      expect(request.url.queryParameters['workspace_id'], isNull);
      return http.Response(jsonEncode({'status': 'APPROVED_FOR_USE'}), 200);
    });

    final service = AiComplianceService();
    final ok = await service.approveDeployment(
      'dep-1',
      assessmentId: 'ass-1',
      rationale: 'reviewed',
      expiresAt: expiry,
    );

    expect(ok, isTrue);
    expect(lastPath, '/finance-legal/ai-compliance/deployments/dep-1/approve');
    expect(lastBody!['assessmentId'], 'ass-1');
    expect(lastBody!['rationale'], 'reviewed');
    expect(lastBody!['expiresAt'], expiry);
    expect(lastHeaders!['X-Workspace-Id'], 'ws_123');
  });

  test('suspend uses the ai-compliance route and rationale body', () async {
    String? lastPath;
    Map<String, dynamic>? lastBody;

    ApiClient.client = MockClient((request) async {
      lastPath = request.url.path;
      lastBody = jsonDecode(request.body) as Map<String, dynamic>;
      expect(request.headers['X-Workspace-Id'], 'ws_123');
      return http.Response(jsonEncode({'status': 'SUSPENDED'}), 200);
    });

    final service = AiComplianceService();
    final ok = await service.suspendDeployment('dep-1', rationale: 'Emergency stop');

    expect(ok, isTrue);
    expect(lastPath, '/finance-legal/ai-compliance/deployments/dep-1/suspend');
    expect(lastBody!['rationale'], 'Emergency stop');
  });

  test('resume uses the ai-compliance route and rationale body', () async {
    String? lastPath;
    Map<String, dynamic>? lastBody;

    ApiClient.client = MockClient((request) async {
      lastPath = request.url.path;
      lastBody = jsonDecode(request.body) as Map<String, dynamic>;
      expect(request.headers['X-Workspace-Id'], 'ws_123');
      return http.Response(jsonEncode({'status': 'APPROVED_FOR_USE'}), 200);
    });

    final service = AiComplianceService();
    final ok = await service.resumeDeployment('dep-1', rationale: 'Audit passed');

    expect(ok, isTrue);
    expect(lastPath, '/finance-legal/ai-compliance/deployments/dep-1/resume');
    expect(lastBody!['rationale'], 'Audit passed');
  });

  test('reportIncident uses the ai-compliance route and required fields', () async {
    String? lastPath;
    Map<String, dynamic>? lastBody;

    ApiClient.client = MockClient((request) async {
      lastPath = request.url.path;
      lastBody = jsonDecode(request.body) as Map<String, dynamic>;
      expect(request.headers['X-Workspace-Id'], 'ws_123');
      return http.Response(jsonEncode({'id': 'inc-100', 'status': 'OPEN'}), 200);
    });

    final service = AiComplianceService();
    final ok = await service.reportIncident(
      deploymentId: 'dep-1',
      severity: 'HIGH',
      summary: 'Data leak detected in model output',
      incidentType: 'SECURITY_INCIDENT',
    );

    expect(ok, isTrue);
    expect(lastPath, '/finance-legal/ai-compliance/incidents');
    expect(lastBody!['deploymentId'], 'dep-1');
    expect(lastBody!['severity'], 'HIGH');
    expect(lastBody!['summary'], 'Data leak detected in model output');
    expect(lastBody!['incidentType'], 'SECURITY_INCIDENT');
  });

  test('getComplianceCenter fetches center data without query workspace_id', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/finance-legal/ai-compliance/center');
      expect(request.headers['X-Workspace-Id'], 'ws_123');
      expect(request.url.queryParameters['workspace_id'], isNull);
      return http.Response(
        jsonEncode({
          'workspaceId': 'ws_123',
          'activeCount': 1,
          'incidentCount': 1,
          'deployments': [
            {
              'id': 'dep-1',
              'systemVersionId': 'sys-v1',
              'mode': 'ADVISORY_ONLY',
              'status': 'APPROVED_FOR_USE',
              'ownerName': 'Founder Member',
              'currentAssessmentId': 'ass-1',
              'assessmentExpiresAt': '2027-01-01T00:00:00Z',
              'providerStatus': 'APPROVED',
              'allowedCapabilities': ['model.input'],
            }
          ],
          'incidents': [
            {
              'id': 'inc-1',
              'deploymentId': 'dep-1',
              'severity': 'LOW',
              'status': 'OPEN',
              'summary': 'Test incident',
              'createdAt': '2026-08-30T00:00:00Z',
            }
          ],
        }),
        200,
      );
    });

    final service = AiComplianceService();
    final data = await service.getComplianceCenter();
    expect(data, isNotNull);
    expect(data!.deployments.length, 1);
    expect(data.deployments.first.id, 'dep-1');
    expect(data.activeCount, 1);
    expect(data.incidentCount, 1);
    expect(data.recentIncidents.length, 1);
  });
}
