import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/hologram_hub/models/project_startup_team.dart';
import 'package:frontend/modules/hologram_hub/services/project_startup_team_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'workspace_id': '1001',
    });
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('fetches startup team roster through generated endpoint with truthful states', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/operations/projects/proj-101/startup-team');

      return http.Response(
        jsonEncode({
          'data': {
            'items': [
              {
                'profileKey': 'founder_assistant',
                'label': 'Co-Founder',
                'displayState': 'CHAT_READY',
                'runtimeReadiness': 'READY',
              },
              {
                'profileKey': 'marketing',
                'label': 'Marketing',
                'displayState': 'ACTIVE',
                'runtimeReadiness': 'READY',
                'assignmentVersion': 2,
                'activatedAt': '2026-09-11T12:00:00.000Z',
                'activatedBy': 'user-1',
              },
              {
                'profileKey': 'coding',
                'label': 'Coding',
                'displayState': 'TEMPLATE',
                'runtimeReadiness': 'DEFERRED_CODING',
                'disabledReason': 'DEFERRED_CODING',
              },
            ],
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-11T12:00:00Z',
            'sources': [
              {'kind': 'company_db', 'ref': 'operating'}
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = ProjectStartupTeamService(client: requestClient);

    final result = await service.fetchTeam('proj-101');
    expect(result, isA<ApiSuccess<List<ProjectStartupTeamMember>>>());
    final members = (result as ApiSuccess<List<ProjectStartupTeamMember>>).data;
    expect(members, hasLength(3));

    expect(members[0].profileKey, 'founder_assistant');
    expect(members[0].displayState, TeamDisplayState.chatReady);
    expect(members[0].runtimeReadiness, RuntimeReadiness.ready);

    expect(members[1].profileKey, 'marketing');
    expect(members[1].displayState, TeamDisplayState.active);
    expect(members[1].assignmentVersion, 2);
    expect(members[1].activatedAt?.isUtc, isTrue);

    expect(members[2].profileKey, 'coding');
    expect(members[2].displayState, TeamDisplayState.template);
    expect(members[2].runtimeReadiness, RuntimeReadiness.deferredCoding);
    expect(members[2].disabledReason, 'DEFERRED_CODING');
  });

  test('activates an agent template with expected version', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(
        request.url.path,
        '/operations/projects/proj-101/startup-team/marketing/activate',
      );
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['expectedVersion'], 1);

      return http.Response(
        jsonEncode({
          'data': {
            'profileKey': 'marketing',
            'label': 'Marketing',
            'displayState': 'ACTIVE',
            'runtimeReadiness': 'READY',
            'assignmentVersion': 2,
            'activatedAt': '2026-09-11T12:30:00.000Z',
            'activatedBy': 'user-1',
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-11T12:30:00Z',
            'sources': [
              {'kind': 'company_db', 'ref': 'operating'}
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = ProjectStartupTeamService(client: requestClient);

    final result = await service.activate(
      projectId: 'proj-101',
      profileKey: 'marketing',
      expectedVersion: 1,
    );

    expect(result, isA<ApiSuccess<ProjectStartupTeamMember>>());
    final member = (result as ApiSuccess<ProjectStartupTeamMember>).data;
    expect(member.displayState, TeamDisplayState.active);
    expect(member.assignmentVersion, 2);
  });

  test('pauses an active agent member with reason', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(
        request.url.path,
        '/operations/projects/proj-101/startup-team/marketing/pause',
      );
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['expectedVersion'], 2);
      expect(body['reason'], 'Budget pause');

      return http.Response(
        jsonEncode({
          'data': {
            'profileKey': 'marketing',
            'label': 'Marketing',
            'displayState': 'PAUSED',
            'runtimeReadiness': 'READY',
            'disabledReason': 'Budget pause',
            'assignmentVersion': 3,
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-11T13:00:00Z',
            'sources': [
              {'kind': 'company_db', 'ref': 'operating'}
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = ProjectStartupTeamService(client: requestClient);

    final result = await service.pause(
      projectId: 'proj-101',
      profileKey: 'marketing',
      expectedVersion: 2,
      reason: 'Budget pause',
    );

    expect(result, isA<ApiSuccess<ProjectStartupTeamMember>>());
    final member = (result as ApiSuccess<ProjectStartupTeamMember>).data;
    expect(member.displayState, TeamDisplayState.paused);
    expect(member.assignmentVersion, 3);
    expect(member.disabledReason, 'Budget pause');
  });

  test('handles 409 version conflict error gracefully', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'message': 'Version conflict'}),
        409,
        headers: {'content-type': 'application/json'},
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = ProjectStartupTeamService(client: requestClient);

    final result = await service.activate(
      projectId: 'proj-101',
      profileKey: 'marketing',
      expectedVersion: 1,
    );

    expect(result, isA<ApiFailure<ProjectStartupTeamMember>>());
    final failure = result as ApiFailure<ProjectStartupTeamMember>;
    expect(failure.failure.statusCode, 409);
    expect(failure.failure.code, ApiFailureCode.conflict);
  });
}
