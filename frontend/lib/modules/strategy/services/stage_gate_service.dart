import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../data/models/stage_gate_model.dart';
import '../../../core/network/api_client.dart';

class StageGateService {
  /// Thực hiện phiên thẩm định chuyển giai đoạn (Stage Gate Audit)
  Future<StageGateAuditModel?> auditStageReadiness({
    required int projectId,
    String? targetStage,
  }) async {
    try {
      final response = await ApiClient.post(
        '/strategy/stage-gate/audit',
        body: {
          'project_id': projectId,
          'target_stage': targetStage,
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
  Future<List<StageGateAuditModel>> getAuditHistory(int projectId) async {
    try {
      final response = await ApiClient.get('/strategy/stage-gate/history/$projectId');
      if (response.statusCode == 200) {
        final list = jsonDecode(utf8.decode(response.bodyBytes)) as List;
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
  Future<List<PrematureAlertModel>> getGuardrailAlerts(int projectId) async {
    try {
      final response = await ApiClient.get('/strategy/stage-gate/guardrails/$projectId');
      if (response.statusCode == 200) {
        final list = jsonDecode(utf8.decode(response.bodyBytes)) as List;
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
    required int auditId,
    String? rationale,
  }) async {
    try {
      final response = await ApiClient.post(
        '/strategy/stage-gate/apply-transition/$auditId',
        body: {
          'rationale': rationale ?? 'Phê duyệt nâng cấp giai đoạn theo kết quả thẩm định Stage Gate.',
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        return data != null && data['status'] == 'success';
      }
    } catch (e) {
      debugPrint('[StageGateService] applyStageTransition error: $e');
    }
    return false;
  }
}
