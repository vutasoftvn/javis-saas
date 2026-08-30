import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/data/models/pilot_run_model.dart';
import 'package:frontend/modules/strategy/services/pilot_run_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() async {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({});
    await SecureStorageService.write('auth_token', 'test-token');
    await SecureStorageService.write('local_session_token', 'test-local-token');
    await SecureStorageService.write('workspace_id', '1001');
  });

  tearDown(() {
    ApiClient.client = realClient;
    ApiClient.clearRuntimeContext();
  });

  group('PilotRunModel Tests', () {
    test('parses from JSON correctly', () {
      final json = {
        'id': '704900111222333444',
        'workspaceId': '1001',
        'projectId': '2001',
        'status': 'DRAFT',
        'designPartnerEvidenceRefs': ['3001', '3002'],
        'metricContractArtifactRef': 'artifact://ws-a/metrics/v1',
        'instrumentationArtifactRef': 'artifact://ws-a/inst/v1',
        'onboardingArtifactRef': 'artifact://ws-a/pilot/onboarding-v1',
        'rollbackArtifactRef': 'artifact://ws-a/pilot/rollback-v1',
        'releaseOwnerMemberId': '9001',
        'version': 1,
        'createdAt': '2026-08-30T12:00:00Z',
        'updatedAt': '2026-08-30T12:00:00Z',
      };

      final model = PilotRun.fromJson(json);
      expect(model.id, '704900111222333444');
      expect(model.status, PilotRunStatus.draft);
      expect(model.designPartnerEvidenceRefs.length, 2);
      expect(model.missingPrerequisites, isEmpty);
      expect(model.isReadyForHumanApproval, true);
    });

    test('identifies missing prerequisites explicitly', () {
      final incomplete = PilotRun(
        id: '1',
        workspaceId: '1001',
        projectId: '2001',
        status: PilotRunStatus.draft,
        designPartnerEvidenceRefs: [],
        metricContractArtifactRef: null,
        instrumentationArtifactRef: 'artifact://ws/inst',
        onboardingArtifactRef: '',
        rollbackArtifactRef: null,
        releaseOwnerMemberId: '',
        version: 1,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      final missing = incomplete.missingPrerequisites;
      expect(missing, contains('Thiếu design partner evidence đã duyệt'));
      expect(missing, contains('Thiếu metric contract'));
      expect(missing, contains('Thiếu onboarding runbook'));
      expect(missing, contains('Thiếu rollback runbook'));
      expect(missing, contains('Thiếu release owner'));
      expect(incomplete.isReadyForHumanApproval, false);
    });
  });

  group('PilotRunService Tests', () {
    test('activate sends only approvalRef without mutating lifecycle stage or sending humanOverride', () async {
      String? capturedBody;
      String? capturedPath;

      final mockClient = MockClient((request) async {
        capturedPath = request.url.path;
        capturedBody = request.body;

        final responseJson = {
          'id': '704900111222333444',
          'workspaceId': '1001',
          'projectId': '2001',
          'status': 'ACTIVE',
          'designPartnerEvidenceRefs': ['3001'],
          'metricContractArtifactRef': 'artifact://ws/metrics',
          'instrumentationArtifactRef': 'artifact://ws/inst',
          'onboardingArtifactRef': 'artifact://ws/onb',
          'rollbackArtifactRef': 'artifact://ws/rb',
          'releaseOwnerMemberId': '9001',
          'approvalRef': 'APR-TEST-1',
          'version': 2,
          'createdAt': '2026-08-30T12:00:00Z',
          'updatedAt': '2026-08-30T12:05:00Z',
        };

        return http.Response(jsonEncode(responseJson), 200, headers: {'content-type': 'application/json'});
      });

      ApiClient.client = mockClient;
      final service = PilotRunService();

      final result = await service.activate(
        pilotId: '704900111222333444',
        approvalRef: 'APR-TEST-1',
      );

      expect(result, isNotNull);
      expect(result!.status, PilotRunStatus.active);
      expect(capturedPath, '/operations/strategy/pilots/704900111222333444/activate');

      final parsed = jsonDecode(capturedBody!) as Map<String, dynamic>;
      expect(parsed['approvalRef'], 'APR-TEST-1');
      expect(parsed.containsKey('lifecycleStage'), false);
      expect(parsed.containsKey('humanOverride'), false);
      expect(parsed.containsKey('stage'), false);
    });
  });
}
