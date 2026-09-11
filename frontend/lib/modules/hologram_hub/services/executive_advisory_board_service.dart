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

  /// Chọn preset Startup Core (startup-discovery hoặc startup-build-launch).
  Future<ApiResult<Map<String, dynamic>>> selectPreset({
    required String projectId,
    required String presetKey,
    String? idempotencyKey,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectExecutiveRolesSelectPreset,
      pathParams: {'projectId': projectId},
      body: {
        'presetKey': presetKey,
        'idempotencyKey': ?idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return raw;
        }
        throw const FormatException('Invalid response format for select preset');
      },
    );
  }

  /// Kích hoạt một vai trò cố vấn (Founder-only).
  Future<ApiResult<ExecutiveAdvisorRole>> activateRole({
    required String projectId,
    required String roleKey,
    required int expectedVersion,
    String? idempotencyKey,
  }) async {
    return _client.request<ExecutiveAdvisorRole>(
      MvpEndpoint.projectExecutiveRolesActivate,
      pathParams: {
        'projectId': projectId,
        'roleKey': roleKey,
      },
      body: {
        'expectedVersion': expectedVersion,
        'idempotencyKey': ?idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveAdvisorRole.fromJson(raw);
        }
        throw const FormatException('Invalid response format for activate executive role');
      },
    );
  }

  /// Vô hiệu hoá một vai trò cố vấn (Founder-only).
  Future<ApiResult<ExecutiveAdvisorRole>> disableRole({
    required String projectId,
    required String roleKey,
    required int expectedVersion,
    String? reason,
    String? idempotencyKey,
  }) async {
    return _client.request<ExecutiveAdvisorRole>(
      MvpEndpoint.projectExecutiveRolesDisable,
      pathParams: {
        'projectId': projectId,
        'roleKey': roleKey,
      },
      body: {
        'expectedVersion': expectedVersion,
        'reason': ?reason,
        'idempotencyKey': ?idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveAdvisorRole.fromJson(raw);
        }
        throw const FormatException('Invalid response format for disable executive role');
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
    bool? criticRequired,
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
        'criticRequired': ?criticRequired,
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
