import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import '../models/executive_advisory_board.dart';

class ExecutiveAdvisoryBoardService {
  final MvpRequestClient _client;

  ExecutiveAdvisoryBoardService({MvpRequestClient? client})
      : _client = client ?? MvpRequestClient();

  /// Lấy danh sách 13 vai trò cố vấn điều hành cùng trạng thái activation cho Project.
  Future<ApiResult<List<ExecutiveAdvisorRole>>> fetchRoles(String projectId) async {
    return _client.request<List<ExecutiveAdvisorRole>>(
      MvpEndpoint.projectExecutiveRolesRead,
      pathParams: {'projectId': projectId},
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          final items = raw['roles'] as List<dynamic>? ?? [];
          return items
              .map((e) => ExecutiveAdvisorRole.fromJson(e as Map<String, dynamic>))
              .toList();
        }
        throw const FormatException('Invalid response format for executive roles');
      },
    );
  }

  /// Kích hoạt một vai trò cố vấn (Founder-only) — Workspace-scoped, ảnh
  /// hưởng tới mọi Project trong cùng workspace (xem Task 9: activation
  /// role không còn theo Project, không còn khái niệm preset).
  Future<ApiResult<ExecutiveRoleMutationReceipt>> activateRole({
    required String workspaceId,
    required String roleKey,
    required int expectedVersion,
    String? idempotencyKey,
  }) async {
    return _client.request<ExecutiveRoleMutationReceipt>(
      MvpEndpoint.operationsExecutiveBoardWorkspaceRoleActivate,
      pathParams: {
        'workspaceId': workspaceId,
        'roleKey': roleKey,
      },
      body: {
        'expectedVersion': expectedVersion,
        'idempotencyKey': ?idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveRoleMutationReceipt.fromJson(raw);
        }
        throw const FormatException('Invalid response format for activate executive role');
      },
    );
  }

  /// Vô hiệu hoá một vai trò cố vấn (Founder-only) — Workspace-scoped.
  Future<ApiResult<ExecutiveRoleMutationReceipt>> disableRole({
    required String workspaceId,
    required String roleKey,
    required int expectedVersion,
    String? reason,
    String? idempotencyKey,
  }) async {
    return _client.request<ExecutiveRoleMutationReceipt>(
      MvpEndpoint.operationsExecutiveBoardWorkspaceRoleDisable,
      pathParams: {
        'workspaceId': workspaceId,
        'roleKey': roleKey,
      },
      body: {
        'expectedVersion': expectedVersion,
        'reason': ?reason,
        'idempotencyKey': ?idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveRoleMutationReceipt.fromJson(raw);
        }
        throw const FormatException('Invalid response format for disable executive role');
      },
    );
  }

  /// Hội tụ bốn role P0 Core cho Project P0 có sẵn. Server giữ quyền quyết
  /// định availability và idempotency; client chỉ phát lệnh Founder explicit.
  Future<ApiResult<bool>> bootstrapP0Core({
    required String projectId,
  }) async {
    return _client.request<bool>(
      MvpEndpoint.operationsExecutiveBoardBootstrapP0Core,
      pathParams: {'projectId': projectId},
      body: const {},
      decode: (raw) {
        if (raw is Map<String, dynamic> && raw['projectId'] == projectId) {
          return true;
        }
        throw const FormatException('Invalid response format for P0 Core bootstrap');
      },
    );
  }

  /// Tạo bản nháp Deliberation.
  Future<ApiResult<ExecutiveDeliberation>> createDraft({
    required String projectId,
    required String title,
  }) async {
    return _client.request<ExecutiveDeliberation>(
      MvpEndpoint.projectDeliberationsDraft,
      pathParams: {'projectId': projectId},
      body: {'title': title},
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveDeliberation.fromJson(raw);
        }
        throw const FormatException('Invalid response format for create draft');
      },
    );
  }

  /// Đóng khung Deliberation và kích hoạt phân tích của các vai trò.
  Future<ApiResult<ExecutiveDeliberation>> frameDeliberation({
    required String projectId,
    required String deliberationId,
    required String question,
    required List<String> roleKeys,
    int? expectedVersion,
    String? deliberationType,
    String? deadline,
    String? idempotencyKey,
  }) async {
    return _client.request<ExecutiveDeliberation>(
      MvpEndpoint.projectDeliberationsFrame,
      pathParams: {
        'projectId': projectId,
        'deliberationId': deliberationId,
      },
      body: {
        'question': question,
        'roleKeys': roleKeys,
        'expectedVersion': ?expectedVersion,
        'deliberationType': ?deliberationType,
        'deadline': ?deadline,
        'idempotencyKey': ?idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveDeliberation.fromJson(raw);
        }
        throw const FormatException('Invalid response format for frame deliberation');
      },
    );
  }

  /// Lấy thông tin chi tiết một Deliberation (kèm active frame, analyses, decision).
  Future<ApiResult<ExecutiveDeliberation>> getDeliberation({
    required String projectId,
    required String deliberationId,
  }) async {
    return _client.request<ExecutiveDeliberation>(
      MvpEndpoint.projectDeliberationsRead,
      pathParams: {
        'projectId': projectId,
        'deliberationId': deliberationId,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveDeliberation.fromJson(raw);
        }
        throw const FormatException('Invalid response format for get deliberation');
      },
    );
  }

  /// Founder ghi nhận quyết định cuối cùng (APPROVE, MODIFY, REJECT, CANCEL, EXPIRE).
  Future<ApiResult<ExecutiveDeliberation>> appendDecision({
    required String projectId,
    required String deliberationId,
    required String decisionType,
    String? notes,
    Map<String, dynamic>? modifications,
    int? expectedVersion,
  }) async {
    return _client.request<ExecutiveDeliberation>(
      MvpEndpoint.projectDeliberationsDecision,
      pathParams: {
        'projectId': projectId,
        'deliberationId': deliberationId,
      },
      body: {
        'decisionType': decisionType,
        'notes': ?notes,
        'modifications': ?modifications,
        'expectedVersion': ?expectedVersion,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveDeliberation.fromJson(raw);
        }
        throw const FormatException('Invalid response format for append decision');
      },
    );
  }

  /// Huỷ Deliberation (Founder-only).
  Future<ApiResult<ExecutiveDeliberation>> cancelDeliberation({
    required String projectId,
    required String deliberationId,
    String? reason,
    int? expectedVersion,
  }) async {
    return _client.request<ExecutiveDeliberation>(
      MvpEndpoint.projectDeliberationsCancel,
      pathParams: {
        'projectId': projectId,
        'deliberationId': deliberationId,
      },
      body: {
        'reason': ?reason,
        'expectedVersion': ?expectedVersion,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveDeliberation.fromJson(raw);
        }
        throw const FormatException('Invalid response format for cancel deliberation');
      },
    );
  }
}
