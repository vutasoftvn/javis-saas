import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import 'founder_trial_board_models.dart';

/// Lệnh mutation nghiêm ngặt của luồng Founder Trial. Mỗi lệnh đi qua đúng một
/// capability R1 và trả `ApiResult` thật — caller chỉ coi là thành công khi
/// nhận `ApiSuccess`, không suy diễn từ absence-of-exception (guardrail 7).
class FounderTrialCommands {
  FounderTrialCommands({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  final MvpRequestClient _client;

  /// Resize Operating Cycle đang chạy. `expectedRevision` LẤY TỪ Board; nếu
  /// server trả 412 (revision conflict) caller phải reload Board rồi hỏi lại.
  Future<ApiResult<FounderTrialCycle>> resizeCycle({
    required String projectId,
    required String cycleId,
    required int durationWeeks,
    required int expectedRevision,
    String? reason,
  }) {
    return _client.request<FounderTrialCycle>(
      MvpEndpoint.strategyOperatingCycleResize,
      pathParams: {'projectId': projectId},
      body: {
        'cycleId': cycleId,
        'durationWeeks': durationWeeks,
        'expectedRevision': expectedRevision,
        if (reason != null && reason.isNotEmpty) 'reason': reason,
      },
      decode: (json) => FounderTrialCycle.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<FounderTrialAssumption>> createAssumption({
    required String projectId,
    required String statement,
    required int importance,
    required int uncertainty,
  }) {
    return _client.request<FounderTrialAssumption>(
      MvpEndpoint.strategyAssumptionCreate,
      body: {
        'projectId': projectId,
        'statement': statement,
        'importance': importance,
        'uncertainty': uncertainty,
      },
      decode: (json) =>
          FounderTrialAssumption.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Experiment nghiêm ngặt: bắt buộc assumption + method + successCriteria.
  Future<ApiResult<FounderTrialExperiment>> createExperiment({
    required String projectId,
    required String assumptionId,
    required String hypothesis,
    required String method,
    required String successCriteria,
  }) {
    return _client.request<FounderTrialExperiment>(
      MvpEndpoint.strategyFounderTrialExperimentCreate,
      pathParams: {'projectId': projectId},
      body: {
        'assumptionId': assumptionId,
        'hypothesis': hypothesis,
        'method': method,
        'successCriteria': successCriteria,
      },
      decode: (json) =>
          FounderTrialExperiment.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Nộp một interview thành evidence candidate (KHÔNG auto-approve).
  Future<ApiResult<Map<String, dynamic>>> submitInterviewEvidence({
    required String interviewId,
    required String claim,
    String? supportsOrRefutes,
  }) {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.commercialInterviewSubmitEvidence,
      pathParams: {'id': interviewId},
      body: {
        'claim': claim,
        'supportsOrRefutes': ?supportsOrRefutes,
      },
      decode: (json) => (json as Map<String, dynamic>?) ?? const {},
    );
  }

  /// Duyệt/từ chối evidence — chỉ founder/role được phép; candidate không bao
  /// giờ tự thành approved.
  Future<ApiResult<Map<String, dynamic>>> reviewEvidence({
    required String evidenceId,
    required bool approve,
    String? note,
  }) {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.strategyEvidenceReview,
      pathParams: {'id': evidenceId},
      body: {
        'action': approve ? 'approve' : 'reject',
        if (note != null && note.isNotEmpty) 'note': note,
      },
      decode: (json) => (json as Map<String, dynamic>?) ?? const {},
    );
  }

  /// Ghi Founder Decision tường minh (proceed | pivot | kill | hold). Đây là
  /// nguồn DUY NHẤT của quyết định — Founder Brief không tự ghi.
  Future<ApiResult<FounderTrialDecision>> createDecision({
    required String projectId,
    required String decision,
    String? rationale,
  }) {
    return _client.request<FounderTrialDecision>(
      MvpEndpoint.strategyDecisionCreate,
      body: {
        'projectId': projectId,
        'decision': decision,
        if (rationale != null && rationale.isNotEmpty) 'rationale': rationale,
      },
      decode: (json) =>
          FounderTrialDecision.fromJson(json as Map<String, dynamic>),
    );
  }
}
