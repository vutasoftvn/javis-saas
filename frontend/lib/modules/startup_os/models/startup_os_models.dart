// Model cho Startup OS (plan 2026-09-18 Phase 4): cây Goal, độ tươi ngữ cảnh 7
// chiều, Goal cần rà soát và dự án khám phá chờ triage. Parse chặt: payload sai
// shape ném FormatException để MvpRequestClient báo malformedResponse, không
// âm thầm thành danh sách rỗng.

String _requireString(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is String && value.isNotEmpty) return value;
  if (value is num) return value.toString();
  throw FormatException('Missing "$key" in Startup OS payload');
}

String? _optString(Object? value) {
  if (value == null) return null;
  if (value is String) return value.isEmpty ? null : value;
  return value.toString();
}

int _int(Object? value) => value is num ? value.toInt() : 0;

List<Map<String, dynamic>> _mapList(Object? value, String key) {
  if (value is! List) throw FormatException('"$key" must be a list');
  return value.map((item) {
    if (item is Map<String, dynamic>) return item;
    throw FormatException('"$key" items must be objects');
  }).toList(growable: false);
}

enum GoalType { vision, strategic, tactical, sprint }

GoalType goalTypeFromWire(String raw) => GoalType.values.firstWhere(
      (t) => t.name == raw,
      orElse: () => throw FormatException('Unknown goalType "$raw"'),
    );

String goalTypeLabel(GoalType type) => switch (type) {
      GoalType.vision => 'Tầm nhìn (3–5 năm)',
      GoalType.strategic => 'Chiến lược (12 tháng)',
      GoalType.tactical => 'Chiến thuật (4–12 tuần)',
      GoalType.sprint => 'Sprint (1–4 tuần)',
    };

class GoalNode {
  const GoalNode({
    required this.id,
    required this.parentId,
    required this.title,
    required this.description,
    required this.goalType,
    required this.status,
    required this.startDate,
    required this.endDate,
    required this.depth,
    required this.objectiveCount,
    required this.krTotal,
    required this.krAchieved,
    required this.children,
  });

  factory GoalNode.fromJson(Map<String, dynamic> json) => GoalNode(
        id: _requireString(json, 'id'),
        parentId: _optString(json['parentId']),
        title: _requireString(json, 'title'),
        description: _optString(json['description']),
        goalType: goalTypeFromWire(_requireString(json, 'goalType')),
        status: _requireString(json, 'status'),
        startDate: _optString(json['startDate']),
        endDate: _optString(json['endDate']),
        depth: _int(json['depth']),
        objectiveCount: _int(json['objectiveCount']),
        krTotal: _int(json['krTotal']),
        krAchieved: _int(json['krAchieved']),
        children: _mapList(json['children'] ?? const <Object>[], 'children')
            .map(GoalNode.fromJson)
            .toList(growable: false),
      );

  final String id;
  final String? parentId;
  final String title;
  final String? description;
  final GoalType goalType;
  final String status;
  final String? startDate;
  final String? endDate;
  final int depth;
  final int objectiveCount;
  final int krTotal;
  final int krAchieved;
  final List<GoalNode> children;

  bool get isActive => status == 'active';

  /// Tổng KR đạt / tổng KR của cả nhánh (Goal này + mọi Goal con).
  ({int achieved, int total}) get rollup {
    var achieved = krAchieved;
    var total = krTotal;
    for (final child in children) {
      final r = child.rollup;
      achieved += r.achieved;
      total += r.total;
    }
    return (achieved: achieved, total: total);
  }

  /// null khi nhánh chưa có KR nào — không hiển thị 0% giả.
  double? get rollupProgress {
    final r = rollup;
    return r.total == 0 ? null : r.achieved / r.total;
  }
}

List<GoalNode> goalTreeFromJson(Object? raw) {
  if (raw is! Map<String, dynamic>) throw const FormatException('Invalid goal tree payload');
  return _mapList(raw['tree'], 'tree').map(GoalNode.fromJson).toList(growable: false);
}

/// Mức độ tươi của 1 chiều, theo urgency Company trả về.
enum Freshness { fresh, dueSoon, due, overdue, missing }

class DimensionCadence {
  const DimensionCadence({
    required this.dimension,
    required this.cadence,
    required this.intervalDays,
    required this.lastReviewedAt,
    required this.daysSinceLastReview,
    required this.neverReviewed,
    required this.urgency,
  });

  factory DimensionCadence.fromJson(Map<String, dynamic> json) => DimensionCadence(
        dimension: _requireString(json, 'dimension'),
        cadence: _requireString(json, 'cadence'),
        intervalDays: _int(json['intervalDays']),
        lastReviewedAt: _optString(json['lastReviewedAt']),
        daysSinceLastReview:
            json['daysSinceLastReview'] is num ? (json['daysSinceLastReview'] as num).toInt() : null,
        neverReviewed: json['neverReviewed'] == true,
        urgency: _requireString(json, 'urgency'),
      );

