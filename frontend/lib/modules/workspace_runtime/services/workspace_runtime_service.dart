import '../../../core/network/api_result.dart';
import 'workspace_runtime_mvp_client.dart';
import '../models/mvp_runtime_models.dart';

class WorkspaceRuntimeService {
  final WorkspaceRuntimeMvpClient _client;

  WorkspaceRuntimeService({WorkspaceRuntimeMvpClient? client})
      : _client = client ?? WorkspaceRuntimeMvpClient();

  Future<ApiResult<List<MvpRuntimeItem>>> getNeedsYouResult() async {
    return _client.listNeedsYou();
  }

  Future<List<dynamic>> getNeedsYou({bool includeSnoozed = false}) async {
    final res = await _client.listNeedsYou();
    if (res is ApiSuccess<List<MvpRuntimeItem>>) {
      return res.data.map((item) => {
        'id': item.id,
        'source_type': item.sourceRef.kind,
        'priority': item.severity,
        'requested_action': item.title,
        'reason': item.description ?? '',
        'created_at': item.createdAt,
        'observed_at': item.observedAt,
        'sourceKind': item.sourceKind,
        'sourceId': item.sourceId,
      }).toList();
    }
    return [];
  }

  Future<bool> resolveNeedsYou(String itemId) async {
    return true;
  }

  Future<ApiResult<void>> snoozeNeedsYouResult({
    required String sourceKind,
    required String sourceId,
    required DateTime until,
  }) async {
    return _client.snoozeItem(
      sourceKind: sourceKind,
      sourceId: sourceId,
      snoozedUntil: until.toUtc().toIso8601String(),
    );
  }

  Future<bool> snoozeNeedsYou(
    String itemId,
    DateTime until, {
    String sourceKind = 'task',
    String? sourceId,
  }) async {
    final actualSourceId = sourceId ?? (itemId.startsWith('need_') || itemId.startsWith('sig_') || itemId.startsWith('task_') ? itemId.split('_').last : itemId);
    final res = await _client.snoozeItem(
      sourceKind: sourceKind,
      sourceId: actualSourceId,
      snoozedUntil: until.toUtc().toIso8601String(),
    );
    return res is ApiSuccess;
  }

  Future<ApiResult<List<MvpRuntimeItem>>> getBlockersResult() async {
    return _client.listBlockers();
  }

  Future<List<dynamic>> getBlockers({String? status}) async {
    final res = await _client.listBlockers();
    if (res is ApiSuccess<List<MvpRuntimeItem>>) {
      return res.data.map((item) => {
        'id': item.id,
        'assigned_function': 'FOUNDER',
        'blocker_type': item.sourceRef.kind.toUpperCase(),
        'status': item.state,
        'priority': item.severity,
        'title': item.title,
        'reason': item.description ?? '',
        'created_at': item.createdAt,
        'sourceKind': item.sourceKind,
        'sourceId': item.sourceId,
      }).toList();
    }
    return [];
  }

  Future<bool> resolveBlocker(String blockerId, {String? resolutionArtifactId}) async {
    return true;
  }

  Future<ApiResult<MvpRuntimeItemDetail>> getWorkInspectorResult({
    required String sourceKind,
    required String sourceId,
  }) async {
    return _client.getItem(sourceKind: sourceKind, sourceId: sourceId);
  }

  Future<Map<String, dynamic>?> getWorkInspector(String taskId, {String sourceKind = 'task'}) async {
    final res = await _client.getItem(sourceKind: sourceKind, sourceId: taskId);
    if (res is ApiSuccess<MvpRuntimeItemDetail>) {
      final d = res.data;
      return {
        'id': d.id,
        'title': d.title,
        'description': d.description,
        'state': d.state,
        'severity': d.severity,
        'source_ref': d.sourceRef.ref,
        'payload': d.payload,
        'dependencies': d.dependencies,
      };
    }
    return null;
  }

  Future<ApiResult<List<MvpSourceStatus>>> getRuntimeStatusResult() async {
    return _client.getSourceStatus();
  }

  Future<Map<String, dynamic>?> getRuntimeStatus() async {
    final res = await _client.getSourceStatus();
    if (res is ApiSuccess<List<MvpSourceStatus>>) {
      return {
        'statuses': res.data.map((s) => {
          'source_kind': s.sourceKind,
          'plane': s.plane,
          'status': s.status,
          'last_observed_at': s.lastObservedAt,
        }).toList(),
      };
    }
    return null;
  }
}
