import '../../../core/network/api_auth_resolver.dart';
import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/organization_api_models.dart';

/// Organization API server-authoritative (spec 2026-09-25 §7). Thay các lời
/// gọi `/org/*` cũ (không có handler) — mọi lỗi 401/403/404/422 trả về
/// `ApiFailure` có mã rõ ràng thay vì bị nuốt thành `null`.
class OrganizationService {
  OrganizationService({MvpRequestClient? client, ApiAuthResolver? authResolver})
      : _client = client ?? MvpRequestClient(),
        _authResolver = authResolver ?? const DefaultApiAuthResolver();

  final MvpRequestClient _client;
  final ApiAuthResolver _authResolver;

  Future<String?> _organizationId() => _authResolver.workspaceId();

  Future<ApiResult<T>> _missingOrganization<T>() async => const ApiFailure(
        ApiFailureDetail(
          code: ApiFailureCode.invalidRequest,
          message: 'Missing organization context',
        ),
      );

  Future<ApiResult<OrganizationOverview>> getOverview() async {
    final orgId = await _organizationId();
    if (orgId == null || orgId.isEmpty) return _missingOrganization();
    return _client.request<OrganizationOverview>(
      MvpEndpoint.organizationOverviewRead,
      pathParams: {'organizationId': orgId},
      decode: (raw) {
        if (raw is Map<String, dynamic>) return OrganizationOverview.fromJson(raw);
        throw const FormatException('Invalid organization overview payload');
      },
    );
  }

  Future<ApiResult<OrganizationWorkforce>> listWorkforce() async {
    final orgId = await _organizationId();
    if (orgId == null || orgId.isEmpty) return _missingOrganization();
    return _client.request<OrganizationWorkforce>(
      MvpEndpoint.organizationWorkforceList,
      pathParams: {'organizationId': orgId},
      decode: (raw) {
        if (raw is Map<String, dynamic>) return OrganizationWorkforce.fromJson(raw);
        throw const FormatException('Invalid organization workforce payload');
      },
    );
  }

  /// Xếp một workspace agent đã publish vào sơ đồ tổ chức. Chỉ gửi id do
  /// server liệt kê + chức danh; không bao giờ gửi prompt/spec/capability.
  Future<ApiResult<OrganizationWorkforceMember>> placeAiWorkforce({
    required String workspaceAgentId,
    required String roleTitle,
    String? managerMemberId,
    required String idempotencyKey,
  }) async {
    final orgId = await _organizationId();
    if (orgId == null || orgId.isEmpty) return _missingOrganization();
    return _client.request<OrganizationWorkforceMember>(
      MvpEndpoint.organizationAiWorkforceCreate,
      pathParams: {'organizationId': orgId},
      body: {
        'workspaceAgentId': workspaceAgentId,
        'roleTitle': roleTitle,
        'managerMemberId': ?managerMemberId,
        'idempotencyKey': idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic> && raw['member'] is Map<String, dynamic>) {
          final member = OrganizationWorkforceMember.fromJson(
            raw['member'] as Map<String, dynamic>,
          );
          if (member.id.isEmpty) {
            throw const FormatException('AI workforce response has no durable member id');
          }
          return member;
        }
        throw const FormatException('Invalid AI workforce payload');
      },
    );
  }
}
