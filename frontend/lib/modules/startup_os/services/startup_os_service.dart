import '../../../core/network/api_auth_resolver.dart';
import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/startup_os_models.dart';

/// Startup OS API (plan 2026-09-18 Phase 4). Company đọc `workspaceId` từ query
/// (GET) hoặc body (POST) — service luôn truyền tường minh từ workspace đang chọn.
/// Mọi lỗi trả về `ApiFailure` có mã rõ ràng; không có nhánh nào đổi lỗi thành
/// dữ liệu rỗng.
class StartupOsService {
  StartupOsService({MvpRequestClient? client, ApiAuthResolver? authResolver})
      : _client = client ?? MvpRequestClient(),
        _authResolver = authResolver ?? const DefaultApiAuthResolver();

  final MvpRequestClient _client;
  final ApiAuthResolver _authResolver;

  Future<String?> _workspaceId() => _authResolver.workspaceId();

  ApiResult<T> _missingWorkspace<T>() => const ApiFailure(
        ApiFailureDetail(code: ApiFailureCode.invalidRequest, message: 'Missing workspace context'),
      );

  Future<ApiResult<T>> _get<T>(MvpEndpoint endpoint, T Function(Object?) decode) async {
    final ws = await _workspaceId();
    if (ws == null || ws.isEmpty) return _missingWorkspace();
    return _client.request<T>(endpoint, query: {'workspaceId': ws}, decode: decode);
  }

  Future<ApiResult<T>> _post<T>(
    MvpEndpoint endpoint,
    Map<String, Object?> body,
    T Function(Object?) decode, {
    Map<String, String>? pathParams,
  }) async {
    final ws = await _workspaceId();
    if (ws == null || ws.isEmpty) return _missingWorkspace();
    return _client.request<T>(
      endpoint,
      pathParams: pathParams,
      body: {'workspaceId': ws, ...body},
      decode: decode,
    );
  }

  Future<ApiResult<List<GoalNode>>> getGoalTree() =>
      _get(MvpEndpoint.startupOsGoalTreeRead, goalTreeFromJson);

  Future<ApiResult<List<GoalNeedingReview>>> getGoalsNeedingReview() =>
      _get(MvpEndpoint.startupOsGoalsNeedingReviewRead, goalsNeedingReviewFromJson);

  Future<ApiResult<List<DimensionCadence>>> getCadenceStatus() =>
      _get(MvpEndpoint.startupOsOnboardCadenceRead, cadencesFromJson);

  /// Ngữ cảnh 7 chiều hiện tại (dùng để điền sẵn wizard). Giá trị null = chưa có.
  Future<ApiResult<Map<String, dynamic>>> getCompanyContext() =>
      _get(MvpEndpoint.startupOsOnboardContextRead, (raw) {
        if (raw is Map<String, dynamic> && raw['fullContext'] is Map<String, dynamic>) {
          return raw['fullContext'] as Map<String, dynamic>;
        }
        throw const FormatException('Invalid company context payload');
      });

  Future<ApiResult<List<PendingProject>>> listPendingProjects() =>
      _get(MvpEndpoint.startupOsPendingProjectsRead, pendingProjectsFromJson);

  Future<ApiResult<CreatedGoal>> createGoal({
    required String title,
    required GoalType goalType,
    String? parentId,
    String? description,
    String? startDate,
    String? endDate,
  }) =>
      _post(
        MvpEndpoint.startupOsGoalCreate,
        {
          'title': title,
          'goalType': goalType.name,
          'parentId': ?parentId,
          'description': ?description,
          'startDate': ?startDate,
          'endDate': ?endDate,
        },
        CreatedGoal.fromJson,
      );

  Future<ApiResult<void>> completeGoal(String goalId) => _post(
        MvpEndpoint.startupOsGoalComplete,
        const {},
        (_) {},
        pathParams: {'id': goalId},
      );

  Future<ApiResult<String>> startSession({required String sessionType, String? summary}) => _post(
        MvpEndpoint.startupOsOnboardSessionCreate,
        {'sessionType': sessionType, 'summary': ?summary},
        (raw) {
          final id = raw is Map<String, dynamic> ? raw['sessionId'] : null;
          if (id is String && id.isNotEmpty) return id;
          throw const FormatException('Onboard session response has no sessionId');
        },
      );

  Future<ApiResult<void>> updateDimension({
    required String sessionId,
    required String dimension,
    required Map<String, Object> data,
  }) =>
      _post(
        MvpEndpoint.startupOsOnboardDimensionUpdate,
        {'sessionId': sessionId, 'data': data},
        (_) {},
        pathParams: {'dimension': dimension},
      );

  Future<ApiResult<String>> createSnapshot({
    required String sessionId,
    required List<String> changedDimensions,
    String? changeReason,
  }) =>
      _post(
        MvpEndpoint.startupOsOnboardSnapshotCreate,
        {
          'sessionId': sessionId,
          'changedDimensions': changedDimensions,
          'changeReason': ?changeReason,
        },
        (raw) {
          final id = raw is Map<String, dynamic> ? raw['snapshotId'] : null;
          if (id is String && id.isNotEmpty) return id;
          throw const FormatException('Snapshot response has no snapshotId');
        },
      );

  Future<ApiResult<void>> triageProject({
    required String projectId,
    required TriageAction action,
    String? newGoalId,
    String? newObjectiveTitle,
  }) =>
      _post(
        MvpEndpoint.startupOsProjectTriageCreate,
        {
          'projectId': projectId,
          'action': action.wire,
          'newGoalId': ?newGoalId,
          'newObjectiveTitle': ?newObjectiveTitle,
        },
        (_) {},
      );
}
