import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../data/models/pilot_run_model.dart';

class PilotRunService {
  /// Lấy danh sách Pilot Runs trong workspace / theo project
  Future<List<PilotRun>> listPilots({dynamic projectId, dynamic workspaceId}) async {
    try {
      final queryParams = <String>[];
      if (projectId != null) queryParams.add('projectId=${projectId.toString()}');
      if (workspaceId != null) queryParams.add('workspaceId=${workspaceId.toString()}');
      final queryStr = queryParams.isNotEmpty ? '?${queryParams.join('&')}' : '';

      final response = await ApiClient.get('/operations/strategy/pilots$queryStr');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is List ? data : (data['items'] as List? ?? []);
        return list.map((item) => PilotRun.fromJson(item as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[PilotRunService] listPilots error: $e');
    }
    return [];
  }

  /// Lấy chi tiết một Pilot Run
  Future<PilotRun?> getPilot(String id, {dynamic workspaceId}) async {
    try {
      final queryStr = workspaceId != null ? '?workspaceId=${workspaceId.toString()}' : '';
      final response = await ApiClient.get('/operations/strategy/pilots/$id$queryStr');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return PilotRun.fromJson(data);
      }
    } catch (e) {
      debugPrint('[PilotRunService] getPilot error: $e');
    }
    return null;
  }

  /// Tạo bản nháp Pilot Run (Draft)
  Future<PilotRun?> createDraft({
    required String projectId,
    String? experimentId,
    required List<String> designPartnerEvidenceRefs,
    required String metricContractArtifactRef,
    required String instrumentationArtifactRef,
    required String onboardingArtifactRef,
    String? supportEscalationArtifactRef,
    required String rollbackArtifactRef,
    required String releaseOwnerMemberId,
  }) async {
    try {
      final body = <String, dynamic>{
        'projectId': projectId,
        'experimentId': ?experimentId,
        'designPartnerEvidenceRefs': designPartnerEvidenceRefs,
        'metricContractArtifactRef': metricContractArtifactRef,
        'instrumentationArtifactRef': instrumentationArtifactRef,
        'onboardingArtifactRef': onboardingArtifactRef,
        'supportEscalationArtifactRef': ?supportEscalationArtifactRef,
        'rollbackArtifactRef': rollbackArtifactRef,
        'releaseOwnerMemberId': releaseOwnerMemberId,
      };

      final response = await ApiClient.post(
        '/operations/strategy/pilots',
        body: body,
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return PilotRun.fromJson(data);
      }
    } catch (e) {
      debugPrint('[PilotRunService] createDraft error: $e');
    }
    return null;
  }

  /// Phê duyệt Pilot Run (Founder/Admin approval)
  Future<PilotRun?> approve({
    required String pilotId,
    required String approvalRef,
  }) async {
    try {
      final response = await ApiClient.post(
        '/operations/strategy/pilots/$pilotId/approve',
        body: {'approvalRef': approvalRef},
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return PilotRun.fromJson(data);
      }
    } catch (e) {
      debugPrint('[PilotRunService] approve error: $e');
    }
    return null;
  }

  /// Kích hoạt Pilot Run (Human-only activation, không thay đổi lifecycle stage)
  Future<PilotRun?> activate({
    required String pilotId,
    required String approvalRef,
  }) async {
    try {
      final response = await ApiClient.post(
        '/operations/strategy/pilots/$pilotId/activate',
        body: {'approvalRef': approvalRef},
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return PilotRun.fromJson(data);
      }
    } catch (e) {
      debugPrint('[PilotRunService] activate error: $e');
    }
    return null;
  }

  /// Đóng hoặc hủy Pilot Run
  Future<PilotRun?> close({
    required String pilotId,
    required String status,
    String? cancellationReason,
  }) async {
    try {
      final body = <String, dynamic>{'status': status};
      if (cancellationReason != null && cancellationReason.isNotEmpty) {
        body['cancellationReason'] = cancellationReason;
      }
      final response = await ApiClient.post(
        '/operations/strategy/pilots/$pilotId/close',
        body: body,
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return PilotRun.fromJson(data);
      }
    } catch (e) {
      debugPrint('[PilotRunService] close error: $e');
    }
    return null;
  }
}
