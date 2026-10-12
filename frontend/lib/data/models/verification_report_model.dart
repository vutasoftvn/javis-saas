enum VerificationVerdict { pass, fail, inconclusive }

/// Một tiêu chí trong báo cáo Verifier. Chỉ chứa mã (id, verdict, reason code) —
/// UI không được hiển thị diễn giải tự do.
class VerificationCriterion {
  final String id;
  final bool required;
  final String check;
  final String verdict; // pass | fail | unclear
  final String reason;

  const VerificationCriterion({
    required this.id,
    required this.required,
    required this.check,
    required this.verdict,
    required this.reason,
  });

  factory VerificationCriterion.fromJson(Map<String, dynamic> j) => VerificationCriterion(
        id: (j['id'] ?? '').toString(),
        required: j['required'] != false,
        check: (j['check'] ?? '').toString(),
        verdict: (j['verdict'] ?? 'unclear').toString(),
        reason: (j['reason'] ?? '').toString(),
      );
}

/// Khóa JSON theo `_verification_report_view` (camelCase) của
/// `GET /agent/workforce/verification-reports`.
class VerificationReportModel {
  final String reportId;
  final String taskId;
  final String runId;
  final VerificationVerdict verdict;
  final String mode;
  final List<VerificationCriterion> criteria;
  final DateTime? createdAt;

  const VerificationReportModel({
    required this.reportId,
    required this.taskId,
    required this.runId,
    required this.verdict,
    required this.mode,
    required this.criteria,
    this.createdAt,
  });

  factory VerificationReportModel.fromJson(Map<String, dynamic> j) {
    final raw = (j['verdict'] ?? '').toString().toLowerCase();
    final results = j['criteriaResults'];
    return VerificationReportModel(
      reportId: (j['reportId'] ?? '').toString(),
      taskId: (j['taskId'] ?? '').toString(),
      runId: (j['runId'] ?? '').toString(),
      verdict: raw == 'pass'
          ? VerificationVerdict.pass
          : raw == 'fail'
              ? VerificationVerdict.fail
              : VerificationVerdict.inconclusive,
      mode: (j['mode'] ?? '').toString(),
      criteria: results is List
          ? results
              .whereType<Map<String, dynamic>>()
              .map(VerificationCriterion.fromJson)
              .toList()
          : const [],
      createdAt: DateTime.tryParse((j['createdAt'] ?? '').toString()),
    );
  }
}
