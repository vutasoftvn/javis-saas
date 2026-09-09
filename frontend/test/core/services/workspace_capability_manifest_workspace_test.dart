import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/services/workspace_capability_manifest_controller.dart';
import 'package:frontend/core/services/workspace_capability_manifest_model.dart';
import 'package:frontend/core/services/workspace_capability_manifest_service.dart';

class _FakeApi implements WorkspaceCapabilityManifestApi {
  _FakeApi({this.workspaceId = 'ws-a', this.fail = false});
  String workspaceId;
  bool fail;
  int calls = 0;

  @override
  Future<ApiResult<WorkspaceCapabilityManifest>> fetch() async {
    calls++;
    if (fail) {
      return const ApiFailure(
        ApiFailureDetail(code: ApiFailureCode.unavailable, message: 'boom'),
      );
    }
    return ApiSuccess(
      data: WorkspaceCapabilityManifest.fromJson({
        'version': 'v1',
        'workspaceId': workspaceId,
        'surfaces': [
          {
            'surfaceKey': 'founder_trial.board',
            'moduleKey': 'strategy',
            'featureKey': 'founder_trial_board',
            'surfaceStatus': 'AVAILABLE',
            'requiredCapabilities': const ['strategy.founder_trial.board.read'],
            'requiredConnectorKeys': const [],
            'entitled': true,
            'reasons': const [],
            'contractEndpoint': 'strategy.founder_trial.board.read',
            'releaseNote': null,
            'updatedAt': '2026-09-10T00:00:00.000Z',
          },
        ],
      }),
      meta: ApiResponseMeta(
        dataState: ApiDataState.populated,
        observedAt: DateTime.now(),
        sources: const [],
      ),
    );
  }
}

void main() {
  test('workspace switch clears the old manifest before the next response', () async {
    final api = _FakeApi(workspaceId: 'ws-a');
    final c = WorkspaceCapabilityManifestController(service: api);

    await c.reloadForWorkspace('ws-a');
    expect(c.statusFor('founder_trial.board'), SurfaceStatus.available);

    c.beginWorkspaceSwitch('ws-b');
    expect(c.currentWorkspaceId, 'ws-b');
    expect(c.hasLoadedSnapshot.value, isFalse);
    expect(c.statusFor('founder_trial.board'), SurfaceStatus.unavailable);
  });

  test('a response for a non-current workspace is ignored (stale switch race)', () async {
    final api = _FakeApi(workspaceId: 'ws-a');
    final c = WorkspaceCapabilityManifestController(service: api);

    // Target ws-b but the backend replies with ws-a's manifest.
    await c.reloadForWorkspace('ws-b');
    expect(c.statusFor('founder_trial.board'), SurfaceStatus.unavailable);
    expect(c.hasLoadedSnapshot.value, isFalse);

    // Now the correct ws-b manifest lands.
    api.workspaceId = 'ws-b';
    await c.reloadForWorkspace('ws-b');
    expect(c.statusFor('founder_trial.board'), SurfaceStatus.available);
  });

  test('logout via clear() drops both the snapshot and the target workspace', () async {
    final api = _FakeApi(workspaceId: 'ws-a');
    final c = WorkspaceCapabilityManifestController(service: api);
    await c.reloadForWorkspace('ws-a');
    expect(c.statusFor('founder_trial.board'), SurfaceStatus.available);

    c.clear();
    expect(c.currentWorkspaceId, isNull);
    expect(c.hasLoadedSnapshot.value, isFalse);
    expect(c.statusFor('founder_trial.board'), SurfaceStatus.unavailable);
  });

  test('a manifest HTTP failure stays fail-closed with the error surfaced', () async {
    final api = _FakeApi(fail: true);
    final c = WorkspaceCapabilityManifestController(service: api);
    await c.reloadForWorkspace('ws-a');
    expect(c.hasLoadedSnapshot.value, isFalse);
    expect(c.lastError.value, 'boom');
    expect(c.statusFor('founder_trial.board'), SurfaceStatus.unavailable);
  });
}
