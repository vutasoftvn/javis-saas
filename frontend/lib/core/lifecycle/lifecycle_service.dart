import 'dart:convert';
import 'package:http/http.dart' as http;
import '../network/api_client.dart';
import '../network/workspace_scoped_service.dart';

/// Task 12 — loại entity có lifecycle stage transition (Workspace W0..W5,
/// Project P0..P6). Dùng enum thay vì string để `pathFor` không thể lệch
/// route theo lỗi chính tả — cả 2 backend endpoint đã live, không cần thêm
/// biến thể entity type nào khác ở đây.
enum LifecycleEntityType { workspace, project }

/// Task 12 — service dùng chung cho lifecycle transition/history của cả
/// Workspace (`services/company/identity/handlers/workspace-lifecycle.handler.ts`)
/// và Project (`services/company/operations/handlers/project-lifecycle.handler.ts`).
/// Backend chỉ có PATCH (transition, trả state mới) + GET `.../events`
/// (lịch sử) — KHÔNG có endpoint GET lifecycle hiện tại riêng, nên service
/// này không expose `getState` (interface line trong task brief liệt kê
/// `getState` nhưng Step 3 — nguồn thật khớp backend — không có; đã verify
/// lại 2 handler file thật, không phỏng đoán theo doc).
class LifecycleService extends WorkspaceService {
  static String pathFor(LifecycleEntityType type, String entityId) {
    switch (type) {
      case LifecycleEntityType.workspace:
        return '/identity/workspaces/$entityId/lifecycle';
      case LifecycleEntityType.project:
        return '/operations/projects/$entityId/lifecycle';
    }
  }

  /// GET `.../lifecycle/events` — backend trả `{ items: LifecycleEvent[] }`,
  /// không phải mảng trần, nên trả `Map` (giữ nguyên wrapper) thay vì ép về
  /// `List` như doc line ở đầu task brief (đã lệch so với response shape thật).
  ///
  /// Dùng path literal đầy đủ (không nội suy qua `pathFor`) để contract-checker
  /// nhận diện đúng 2 route thật trong `mvp-surface.json` — nội suy method call
  /// bị checker flatten thành `:pathFor`, không khớp manifest.
  Future<Map<String, dynamic>> getHistory(LifecycleEntityType type, String entityId) async {
    final http.Response response;
    if (type == LifecycleEntityType.workspace) {
      response = await ApiClient.get('/identity/workspaces/$entityId/lifecycle/events');
    } else {
      response = await ApiClient.get('/operations/projects/$entityId/lifecycle/events');
    }
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    }
    throw StateError('Failed to load lifecycle history: ${response.statusCode} ${response.body}');
  }

  /// PATCH `.../lifecycle` — chuyển stage, bind `expectedStageVersion` để
  /// backend optimistic-lock chặn double-transition (đọc stale version rồi
  /// ghi đè lên transition khác đã xảy ra song song).
  Future<Map<String, dynamic>> transition(
    LifecycleEntityType type,
    String entityId, {
    required String toStage,
    required int expectedStageVersion,
    String? rationale,
  }) async {
    final response = await ApiClient.patch(
      pathFor(type, entityId),
      body: {
        'toStage': toStage,
        'expectedStageVersion': expectedStageVersion,
        'rationale': ?rationale,
      },
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    }
    throw StateError('Failed to transition lifecycle: ${response.statusCode} ${response.body}');
  }
}
