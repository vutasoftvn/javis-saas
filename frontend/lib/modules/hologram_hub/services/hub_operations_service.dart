import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';

import '../models/hub_operations_models.dart';

List<Map<String, dynamic>> _items(Object? raw) {
  if (raw is Map<String, dynamic>) {
    final items = raw['items'];
    if (items is List) return items.whereType<Map<String, dynamic>>().toList();
  }
  throw const FormatException('Expected an object with an items array');
}

/// Gọi API cho card vận hành ở hub (Lịch, quyền agent). Task dùng
/// `ProjectOperatingLoopService`, agent dùng `ProjectStartupTeamService`, connector dùng
/// `SettingsMvpService` — không nhân bản các service đó ở đây.
class HubOperationsService {
  HubOperationsService({MvpRequestClient? client}) : _client = client ?? MvpRequestClient();

  final MvpRequestClient _client;

  /// Lịch của organization; lọc theo Project ở phía gọi (server chưa lọc theo Project).
  Future<ApiResult<List<HubSchedule>>> listSchedules() {
    return _client.request<List<HubSchedule>>(
      MvpEndpoint.hubSchedulesList,
      decode: (raw) => _items(raw).map(HubSchedule.fromJson).toList(),
    );
  }

  Future<ApiResult<void>> runScheduleNow(String scheduleId) {
    return _client.request<void>(
      MvpEndpoint.hubScheduleRunNow,
      pathParams: {'scheduleId': scheduleId},
      decode: (_) {},
    );
  }

  /// `state`: `enabled` | `paused` | `archived` (lưu trữ là trạng thái cuối).
  Future<ApiResult<HubSchedule>> setScheduleState(String scheduleId, String state) {
    return _client.request<HubSchedule>(
      MvpEndpoint.hubScheduleSetState,
      pathParams: {'scheduleId': scheduleId},
      body: {'state': state},
      decode: (raw) => HubSchedule.fromJson(raw as Map<String, dynamic>),
    );
  }

  Future<ApiResult<List<HubScheduleExecution>>> listScheduleExecutions(
    String scheduleId, {
    int limit = 5,
  }) {
    return _client.request<List<HubScheduleExecution>>(
      MvpEndpoint.hubScheduleExecutions,
      pathParams: {'scheduleId': scheduleId},
      query: {'limit': '$limit'},
      decode: (raw) => _items(raw).map(HubScheduleExecution.fromJson).toList(),
    );
  }

  Future<ApiResult<List<HubAgentGrant>>> listAgentGrants(String projectId) {
    return _client.request<List<HubAgentGrant>>(
      MvpEndpoint.projectAgentCapabilityGrantsRead,
      pathParams: {'projectId': projectId},
      decode: (raw) => _items(raw).map(HubAgentGrant.fromJson).toList(),
    );
  }
}
