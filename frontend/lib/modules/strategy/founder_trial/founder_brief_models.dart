/// Client model cho Founder Brief (spec §4 / Node E). R1 chỉ báo evidence
/// coverage — KHÔNG verdict, KHÔNG đề xuất quyết định. `nextReviewFocus` là
/// gợi ý trọng tâm review kế, luôn non-authoritative.
library;

/// AxisState wire: NOT_ASSESSED | NO_EVIDENCE | EVIDENCE_PRESENT |
/// CONFIGURATION_REQUIRED | UNAVAILABLE. Giữ nguyên chuỗi để không "đoán".
class EconomicsSubcomponent {
  const EconomicsSubcomponent({
    required this.state,
    required this.sourceTimestamp,
    required this.gap,
  });

  final String state;
  final String? sourceTimestamp;
  final String? gap;

  factory EconomicsSubcomponent.fromJson(Map<String, dynamic> json) =>
      EconomicsSubcomponent(
        state: json['state']?.toString() ?? 'UNAVAILABLE',
        sourceTimestamp: json['sourceTimestamp']?.toString(),
        gap: json['gap']?.toString(),
      );
}

class ReadinessAxis {
  const ReadinessAxis({
    required this.axis,
    required this.state,
    required this.evidenceRefs,
    required this.knownGaps,
    required this.lastObservedAt,
    this.projectBudget,
    this.workspaceLiquidity,
  });

  final String axis; // problem | solution | traction | economics | compliance
  final String state;
  final List<String> evidenceRefs;
  final List<String> knownGaps;
  final String? lastObservedAt;

  /// Chỉ có ở axis "economics" — hai thành phần ĐỘC LẬP.
  final EconomicsSubcomponent? projectBudget;
  final EconomicsSubcomponent? workspaceLiquidity;

  factory ReadinessAxis.fromJson(Map<String, dynamic> json) {
    List<String> strs(dynamic v) =>
        (v as List?)?.map((e) => e.toString()).toList() ?? const [];
    EconomicsSubcomponent? sub(dynamic v) => v is Map<String, dynamic>
        ? EconomicsSubcomponent.fromJson(v)
        : null;
    return ReadinessAxis(
      axis: json['axis']?.toString() ?? '',
      state: json['state']?.toString() ?? '',
      evidenceRefs: strs(json['evidenceRefs']),
      knownGaps: strs(json['knownGaps']),
      lastObservedAt: json['lastObservedAt']?.toString(),
      projectBudget: sub(json['projectBudget']),
      workspaceLiquidity: sub(json['workspaceLiquidity']),
    );
  }
}

/// Non-authoritative — chỉ nêu trục nào còn thiếu bằng chứng/cấu hình cho lần
/// review kế. KHÔNG map sang proceed/pivot/kill/hold.
class NextReviewFocus {
  const NextReviewFocus({
    required this.axis,
    required this.note,
    required this.isAuthoritative,
  });

  final String? axis;
  final String note;
  final bool isAuthoritative;

  factory NextReviewFocus.fromJson(Map<String, dynamic> json) => NextReviewFocus(
        axis: json['axis']?.toString(),
        note: json['note']?.toString() ?? '',
        // Defensive: client luôn coi đây là non-authoritative.
        isAuthoritative: false,
      );
}

class FounderBrief {
  const FounderBrief({
    required this.projectId,
    required this.axes,
    required this.nextReviewFocus,
    required this.generatedFrom,
  });

  final String projectId;
  final List<ReadinessAxis> axes;
  final NextReviewFocus nextReviewFocus;
  final String generatedFrom;

  ReadinessAxis? axisFor(String key) {
    for (final a in axes) {
      if (a.axis == key) return a;
    }
    return null;
  }

  factory FounderBrief.fromJson(Map<String, dynamic> json) {
    return FounderBrief(
      projectId: json['projectId']?.toString() ?? '',
      axes: (json['axes'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map(ReadinessAxis.fromJson)
              .toList() ??
          const [],
      nextReviewFocus: NextReviewFocus.fromJson(
          (json['nextReviewFocus'] as Map<String, dynamic>?) ?? const {}),
      generatedFrom: json['generatedFrom']?.toString() ?? '',
    );
  }
}
