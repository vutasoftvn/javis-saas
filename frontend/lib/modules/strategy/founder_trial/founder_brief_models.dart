/// Client model cho Founder Brief (spec §4 / Node E). Deterministic, R1 KHÔNG
/// có agent recommendation — `suggestedDecision` luôn non-authoritative.
library;

class ReadinessAxis {
  const ReadinessAxis({
    required this.axis,
    required this.state,
    required this.evidenceRefs,
    required this.knownGaps,
    required this.lastObservedAt,
  });

  final String axis; // problem | solution | traction | economics | compliance
  final String state;
  final List<String> evidenceRefs;
  final List<String> knownGaps;
  final String? lastObservedAt;

  factory ReadinessAxis.fromJson(Map<String, dynamic> json) {
    List<String> strs(dynamic v) =>
        (v as List?)?.map((e) => e.toString()).toList() ?? const [];
    return ReadinessAxis(
      axis: json['axis']?.toString() ?? '',
      state: json['state']?.toString() ?? '',
      evidenceRefs: strs(json['evidenceRefs']),
      knownGaps: strs(json['knownGaps']),
      lastObservedAt: json['lastObservedAt']?.toString(),
    );
  }
}

class SuggestedDecision {
  const SuggestedDecision({
    required this.label,
    required this.rationale,
    required this.isAuthoritative,
  });

  final String label; // proceed | pivot | kill | hold
  final String rationale;
  final bool isAuthoritative;

  factory SuggestedDecision.fromJson(Map<String, dynamic> json) => SuggestedDecision(
        label: json['label']?.toString() ?? 'hold',
        rationale: json['rationale']?.toString() ?? '',
        // Defensive: dù server có trả gì, client coi đây là gợi ý non-authoritative.
        isAuthoritative: false,
      );
}

class FounderBrief {
  const FounderBrief({
    required this.projectId,
    required this.axes,
    required this.suggestedDecision,
    required this.generatedFrom,
  });

  final String projectId;
  final List<ReadinessAxis> axes;
  final SuggestedDecision suggestedDecision;
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
      suggestedDecision: SuggestedDecision.fromJson(
          (json['suggestedDecision'] as Map<String, dynamic>?) ?? const {}),
      generatedFrom: json['generatedFrom']?.toString() ?? '',
    );
  }
}
