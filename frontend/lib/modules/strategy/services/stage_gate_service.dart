import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../data/models/stage_gate_model.dart';
import '../../../core/network/api_client.dart';

class StageGateService {
  /// Thực hiện phiên thẩm định chuyển giai đoạn (Stage Gate Audit / Evaluation)
  Future<StageGateAuditModel?> auditStageReadiness({
    required dynamic projectId,
    dynamic workspaceId,
    dynamic companyId,
    dynamic stagePolicyId,
    String? targetStage,
  }) async {
    try {
      final wId = workspaceId?.toString() ?? '1';
      final cId = companyId?.toString() ?? '1';
      final pId = stagePolicyId?.toString() ?? '1';

      final response = await ApiClient.post(
        '/operations/strategy/gate-evaluations',
        body: {
          'workspaceId': wId,
          'companyId': cId,
          'projectId': projectId?.toString() ?? '1',
          'stagePolicyId': pId,
          'humanOverride': false,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return StageGateAuditModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[StageGateService] auditStageReadiness error: $e');
    }
    return null;
  }

  /// Lấy lịch sử các phiên thẩm định
  Future<List<StageGateAuditModel>> getAuditHistory(dynamic projectId, {dynamic workspaceId}) async {
    try {
      final pId = projectId?.toString() ?? '1';
      final queryParams = <String>['projectId=$pId'];
      if (workspaceId != null) queryParams.add('workspaceId=${workspaceId.toString()}');
      final response = await ApiClient.get('/operations/strategy/gate-evaluations?${queryParams.join('&')}');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is List ? data : (data['evaluations'] as List? ?? []);
        return list
            .map((item) => StageGateAuditModel.fromJson(item as Map<String, dynamic>))
            .toList();
      }
    } catch (e) {
      debugPrint('[StageGateService] getAuditHistory error: $e');
    }
    return [];
  }

  /// Quét và lấy danh sách cảnh báo Anti-Premature Scaling
  Future<List<PrematureAlertModel>> getGuardrailAlerts(dynamic projectId) async {
    try {
      final pId = projectId?.toString() ?? '1';
      final response = await ApiClient.get('/operations/strategy/gate-evaluations?projectId=$pId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is List ? data : (data['evaluations'] as List? ?? []);
        return list
            .map((item) => PrematureAlertModel.fromJson(item as Map<String, dynamic>))
            .toList();
      }
    } catch (e) {
      debugPrint('[StageGateService] getGuardrailAlerts error: $e');
    }
    return [];
  }

  /// Áp dụng nâng cấp giai đoạn chính thức
  Future<bool> applyStageTransition({
    required dynamic auditId,
    dynamic workspaceId,
    dynamic companyId,
    dynamic projectId,
    String? fromStage,
    String? toStage,
    String? rationale,
  }) async {
    try {
      final response = await ApiClient.post(
        '/operations/strategy/stage-transitions',
        body: {
          'workspaceId': workspaceId?.toString() ?? '1',
          'companyId': companyId?.toString() ?? '1',
          'projectId': projectId?.toString() ?? '1',
          'fromStage': fromStage ?? 'S0',
          'toStage': toStage ?? 'S1',
          'gateEvaluationId': auditId?.toString(),
          'rationale': rationale ?? 'Phê duyệt nâng cấp giai đoạn theo kết quả thẩm định Stage Gate.',
        },
      );
      return response.statusCode == 200 || response.statusCode == 201;
    } catch (e) {
      debugPrint('[StageGateService] applyStageTransition error: $e');
    }
    return false;
  }
}
