import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';

/// Loại entity có lifecycle stage transition (Workspace W0..W5, Project P0..P6).
enum LifecycleEntityType { workspace, project }

/// Service dùng cho lifecycle transition và history của Workspace và Project.
/// Sử dụng MvpRequestClient và MvpEndpoint thay cho legacy WorkspaceService.
class LifecycleService {
  final MvpRequestClient _client;

  LifecycleService({MvpRequestClient? client})
      : _client = client ?? MvpRequestClient();

  static String pathFor(LifecycleEntityType type, String entityId) {
    switch (type) {
      case LifecycleEntityType.workspace:
        return '/identity/workspaces/$entityId/lifecycle';
      case LifecycleEntityType.project:
        return '/operations/projects/$entityId/lifecycle';
    }
  }

  /// GET `.../lifecycle/events` — trả `{ items: LifecycleEvent[] }`.
  Future<Map<String, dynamic>> getHistory(
    LifecycleEntityType type,
    String entityId,
  ) async {
    final endpoint = type == LifecycleEntityType.workspace
        ? MvpEndpoint.identityWorkspaceLifecycleEvents
        : MvpEndpoint.operationsProjectLifecycleEvents;
    final pathParams = type == LifecycleEntityType.workspace
        ? {'workspaceId': entityId}
        : {'projectId': entityId};

    final result = await _client.request<Map<String, dynamic>>(
      endpoint,
      pathParams: pathParams,
      decode: (raw) => raw as Map<String, dynamic>,
    );

    if (result.isSuccess) {
      return (result as ApiSuccess<Map<String, dynamic>>).data;
    }
    final failure = result.failureOrNull;
    throw StateError(
      'Failed to load lifecycle history: ${failure?.code} ${failure?.message}',
    );
  }

  /// PATCH `.../lifecycle` — chuyển stage với optimistic locking qua expectedStageVersion.
  Future<Map<String, dynamic>> transition(
    LifecycleEntityType type,
    String entityId, {
    required String toStage,
    required int expectedStageVersion,
    String? rationale,
  }) async {
    final endpoint = type == LifecycleEntityType.workspace
        ? MvpEndpoint.identityWorkspaceLifecycleTransition
        : MvpEndpoint.operationsProjectLifecycleTransition;
    final pathParams = type == LifecycleEntityType.workspace
        ? {'workspaceId': entityId}
        : {'projectId': entityId};

    final body = <String, dynamic>{
      'toStage': toStage,
      'expectedStageVersion': expectedStageVersion,
      'rationale': ?rationale,
    };

    final result = await _client.request<Map<String, dynamic>>(
      endpoint,
      pathParams: pathParams,
      body: body,
      decode: (raw) => raw as Map<String, dynamic>,
    );

    if (result.isSuccess) {
      return (result as ApiSuccess<Map<String, dynamic>>).data;
    }
    final failure = result.failureOrNull;
    throw StateError(
      'Failed to transition lifecycle: ${failure?.code} ${failure?.message}',
    );
  }
}
