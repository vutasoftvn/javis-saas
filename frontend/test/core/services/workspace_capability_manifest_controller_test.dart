import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/services/workspace_capability_manifest_controller.dart';
import 'package:frontend/core/services/workspace_capability_manifest_model.dart';
import 'package:frontend/core/services/workspace_capability_manifest_service.dart';

class _FakeApi implements WorkspaceCapabilityManifestApi {
  _FakeApi(this.result);
  ApiResult<WorkspaceCapabilityManifest> result;
  int calls = 0;

  @override
  Future<ApiResult<WorkspaceCapabilityManifest>> fetch() async {
    calls++;
    return result;
  }
}

ApiResult<WorkspaceCapabilityManifest> _ok(List<Map<String, dynamic>> surfaces) {
  return ApiSuccess(
    data: WorkspaceCapabilityManifest.fromJson({
      'version': '2026-09-09.1',
      'workspaceId': 'ws1',
      'surfaces': surfaces,
    }),
    meta: ApiResponseMeta(
      dataState: ApiDataState.populated,
      observedAt: DateTime.now(),
      sources: const [],
    ),
  );
}

Map<String, dynamic> _surface(String key, String status) => {
      'surfaceKey': key,
      'moduleKey': 'strategy',
      'featureKey': key,
      'surfaceStatus': status,
      'requiredCapabilities': const [],
      'requiredConnectorKeys': const [],
      'entitled': true,
      'reasons': const [],
      'contractEndpoint': null,
      'releaseNote': null,
      'updatedAt': '2026-09-09T00:00:00.000Z',
    };

void main() {
  test('fails closed to UNAVAILABLE before any snapshot is loaded', () {
    final c = WorkspaceCapabilityManifestController(
      service: _FakeApi(_ok([_surface('founder_trial.board', 'AVAILABLE')])),
    );
    expect(c.hasLoadedSnapshot.value, isFalse);
    expect(c.statusFor('founder_trial.board'), SurfaceStatus.unavailable);
    expect(c.isInteractive('founder_trial.board'), isFalse);
  });

  test('maps all five statuses from the manifest', () async {
    final c = WorkspaceCapabilityManifestController(
      service: _FakeApi(_ok([
        _surface('a.available', 'AVAILABLE'),
        _surface('b.pilot', 'PILOT'),
        _surface('c.planned', 'PLANNED'),
        _surface('d.config', 'CONFIGURATION_REQUIRED'),
        _surface('e.unavailable', 'UNAVAILABLE'),
      ])),
    );
    await c.reload();
    expect(c.hasLoadedSnapshot.value, isTrue);
    expect(c.statusFor('a.available'), SurfaceStatus.available);
    expect(c.statusFor('b.pilot'), SurfaceStatus.pilot);
    expect(c.statusFor('c.planned'), SurfaceStatus.planned);
    expect(c.statusFor('d.config'), SurfaceStatus.configurationRequired);
    expect(c.statusFor('e.unavailable'), SurfaceStatus.unavailable);
    // Surface not in manifest → fail closed.
    expect(c.statusFor('z.unknown'), SurfaceStatus.unavailable);
    expect(c.isInteractive('a.available'), isTrue);
    expect(c.isInteractive('b.pilot'), isTrue);
    expect(c.isInteractive('c.planned'), isFalse);
  });

  test('an unknown wire status decodes to UNAVAILABLE, not a guess', () async {
    final c = WorkspaceCapabilityManifestController(
      service: _FakeApi(_ok([_surface('x.weird', 'SOMETHING_NEW')])),
    );
    await c.reload();
    expect(c.statusFor('x.weird'), SurfaceStatus.unavailable);
  });

  test('a failed request keeps the controller fail-closed with an error', () async {
    final c = WorkspaceCapabilityManifestController(
      service: _FakeApi(const ApiFailure(
        ApiFailureDetail(code: ApiFailureCode.unavailable, message: 'boom'),
      )),
    );
    await c.reload();
    expect(c.hasLoadedSnapshot.value, isFalse);
    expect(c.lastError.value, 'boom');
    expect(c.statusFor('anything'), SurfaceStatus.unavailable);
  });

  test('clear() drops the snapshot and returns to fail-closed', () async {
    final c = WorkspaceCapabilityManifestController(
      service: _FakeApi(_ok([_surface('founder_trial.board', 'AVAILABLE')])),
    );
    await c.reload();
    expect(c.statusFor('founder_trial.board'), SurfaceStatus.available);
    c.clear();
    expect(c.hasLoadedSnapshot.value, isFalse);
    expect(c.statusFor('founder_trial.board'), SurfaceStatus.unavailable);
  });
}
