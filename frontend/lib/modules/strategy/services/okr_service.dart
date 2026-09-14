// OKR module nối API thật (2026-09-14) — backend operations/handlers/okr.handler.ts
// đã sống, xem docs/superpowers/specs/2026-09-14-...-design.md mục 2.
import 'dart:convert';
import 'package:get/get.dart';
import '../../../core/localization/app_translations.dart';
import '../../../core/network/api_client.dart';
import '../models/strategy_list_result.dart';
import 'strategy_service_base.dart';

/// OKRs & Key Results service using operating-strategy routes
class OkrService extends StrategyServiceBase {
  StrategyListResult<Map<String, dynamic>> _decodeFlexibleList(
    dynamic response,
    String key, {
    bool optionalOn404 = false,
  }) {
    if (response.statusCode == 404) {
      if (optionalOn404) return const StrategyListResult.unavailable();
      return StrategyListResult.failure('Không tìm thấy dữ liệu (404)');
    }
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return const StrategyListResult.success([]);
      try {
        final data = jsonDecode(response.body);
        if (data is List) {
          final items = data
              .map(
                (e) => e is Map<String, dynamic>
                    ? e
                    : Map<String, dynamic>.from(e as Map),
              )
              .toList();
          return StrategyListResult.success(items);
        }
        if (data is Map) {
          final rawList =
              data[key] ??
              data['data'] ??
              data['items'] ??
              data['cycles'] ??
              data['objectives'] ??
              data['key_results'];
          if (rawList is List) {
            final items = rawList
                .map(
                  (e) => e is Map<String, dynamic>
                      ? e
                      : Map<String, dynamic>.from(e as Map),
                )
                .toList();
            return StrategyListResult.success(items);
          }
        }
        return StrategyListResult.failure(L10nKey.errBadFormat.tr);
      } catch (_) {
        return StrategyListResult.failure(L10nKey.errParseFailed.tr);
      }
    }
    return StrategyListResult.failure('${L10nKey.errRequestFailed.tr} (${response.statusCode})');
  }

  Future<StrategyListResult<Map<String, dynamic>>> getOkrCycles() async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return StrategyListResult.failure(L10nKey.errNoWorkspace.tr);
    }
    try {
      final response = await ApiClient.get('/operations/okr-cycles');
      return _decodeFlexibleList(response, 'cycles');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createOkrCycle({
    required String name,
    DateTime? startDate,
    DateTime? endDate,
    String? status,
  }) async {
    await requireWorkspaceId();
    final response = await ApiClient.post('/operations/okr-cycles', body: {
      'name': name,
      'startDate': ?startDate?.toUtc().toIso8601String(),
      'endDate': ?endDate?.toUtc().toIso8601String(),
      'status': ?status,
    });
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getObjectives({
    String? cycleId,
  }) async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure(
        'Chưa xác định workspace hiện tại',
      );
    }
    try {
      final query = (cycleId != null && cycleId.isNotEmpty)
          ? '?cycle_id=$cycleId'
          : '';
      final response = await ApiClient.get('/operations/objectives$query');
      final result = _decodeFlexibleList(response, 'objectives');
      if (cycleId != null && cycleId.isNotEmpty && result.isSuccess) {
        final filtered = result.items
            .where(
              (o) =>
                  o['cycleId']?.toString() == cycleId ||
                  o['cycle_id']?.toString() == cycleId,
            )
            .toList();
        return StrategyListResult.success(filtered);
      }
      return result;
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createObjective({
    required String title,
    String? cycleId,
    String? status,
    String? why,
    String? ownerMemberId,
  }) async {
    await requireWorkspaceId();
    final response = await ApiClient.post('/operations/objectives', body: {
      'title': title,
      'cycleId': ?cycleId,
      'status': ?status,
      'why': ?why,
      'ownerMemberId': ?ownerMemberId,
    });
    return decode(response);
  }

  Future<Map<String, dynamic>> publishObjective(String objectiveId) async {
    final response = await ApiClient.post('/operations/objectives/$objectiveId/publish');
    return decode(response);
  }

  Future<Map<String, dynamic>> updateObjective(
    String objectiveId, {
    String? title,
    String? status,
  }) async {
    await requireWorkspaceId();
    // ApiClient tự gắn header X-Workspace-Id — không còn cần query
    // ?workspace_id= thủ công (xem ApiClient._getHeaders).
    final response = await ApiClient.put('/operations/objectives/$objectiveId', body: {
      'title': ?title,
      'status': ?status,
    });
    return decode(response);
  }

  Future<void> deleteObjective(String objectiveId) async {
    await requireWorkspaceId();
    final response = await ApiClient.delete('/operations/objectives/$objectiveId');
    decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getKeyResults({
    String? objectiveId,
  }) async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure(
        'Chưa xác định workspace hiện tại',
      );
    }
    final query = objectiveId != null ? '?objective_id=$objectiveId' : '';
    try {
      final response = await ApiClient.get('/operations/key-results$query');
      return _decodeFlexibleList(response, 'key_results');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createKeyResult({
    required String objectiveId,
    String? title,
    double? baselineValue,
    double? currentValue,
    double? targetValue,
    String? unit,
    String? cadence,
    String? status,
    String? scoringType,
  }) async {
    await requireWorkspaceId();
    final response = await ApiClient.post('/operations/objectives/$objectiveId/key-results', body: {
      'title': ?title,
      'baselineValue': ?baselineValue,
      'currentValue': ?currentValue,
      'targetValue': ?targetValue,
      'unit': ?unit,
      'cadence': ?cadence,
      'status': ?status,
      'scoringType': ?scoringType,
    });
    return decode(response);
  }

  Future<Map<String, dynamic>> checkinKeyResult(
    String keyResultId,
    double value,
  ) async {
    final response = await ApiClient.post('/operations/key-results/$keyResultId/checkin', body: {
      'value': value,
    });
    return decode(response);
  }

  Future<Map<String, dynamic>> updateKeyResult(
    String keyResultId, {
    double? currentValue,
    double? targetValue,
    String? unit,
    String? status,
  }) async {
    await requireWorkspaceId();
    // ApiClient tự gắn header X-Workspace-Id — không còn cần query
    // ?workspace_id= thủ công (xem ApiClient._getHeaders).
    final response = await ApiClient.put('/operations/key-results/$keyResultId', body: {
      'currentValue': ?currentValue,
      'targetValue': ?targetValue,
      'unit': ?unit,
      'status': ?status,
    });
    return decode(response);
  }

  Future<void> deleteKeyResult(String keyResultId) async {
    await requireWorkspaceId();
    final response = await ApiClient.delete('/operations/key-results/$keyResultId');
    decode(response);
  }

  Future<Map<String, dynamic>> generateAiOkrs({
    int objectivesCount = 2,
    int krsPerObjectiveCount = 3,
    String? cycleId,
  }) {
    throw UnsupportedError(
      'Sinh OKR bằng AI chưa có capability đã được phê duyệt ở backend.',
    );
  }
}
