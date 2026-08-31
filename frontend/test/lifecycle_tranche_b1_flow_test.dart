// Tranche B1 Flow Test: chứng minh bất biến "pilot activation không bao giờ
// thay đổi lifecycle stage" đúng ở tầng UI/service Flutter, đối xứng với
// invariant đã kiểm chứng ở tầng Python agent-plane
// (tests/apps/cosa/test_lifecycle_tranche_b1_acceptance.py) và tầng TypeScript
// Company service (lifecycle-tranche-b1-contract.test.ts).
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/data/models/pilot_run_model.dart';
import 'package:frontend/modules/strategy/services/pilot_run_service.dart';
import 'package:frontend/modules/strategy/views/widgets/pilot_readiness_panel.dart';

Map<String, dynamic> _pilotJson({
  String id = '704900111',
  String status = 'DRAFT',
  String? rollbackArtifactRef = 'artifact://ws/rb/v1',
  String? approvalRef,
}) {
  return {
    'id': id,
    'workspaceId': '1001',
    'projectId': '2001',
    'status': status,
    'designPartnerEvidenceRefs': ['3001'],
    'metricContractArtifactRef': 'artifact://ws/metrics/v1',
    'instrumentationArtifactRef': 'artifact://ws/inst/v1',
    'onboardingArtifactRef': 'artifact://ws/onb/v1',
    'rollbackArtifactRef': rollbackArtifactRef,
    'releaseOwnerMemberId': '9001',
    'approvalRef': approvalRef,
    'approvedAt': approvalRef != null ? '2026-08-30T12:00:00Z' : null,
    'version': 1,
    'createdAt': '2026-08-30T12:00:00Z',
    'updatedAt': '2026-08-30T12:00:00Z',
  };
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() async {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test-token-jwt',
      'workspace_id': '1001',
    });
    await SecureStorageService.write('auth_token', 'test-token');
    await SecureStorageService.write('local_session_token', 'test-local-token');
    await SecureStorageService.write('workspace_id', '1001');
  });

  tearDown(() {
    ApiClient.client = realClient;
    ApiClient.clearRuntimeContext();
  });

  group('COSA Lifecycle Tranche B1 Pilot Flow Test', () {
    test(
      'list/createDraft/approve/activate/close send exactly the expected method+path+body',
      () async {
        final capturedRequests = <http.Request>[];

        final mockClient = MockClient((request) async {
          capturedRequests.add(request);
          if (request.method == 'GET') {
            return http.Response(
              jsonEncode({
                'items': [_pilotJson()],
              }),
              200,
              headers: {'content-type': 'application/json'},
            );
          }
          return http.Response(
            jsonEncode(_pilotJson(status: 'DRAFT')),
            200,
            headers: {'content-type': 'application/json'},
          );
        });

        ApiClient.client = mockClient;
        final service = PilotRunService();

        // list
        await service.listPilots(projectId: '2001');
        expect(capturedRequests.last.method, 'GET');
        expect(capturedRequests.last.url.path, '/operations/strategy/pilots');
        expect(capturedRequests.last.url.query, contains('projectId=2001'));

        // createDraft
        await service.createDraft(
          projectId: '2001',
          designPartnerEvidenceRefs: ['3001'],
          metricContractArtifactRef: 'artifact://ws/metrics/v1',
          instrumentationArtifactRef: 'artifact://ws/inst/v1',
          onboardingArtifactRef: 'artifact://ws/onb/v1',
          rollbackArtifactRef: 'artifact://ws/rb/v1',
          releaseOwnerMemberId: '9001',
        );
        expect(capturedRequests.last.method, 'POST');
        expect(capturedRequests.last.url.path, '/operations/strategy/pilots');
        final createBody =
            jsonDecode(capturedRequests.last.body) as Map<String, dynamic>;
        expect(createBody['projectId'], '2001');
        expect(createBody['designPartnerEvidenceRefs'], ['3001']);
        expect(createBody['rollbackArtifactRef'], 'artifact://ws/rb/v1');
        expect(createBody.containsKey('lifecycleStage'), false);
        expect(createBody.containsKey('humanOverride'), false);

        // approve
        await service.approve(pilotId: '704900111', approvalRef: 'APR-1');
        expect(capturedRequests.last.method, 'POST');
        expect(
          capturedRequests.last.url.path,
          '/operations/strategy/pilots/704900111/approve',
        );
        final approveBody =
            jsonDecode(capturedRequests.last.body) as Map<String, dynamic>;
        expect(approveBody, {'approvalRef': 'APR-1'});

        // activate
        await service.activate(pilotId: '704900111', approvalRef: 'APR-2');
        expect(capturedRequests.last.method, 'POST');
        expect(
          capturedRequests.last.url.path,
          '/operations/strategy/pilots/704900111/activate',
        );
        final activateBody =
            jsonDecode(capturedRequests.last.body) as Map<String, dynamic>;
        expect(activateBody, {'approvalRef': 'APR-2'});

        // close
        await service.close(pilotId: '704900111', status: 'COMPLETED');
        expect(capturedRequests.last.method, 'POST');
        expect(
          capturedRequests.last.url.path,
          '/operations/strategy/pilots/704900111/close',
        );
        final closeBody =
            jsonDecode(capturedRequests.last.body) as Map<String, dynamic>;
        expect(closeBody, {'status': 'COMPLETED'});

        // Không có request nào từng nhắm tới stage-transition endpoint.
        for (final req in capturedRequests) {
          expect(req.url.path, isNot(contains('/stage')));
        }
      },
    );

    test(
      'activate() sends only { approvalRef } — never a stage value',
      () async {
        String? capturedBody;

        final mockClient = MockClient((request) async {
          capturedBody = request.body;
          return http.Response(
            jsonEncode(_pilotJson(status: 'ACTIVE', approvalRef: 'APR-ONLY-1')),
            200,
            headers: {'content-type': 'application/json'},
          );
        });

        ApiClient.client = mockClient;
        final service = PilotRunService();

        final result = await service.activate(
          pilotId: '704900111',
          approvalRef: 'APR-ONLY-1',
        );
        expect(result, isNotNull);
        expect(result!.status, PilotRunStatus.active);

        final parsedBody = jsonDecode(capturedBody!) as Map<String, dynamic>;
        expect(parsedBody.keys.toSet(), {'approvalRef'});
        expect(parsedBody.containsKey('lifecycleStage'), false);
        expect(parsedBody.containsKey('stage'), false);
        expect(parsedBody.containsKey('humanOverride'), false);
      },
    );

    testWidgets(
      'PilotReadinessPanel with a missing reference shows missing-item message and no activate action',
      (WidgetTester tester) async {
        final draftMissingRollback = PilotRun(
          id: '101',
          workspaceId: '1001',
          projectId: '2001',
          status: PilotRunStatus.draft,
          designPartnerEvidenceRefs: ['3001'],
          metricContractArtifactRef: 'artifact://ws/metrics',
          instrumentationArtifactRef: 'artifact://ws/inst',
          onboardingArtifactRef: 'artifact://ws/onb',
          rollbackArtifactRef: null, // MISSING
          releaseOwnerMemberId: '9001',
          version: 1,
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
        );

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: PilotReadinessPanel(
                  pilot: draftMissingRollback,
                  isFounderOrAdmin: true,
                ),
              ),
            ),
          ),
        );

        expect(find.textContaining('Thiếu rollback runbook'), findsOneWidget);
        expect(find.text('Kích hoạt pilot'), findsNothing);
      },
    );

    testWidgets(
      'PilotReadinessPanel with a fully-ready APPROVED pilot shows the activate path',
      (WidgetTester tester) async {
        final approvedPilot = PilotRun(
          id: '102',
          workspaceId: '1001',
          projectId: '2001',
          status: PilotRunStatus.approved,
          designPartnerEvidenceRefs: ['3001'],
          metricContractArtifactRef: 'artifact://ws/metrics',
          instrumentationArtifactRef: 'artifact://ws/inst',
          onboardingArtifactRef: 'artifact://ws/onb',
          rollbackArtifactRef: 'artifact://ws/rb',
          releaseOwnerMemberId: '9001',
          approvalRef: 'APR-2026-001',
          approvedAt: DateTime.now(),
          version: 2,
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
        );

        String? activatedRef;

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: PilotReadinessPanel(
                  pilot: approvedPilot,
                  isFounderOrAdmin: true,
                  onActivate: (ref) {
                    activatedRef = ref;
                  },
                ),
              ),
            ),
          ),
        );

        expect(find.text('Kích hoạt pilot'), findsOneWidget);

        await tester.tap(find.text('Kích hoạt pilot'));
        await tester.pumpAndSettle();
        await tester.enterText(find.byType(TextField), 'APR-FLOW-TEST-1');
        await tester.tap(find.text('Xác nhận Kích hoạt'));
        await tester.pumpAndSettle();

        expect(activatedRef, 'APR-FLOW-TEST-1');
      },
    );

    test(
      'no widget or service call in the pilot flow ever hits the stage-transition endpoint',
      () async {
        final capturedPaths = <String>[];

        final mockClient = MockClient((request) async {
          capturedPaths.add(request.url.path);
          if (request.method == 'GET') {
            return http.Response(
              jsonEncode({
                'items': [
                  _pilotJson(
                    status: 'APPROVED',
                    approvalRef: 'APR-STAGE-CHECK',
                  ),
                ],
              }),
              200,
              headers: {'content-type': 'application/json'},
            );
          }
          return http.Response(
            jsonEncode(
              _pilotJson(status: 'ACTIVE', approvalRef: 'APR-STAGE-CHECK'),
            ),
            200,
            headers: {'content-type': 'application/json'},
          );
        });

        ApiClient.client = mockClient;
        final service = PilotRunService();

        await service.listPilots(projectId: '2001');
        await service.getPilot('704900111');
        await service.approve(
          pilotId: '704900111',
          approvalRef: 'APR-STAGE-CHECK',
        );
        await service.activate(
          pilotId: '704900111',
          approvalRef: 'APR-STAGE-CHECK',
        );
        await service.close(pilotId: '704900111', status: 'COMPLETED');

        expect(capturedPaths, isNotEmpty);
        for (final path in capturedPaths) {
          expect(path, isNot(contains('/stage')));
        }
      },
    );
  });
}
