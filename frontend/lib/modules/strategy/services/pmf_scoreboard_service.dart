import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../data/models/pmf_scoreboard_model.dart';

class PmfScoreboardService {
  /// Lấy danh sách Metric Contracts
  Future<List<MetricContract>> listMetricContracts({
    required String projectId,
    String? workspaceId,
  }) async {
    try {
      final queryParams = <String>['projectId=$projectId'];
      if (workspaceId != null) queryParams.add('workspaceId=$workspaceId');
      final queryStr = '?${queryParams.join('&')}';

      final response = await ApiClient.get('/operations/strategy/metric-contracts$queryStr');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is List ? data : (data['items'] as List? ?? []);
        return list.map((item) => MetricContract.fromJson(item as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[PmfScoreboardService] listMetricContracts error: $e');
    }
    return [];
  }

  /// Lấy danh sách Metric Snapshots
  Future<List<MetricSnapshot>> listMetricSnapshots({
    String? contractVersionId,
    String? projectId,
    String? workspaceId,
  }) async {
    try {
      final queryParams = <String>[];
      if (contractVersionId != null) queryParams.add('contractVersionId=$contractVersionId');
      if (projectId != null) queryParams.add('projectId=$projectId');
      if (workspaceId != null) queryParams.add('workspaceId=$workspaceId');
      final queryStr = queryParams.isNotEmpty ? '?${queryParams.join('&')}' : '';

      final response = await ApiClient.get('/operations/strategy/metric-snapshots$queryStr');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is List ? data : (data['items'] as List? ?? []);
        return list.map((item) => MetricSnapshot.fromJson(item as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[PmfScoreboardService] listMetricSnapshots error: $e');
    }
    return [];
  }

  /// Tính toán PMF Scoreboard
  Future<PmfScoreboardRun?> calculateScoreboard({
    required String projectId,
    required List<String> contractVersionIds,
    required List<String> inputSnapshotIds,
    required List<String> reviewedEvidenceIds,
    String? policyVersion,
  }) async {
    try {
      final body = <String, dynamic>{
        'projectId': projectId,
        'contractVersionIds': contractVersionIds,
        'inputSnapshotIds': inputSnapshotIds,
        'reviewedEvidenceIds': reviewedEvidenceIds,
        'policyVersion': policyVersion ?? 'v1',
      };

      final response = await ApiClient.post(
        '/operations/strategy/pmf-scoreboards/calculate',
        body: body,
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return PmfScoreboardRun.fromJson(data);
      }
    } catch (e) {
      debugPrint('[PmfScoreboardService] calculateScoreboard error: $e');
    }
    return null;
  }

  /// Lấy chi tiết một PMF Scoreboard Run
  Future<PmfScoreboardRun?> getPmfScoreboardRun(String runId) async {
    try {
      final response = await ApiClient.get('/operations/strategy/pmf-scoreboards/$runId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return PmfScoreboardRun.fromJson(data);
      }
    } catch (e) {
      debugPrint('[PmfScoreboardService] getPmfScoreboardRun error: $e');
    }
    return null;
  }

  /// Lấy danh sách PMF Scoreboard Runs của dự án
  Future<List<PmfScoreboardRun>> listPmfScoreboardRuns({
    required String projectId,
    String? workspaceId,
  }) async {
    try {
      final queryParams = <String>['projectId=$projectId'];
      if (workspaceId != null) queryParams.add('workspaceId=$workspaceId');
      final queryStr = '?${queryParams.join('&')}';

      final response = await ApiClient.get('/operations/strategy/pmf-scoreboards$queryStr');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is List ? data : (data['items'] as List? ?? []);
        return list.map((item) => PmfScoreboardRun.fromJson(item as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[PmfScoreboardService] listPmfScoreboardRuns error: $e');
    }
    return [];
  }

  /// Đánh giá mức độ trưởng thành (Maturity Assessment)
  Future<MaturityAssessment?> assessMaturity({
    required String projectId,
    String? scoreboardRunId,
  }) async {
    try {
      final body = <String, dynamic>{
        'projectId': projectId,
        'scoreboardRunId': ?scoreboardRunId,
      };

      final response = await ApiClient.post(
        '/operations/strategy/maturity-assessments',
        body: body,
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return MaturityAssessment.fromJson(data);
      }
    } catch (e) {
      debugPrint('[PmfScoreboardService] assessMaturity error: $e');
    }
    return null;
  }

  /// Lấy danh sách đánh giá trưởng thành
  Future<List<MaturityAssessment>> listMaturityAssessments({
    required String projectId,
  }) async {
    try {
      final response = await ApiClient.get('/operations/strategy/maturity-assessments?projectId=$projectId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is List ? data : (data['items'] as List? ?? []);
        return list.map((item) => MaturityAssessment.fromJson(item as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[PmfScoreboardService] listMaturityAssessments error: $e');
    }
    return [];
  }
}
