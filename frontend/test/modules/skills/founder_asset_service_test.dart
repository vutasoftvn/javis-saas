import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/skills/models/founder_asset.dart';
import 'package:frontend/modules/skills/services/founder_asset_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('lists the founder asset library through the generated endpoint', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/operations/founder-assets');

      return http.Response(
        jsonEncode({
          'data': [
            {
              'assetId': 'skill.custom.summary',
              'assetKind': 'SKILL',
              'originAssetId': 'skill.builtin.summary',
              'version': '1',
              'definitionHash': 'sha256:abc',
              'lifecycle': 'DRAFT',
              'lastOperation': 'CLONE',
              'deployments': {'active': 0, 'paused': 0, 'retired': 0},
            },
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-14T00:00:00Z',
            'sources': [
              {'kind': 'company_db', 'ref': 'operations.founder_asset_events'},
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.listLibrary();

    expect(result, isA<ApiSuccess<List<FounderAssetLibraryItem>>>());
    final items = (result as ApiSuccess<List<FounderAssetLibraryItem>>).data;
    expect(items, hasLength(1));
    expect(items.first.assetKind, FounderAssetKind.skill);
    expect(items.first.originAssetId, 'skill.builtin.summary');
    expect(items.first.lifecycle, 'DRAFT');
  });

  test('clones a built-in skill into a workspace draft', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/operations/founder/assets/commands');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['assetKind'], 'SKILL');
      expect(body['operation'], 'CLONE');
      expect(body['assetRef'], {'assetId': 'skill.builtin.summary', 'version': '1'});
      expect(body['reason'], 'Tuỳ biến cho workspace');
      expect(body['idempotencyKey'], isNotEmpty);

      return http.Response(
        jsonEncode({
          'data': {
            'commandId': 'cmd-1',
            'assetKind': 'SKILL',
            'operation': 'CLONE',
            'status': 'PENDING',
            'idempotencyKey': body['idempotencyKey'],
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-14T00:00:00Z',
            'sources': [
              {'kind': 'company_db', 'ref': 'operations.founder_asset_events'},
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.cloneAsset(
      assetKind: FounderAssetKind.skill,
      sourceAssetId: 'skill.builtin.summary',
      sourceVersion: '1',
      reason: 'Tuỳ biến cho workspace',
    );

    expect(result, isA<ApiSuccess<FounderAssetCommandResult>>());
    final cmd = (result as ApiSuccess<FounderAssetCommandResult>).data;
    expect(cmd.operation, 'CLONE');
    expect(cmd.status, 'PENDING');
  });

  test('publishes a draft with the exact asset ref (id + version + hash)', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['operation'], 'PUBLISH');
      expect(body['assetRef'], {
        'assetId': 'skill.custom.summary',
        'version': '1',
        'definitionHash': 'sha256:abc',
      });

      return http.Response(
        jsonEncode({
          'data': {
            'commandId': 'cmd-2',
            'assetKind': 'SKILL',
            'operation': 'PUBLISH',
            'status': 'PENDING',
            'idempotencyKey': body['idempotencyKey'],
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-14T00:00:00Z',
            'sources': [
              {'kind': 'company_db', 'ref': 'operations.founder_asset_events'},
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.publishAsset(
      assetKind: FounderAssetKind.skill,
      assetId: 'skill.custom.summary',
      version: '1',
      expectedHash: 'sha256:abc',
      reason: 'Đã evaluate PASS',
    );

    expect(result, isA<ApiSuccess<FounderAssetCommandResult>>());
    expect((result as ApiSuccess<FounderAssetCommandResult>).data.operation, 'PUBLISH');
  });

  test('surfaces a hash-conflict error without retrying silently', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'message': 'expected_hash mismatch'}),
        409,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.publishAsset(
      assetKind: FounderAssetKind.skill,
      assetId: 'skill.custom.summary',
      version: '1',
      expectedHash: 'sha256:stale',
      reason: 'Đã evaluate PASS',
    );

    expect(result, isA<ApiFailure<FounderAssetCommandResult>>());
    final failure = result as ApiFailure<FounderAssetCommandResult>;
    expect(failure.failure.statusCode, 409);
    expect(failure.failure.code, ApiFailureCode.conflict);
  });

  // ── Task 9 (C2) — CLONE/EDIT_DRAFT/EVALUATE polling + workspace-agents ─────

  test('clones an AGENT with metadata name/description and an optional projectId', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/operations/founder/assets/commands');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['assetKind'], 'AGENT');
      expect(body['operation'], 'CLONE');
      expect(body['assetRef'], {'assetId': 'cosa.agents.operations'});
      expect(body['projectId'], 'proj-1');
      expect(body['metadata'], {'name': 'Vận hành gọn', 'description': 'Agent riêng'});

      return http.Response(
        jsonEncode({
          'commandId': 'cmd-agent-1',
          'assetKind': 'AGENT',
          'operation': 'CLONE',
          'status': 'PENDING',
          'idempotencyKey': body['idempotencyKey'],
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.cloneAsset(
      assetKind: FounderAssetKind.agent,
      sourceAssetId: 'cosa.agents.operations',
      reason: 'Tạo agent riêng',
      projectId: 'proj-1',
      metadata: {'name': 'Vận hành gọn', 'description': 'Agent riêng'},
    );

    expect(result, isA<ApiSuccess<FounderAssetCommandResult>>());
    expect((result as ApiSuccess<FounderAssetCommandResult>).data.commandId, 'cmd-agent-1');
  });

  test('edits a draft with the exact assetRef of the previous command', () async {
    final mockHttp = MockClient((request) async {
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['operation'], 'EDIT_DRAFT');
      expect(body['assetRef'], {'assetId': 'custom.operations.cmd-agent-1', 'version': '0.1.0', 'definitionHash': 'sha256:draft'});
      expect(body['metadata'], {'content': {'name': 'Vận hành gọn 2'}});

      return http.Response(
        jsonEncode({
          'commandId': 'cmd-agent-2',
          'assetKind': 'AGENT',
          'operation': 'EDIT_DRAFT',
          'status': 'PENDING',
          'idempotencyKey': body['idempotencyKey'],
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.editDraft(
      assetKind: FounderAssetKind.agent,
      assetRef: const FounderAssetRef(
        assetId: 'custom.operations.cmd-agent-1',
        version: '0.1.0',
        definitionHash: 'sha256:draft',
      ),
      content: const {'name': 'Vận hành gọn 2'},
      reason: 'Sửa tên',
    );

    expect(result, isA<ApiSuccess<FounderAssetCommandResult>>());
  });

  test('polls founder asset events and decodes status/safeReasonCode/updatedAssetRef', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/operations/founder/assets/events');
      expect(request.url.queryParameters['commandId'], 'cmd-agent-2');

      return http.Response(
        jsonEncode({
          'events': [
            {
              'id': 'cmd-agent-2',
              'metadata': {
                'status': 'REJECTED',
                'safeReasonCode': 'AGENT_CAPABILITY_ESCALATION',
                'updatedAssetRef': {
                  'assetId': 'custom.operations.cmd-agent-1',
                  'version': '0.1.0',
                  'definitionHash': 'sha256:edited',
                },
              },
            },
          ],
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.getEvents(commandId: 'cmd-agent-2');

    expect(result, isA<ApiSuccess<List<FounderAssetEvent>>>());
    final events = (result as ApiSuccess<List<FounderAssetEvent>>).data;
    expect(events, hasLength(1));
    expect(events.first.status, 'REJECTED');
    expect(events.first.isFailed, isTrue);
    expect(events.first.safeReasonCode, 'AGENT_CAPABILITY_ESCALATION');
    expect(events.first.updatedAssetRef?.definitionHash, 'sha256:edited');
  });

  test('creates a workspace agent from a published clone', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/operations/founder/assets/workspace-agents');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['agentAssetId'], 'custom.operations.cmd-agent-1');
      expect(body['agentAssetVersion'], '0.1.0');
      expect(body['agentDefinitionHash'], 'sha256:edited');

      return http.Response(
        jsonEncode({
          'id': 'wa-1',
          'agentAssetId': 'custom.operations.cmd-agent-1',
          'agentAssetVersion': '0.1.0',
          'agentDefinitionHash': 'sha256:edited',
          'originKind': 'WORKSPACE_CLONE',
          'state': 'ACTIVE',
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.createWorkspaceAgent(
      agentAssetId: 'custom.operations.cmd-agent-1',
      agentAssetVersion: '0.1.0',
      agentDefinitionHash: 'sha256:edited',
    );

    expect(result, isA<ApiSuccess<WorkspaceAgentDto>>());
    final dto = (result as ApiSuccess<WorkspaceAgentDto>).data;
    expect(dto.id, 'wa-1');
    expect(dto.originKind, 'WORKSPACE_CLONE');
  });
}
