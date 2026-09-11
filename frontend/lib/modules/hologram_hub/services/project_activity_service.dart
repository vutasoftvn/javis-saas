import 'package:frontend/modules/hologram_hub/models/project_activity_models.dart';

class ProjectActivityService {
  /// Fetch project activity events
  Future<List<ProjectActivityEvent>> fetch({
    required String projectId,
    int? afterSequence,
    List<String>? kinds,
    int limit = 50,
  }) async {
    // TODO: Implement API call to GET /agent/projects/{projectId}/activity
    // with filters and pagination
    return [];
  }

  /// Get details of a specific activity event
  Future<ProjectActivityEvent?> detail({
    required String projectId,
    required String eventId,
  }) async {
    // TODO: Implement API call to GET /agent/projects/{projectId}/activity/{eventId}
    return null;
  }

  /// Stream activity events with reconnect support
  Stream<ProjectActivityEvent> stream({
    required String projectId,
    int? afterSequence,
  }) async* {
    // TODO: Implement SSE stream from GET /agent/projects/{projectId}/activity/stream
    // with Last-Event-ID support for reconnect
  }
}
