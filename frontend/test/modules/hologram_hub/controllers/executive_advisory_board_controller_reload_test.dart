import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/hologram_hub/controllers/executive_advisory_board_controller.dart';
import 'package:frontend/modules/hologram_hub/models/executive_advisory_board.dart';
import 'package:frontend/modules/hologram_hub/services/executive_advisory_board_service.dart';

class _Service extends ExecutiveAdvisoryBoardService {
  int calls = 0;
  String? fetchedProjectId;
  @override Future<ApiResult<ExecutiveRoleMutationReceipt>> activateRole({required String workspaceId, required String roleKey, required int expectedVersion, String? idempotencyKey}) async => ApiSuccess(data: const ExecutiveRoleMutationReceipt(id: 'm', roleKey: 'cfo', state: 'ACTIVE', version: 2), meta: _meta());
  @override Future<ApiResult<List<ExecutiveAdvisorRole>>> fetchRoles(String projectId) async { calls++; fetchedProjectId = projectId; return ApiSuccess(data: const [], meta: _meta()); }
}

class _ConflictService extends _Service {
  @override
  Future<ApiResult<ExecutiveRoleMutationReceipt>> activateRole({
    required String workspaceId,
    required String roleKey,
    required int expectedVersion,
    String? idempotencyKey,
  }) async => const ApiFailure(ApiFailureDetail(
    code: ApiFailureCode.conflict,
    statusCode: 409,
    message: 'Workspace office version is stale',
  ));
}
ApiResponseMeta _meta() => ApiResponseMeta(dataState: ApiDataState.populated, observedAt: DateTime.parse('2026-09-15T00:00:00Z'), sources: const []);
void main() {
  test('workspace office mutation refreshes Project effective state', () async {
    final service = _Service();
    final ok = await ExecutiveAdvisoryBoardController(service: service).activateRole(workspaceId: 'ws', projectId: 'project', roleKey: 'cfo', expectedVersion: 1);
    expect(ok, isTrue); expect(service.calls, 1); expect(service.fetchedProjectId, 'project');
  });
  test('stale Workspace office CAS leaves Project state untouched and exposes the conflict', () async {
    final service = _ConflictService();
    final controller = ExecutiveAdvisoryBoardController(service: service);
    final ok = await controller.activateRole(workspaceId: 'ws', projectId: 'project', roleKey: 'cfo', expectedVersion: 1);
    expect(ok, isFalse);
    expect(service.calls, 0);
    expect(controller.errorMessage.value, 'Workspace office version is stale');
  });
}