  final String dimension;
  final String cadence;
  final int intervalDays;
  final String? lastReviewedAt;
  final int? daysSinceLastReview;
  final bool neverReviewed;
  final String urgency;

  bool get isFast => cadence == 'fast';

  Freshness get freshness {
    if (neverReviewed) return Freshness.missing;
    return switch (urgency) {
      'critical' => Freshness.overdue,
      'recommended' => Freshness.due,
      'optional' => Freshness.dueSoon,
      _ => Freshness.fresh,
    };
  }

  /// Chiều cần cập nhật trước khi đặt Goal (đến hạn, quá hạn hoặc chưa có).
  bool get needsUpdate =>
      freshness == Freshness.missing || freshness == Freshness.overdue || freshness == Freshness.due;
}

List<DimensionCadence> cadencesFromJson(Object? raw) {
  if (raw is! Map<String, dynamic>) throw const FormatException('Invalid cadence payload');
  return _mapList(raw['cadences'], 'cadences').map(DimensionCadence.fromJson).toList(growable: false);
}

class GoalNeedingReview {
  const GoalNeedingReview({
    required this.goalId,
    required this.goalTitle,
    required this.goalType,
    required this.snapshotAgeDays,
    required this.urgency,
  });

  factory GoalNeedingReview.fromJson(Map<String, dynamic> json) => GoalNeedingReview(
        goalId: _requireString(json, 'goalId'),
        goalTitle: _requireString(json, 'goalTitle'),
        goalType: _requireString(json, 'goalType'),
        snapshotAgeDays: _int(json['snapshotAgeDays']),
        urgency: _requireString(json, 'urgency'),
      );

  final String goalId;
  final String goalTitle;
  final String goalType;
  final int snapshotAgeDays;
  final String urgency;
}

List<GoalNeedingReview> goalsNeedingReviewFromJson(Object? raw) {
  if (raw is! Map<String, dynamic>) throw const FormatException('Invalid needing-review payload');
  return _mapList(raw['goals'], 'goals').map(GoalNeedingReview.fromJson).toList(growable: false);
}

class PendingProject {
  const PendingProject({
    required this.id,
    required this.title,
    required this.description,
    required this.origin,
  });

  factory PendingProject.fromJson(Map<String, dynamic> json) => PendingProject(
        id: _requireString(json, 'id'),
        title: _requireString(json, 'title'),
        description: _optString(json['description']),
        origin: _optString(json['origin']),
      );

  final String id;
  final String title;
  final String? description;
  final String? origin;
}

List<PendingProject> pendingProjectsFromJson(Object? raw) {
  if (raw is! Map<String, dynamic>) throw const FormatException('Invalid pending projects payload');
  return _mapList(raw['projects'], 'projects').map(PendingProject.fromJson).toList(growable: false);
}

class CadenceWarning {
  const CadenceWarning({required this.dimension, required this.urgency, required this.message});

  factory CadenceWarning.fromJson(Map<String, dynamic> json) => CadenceWarning(
        dimension: _requireString(json, 'dimension'),
        urgency: _requireString(json, 'urgency'),
        message: _requireString(json, 'message'),
      );

  final String dimension;
  final String urgency;
  final String message;
}

class CreatedGoal {
  const CreatedGoal({required this.goalId, required this.cadenceWarnings});

  factory CreatedGoal.fromJson(Object? raw) {
    if (raw is! Map<String, dynamic>) throw const FormatException('Invalid create goal payload');
    return CreatedGoal(
      goalId: _requireString(raw, 'goalId'),
      cadenceWarnings: _mapList(raw['cadenceWarnings'] ?? const <Object>[], 'cadenceWarnings')
          .map(CadenceWarning.fromJson)
          .toList(growable: false),
    );
  }

  final String goalId;
  final List<CadenceWarning> cadenceWarnings;
}

enum TriageAction { markRd, archive, rollToNewGoal }

extension TriageActionWire on TriageAction {
  String get wire => switch (this) {
        TriageAction.markRd => 'mark_rd',
        TriageAction.archive => 'archive',
        TriageAction.rollToNewGoal => 'roll_to_new_goal',
      };

  String get label => switch (this) {
        TriageAction.markRd => 'Giữ làm R&D (không gắn mục tiêu)',
        TriageAction.archive => 'Lưu trữ',
        TriageAction.rollToNewGoal => 'Nâng thành Objective của một Goal',
      };
}
