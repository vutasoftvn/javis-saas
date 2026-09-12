import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/hologram_hub/controllers/executive_advisory_board_controller.dart';
import 'package:frontend/modules/hologram_hub/models/executive_advisory_board.dart';
import 'package:frontend/modules/hologram_hub/services/executive_advisory_board_service.dart';

/// Fake service không gọi HTTP thật — chỉ đếm số lần gọi và trả về response
/// giả lập giống hệt shape Company thật trả về: mutation receipt RÚT GỌN
/// (chỉ {id, roleKey, state, version}) từ endpoint activate, và role đầy đủ
/// (title, capabilities, domain...) từ endpoint fetch roles.
class _RecordingService extends ExecutiveAdvisoryBoardService {
  int fetchRolesCallCount = 0;
  int activateRoleCallCount = 0;

  final ApiResult<ExecutiveRoleMutationReceipt> activateResult;
  final ApiResult<List<ExecutiveAdvisorRole>> fetchRolesResult;

  _RecordingService({
    required this.activateResult,
    required this.fetchRolesResult,
  });

  @override
  Future<ApiResult<List<ExecutiveAdvisorRole>>> fetchRoles(String projectId) async {
    fetchRolesCallCount += 1;
    return fetchRolesResult;
  }

  @override
  Future<ApiResult<ExecutiveRoleMutationReceipt>> activateRole({
    required String projectId,
    required String roleKey,
    required int expectedVersion,
    String? idempotencyKey,
  }) async {
    activateRoleCallCount += 1;
    return activateResult;
  }
}

ApiResponseMeta _meta() => ApiResponseMeta(
      dataState: ApiDataState.populated,
      observedAt: DateTime.parse('2026-09-11T12:00:00Z'),
      sources: const [ApiSourceRef(kind: 'company_db', ref: 'operating')],
    );

void main() {
  test(
    'activateRole reloads full role list instead of trusting the abbreviated mutation receipt',
    () async {
      // Mutation receipt CHỈ có {id, roleKey, state, version} — không có
      // title/domain/capabilities/activationState đầy đủ của một role thật.
      final receipt = ExecutiveRoleMutationReceipt(
        id: 'mut-cpo-1',
        roleKey: 'cpo',
        state: 'ACTIVE',
        version: 2,
      );

      // Role đầy đủ mà Company trả về khi gọi lại fetchRoles sau mutation.
      final fullCpoRole = ExecutiveAdvisorRole(
        roleKey: 'cpo',
        title: 'CPO Advisor',
        domain: 'product',
        advisoryLevel: 'L1',
        description: 'Định hướng sản phẩm và ưu tiên roadmap',
        capabilities: const ['read_data', 'propose_roadmap'],
        activationState: ExecutiveActivationState.active,
        underlyingProfileKey: 'product',
        assignmentStatus: 'ACTIVE',
        specHash: 'hash-cpo',
        assignmentVersion: 2,
      );

      final service = _RecordingService(
        activateResult: ApiSuccess(data: receipt, meta: _meta()),
        fetchRolesResult: ApiSuccess(data: [fullCpoRole], meta: _meta()),
      );

      final controller = ExecutiveAdvisoryBoardController(service: service);

      final ok = await controller.activateRole(
        projectId: 'proj-101',
        roleKey: 'cpo',
        expectedVersion: 1,
      );

      expect(ok, isTrue);
      // Reload phải thật sự gọi lại fetchRoles — không chỉ dùng receipt.
      expect(service.activateRoleCallCount, 1);
      expect(service.fetchRolesCallCount, 1);

      // Role trong controller phải là bản đầy đủ từ fetchRoles (có title,
      // capabilities...), không phải shape rút gọn của mutation receipt.
      expect(controller.roles, hasLength(1));
      final cpo = controller.roles.first;
      expect(cpo.roleKey, 'cpo');
      expect(cpo.title, 'CPO Advisor');
      expect(cpo.underlyingProfileKey, 'product');
      expect(cpo.activationState, ExecutiveActivationState.active);
      expect(cpo.capabilities, contains('propose_roadmap'));
    },
  );
}
