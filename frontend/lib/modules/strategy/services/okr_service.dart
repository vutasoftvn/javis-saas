// Founder Trial R1 — OKR/12WY module is PLANNED; every request here returns
// ApiClient.removed(). Shell kept so cards/controllers still compile.
// ignore_for_file: unused_local_variable, unused_field, unused_element
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
      final response = await ApiClient.removed('r1-removed:/operations/okr-cycles');
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
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.removed('r1-removed:/operations/okr-cycles');
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
      final response = await ApiClient.removed('r1-removed:/operations/objectives$query');
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
    String? strategicObjectiveId,
    String? towsOptionId,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.removed('r1-removed:/operations/objectives');
    return decode(response);
  }

  Future<Map<String, dynamic>> publishObjective(String objectiveId) async {
    final response = await ApiClient.removed('r1-removed:/operations/objectives/$objectiveId/publish');
    return decode(response);
  }

  Future<Map<String, dynamic>> updateObjective(
    String objectiveId, {
    String? title,
    String? status,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.removed('r1-removed:/operations/objectives/$objectiveId?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<void> deleteObjective(String objectiveId) async {
    await requireWorkspaceId();
    final response = await ApiClient.removed('r1-removed:/operations/objectives/$objectiveId');
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
    if (objectiveId != null && objectiveId.isNotEmpty) {
      try {
        final response = await ApiClient.removed('r1-removed:/operations/objectives/$objectiveId');
        if (response.statusCode >= 200 && response.statusCode < 300) {
          final data = jsonDecode(response.body);
          final krsRaw = data['keyResults'] ?? data['key_results'];
          if (krsRaw is List) {
            final items = krsRaw
                .map(
                  (e) => e is Map<String, dynamic>
                      ? e
                      : Map<String, dynamic>.from(e as Map),
                )
                .toList();
            return StrategyListResult.success(items);
          }
        }
      } catch (_) {}
    }
    final query = objectiveId != null ? '?objective_id=$objectiveId' : '';
    try {
      final response = await ApiClient.removed('r1-removed:/operations/key-results$query');
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
    final response = await ApiClient.removed('r1-removed:/operations/objectives/$objectiveId/key-results');
    return decode(response);
  }

  Future<Map<String, dynamic>> checkinKeyResult(
    String keyResultId,
    double value,
  ) async {
    final response = await ApiClient.removed('r1-removed:/operations/key-results/$keyResultId/checkin');
    return decode(response);
  }

  Future<Map<String, dynamic>> updateKeyResult(
    String keyResultId, {
    double? currentValue,
    double? targetValue,
    String? unit,
    String? status,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.removed('r1-removed:/operations/key-results/$keyResultId?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<void> deleteKeyResult(String keyResultId) async {
    await requireWorkspaceId();
    final response = await ApiClient.removed('r1-removed:/operations/key-results/$keyResultId');
    decode(response);
  }

  Future<Map<String, dynamic>> generateAiOkrs({
    String? towsId,
    int objectivesCount = 2,
    int krsPerObjectiveCount = 3,
    String? cycleId,
  }) {
    throw UnsupportedError(
      'Sinh OKR bằng AI chưa có capability đã được phê duyệt ở backend.',
    );
  }
}
