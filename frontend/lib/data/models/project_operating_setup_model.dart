import '../../core/contracts/enums.generated.dart';

enum KickoffEvidenceLevel {
  none('NONE', 'Chưa nói chuyện với khách hàng'),
  oneToFourInterviews('ONE_TO_FOUR_INTERVIEWS', 'Đã có 1–4 cuộc trao đổi'),
  fivePlusInterviews('FIVE_PLUS_INTERVIEWS', 'Có từ 5 cuộc trao đổi'),
  prototypeOrRevenue(
    'PROTOTYPE_OR_REVENUE',
    'Đã có prototype hoặc khách trả tiền',
  );

  const KickoffEvidenceLevel(this.wire, this.label);
  final String wire;
  final String label;

  static KickoffEvidenceLevel? tryFromWire(String? v) {
    if (v == null) return null;
    for (final e in values) {
      if (e.wire == v) return e;
    }
    return null;
  }

  String toApi() => wire;
}

enum OperatingSetupStatus {
  notStarted('NOT_STARTED'),
  inProgress('IN_PROGRESS'),
  active('ACTIVE');

  const OperatingSetupStatus(this.wire);
  final String wire;

  static OperatingSetupStatus fromWire(String? v) {
    if (v == 'IN_PROGRESS') return OperatingSetupStatus.inProgress;
    if (v == 'ACTIVE') return OperatingSetupStatus.active;
    return OperatingSetupStatus.notStarted;
  }

  String toApi() => wire;
}

class FirstWeekActionDraft {
  const FirstWeekActionDraft({this.id, required this.title});
  final String? id;
  final String title;

  Map<String, dynamic> toJson() => {
    if (id != null) 'id': id,
    'title': title.trim(),
  };
}

class KickoffStagePolicy {
  static const p0DefaultWeeks = 2;
  static const p1DefaultWeeks = 4;

  static bool allows(ProjectLifecycleStage stage, int weeks) =>
      stage == ProjectLifecycleStage.p0Discovery
      ? weeks >= 1 && weeks <= 2
      : weeks >= 2 && weeks <= 4;

  static ProjectLifecycleStage recommend(KickoffEvidenceLevel? level) {
    if (level == KickoffEvidenceLevel.fivePlusInterviews ||
        level == KickoffEvidenceLevel.prototypeOrRevenue) {
      return ProjectLifecycleStage.p1ProblemValidation;
    }
    return ProjectLifecycleStage.p0Discovery;
  }
}

class ProjectOperatingSetupDraft {
  const ProjectOperatingSetupDraft({
    this.targetCustomer,
    this.problemStatement,
    this.evidenceLevel,
    this.selectedStage,
    this.stageDurationWeeks,
    this.weeklyReviewWeekday,
    this.weeklyReviewTime,
    this.firstWeekOutcome,
    this.firstWeekActions = const [],
  });

  final String? targetCustomer;
  final String? problemStatement;
  final KickoffEvidenceLevel? evidenceLevel;
  final ProjectLifecycleStage? selectedStage;
  final int? stageDurationWeeks;
  final int? weeklyReviewWeekday;
  final String? weeklyReviewTime;
  final String? firstWeekOutcome;
  final List<FirstWeekActionDraft> firstWeekActions;

  Map<String, dynamic> toJson() => {
    if (targetCustomer != null) 'targetCustomer': targetCustomer,
    if (problemStatement != null) 'problemStatement': problemStatement,
    if (evidenceLevel != null) 'evidenceLevel': evidenceLevel!.toApi(),
    if (selectedStage != null) 'selectedStage': selectedStage!.toApi(),
    if (stageDurationWeeks != null) 'stageDurationWeeks': stageDurationWeeks,
    if (weeklyReviewWeekday != null) 'weeklyReviewWeekday': weeklyReviewWeekday,
    if (weeklyReviewTime != null) 'weeklyReviewTime': weeklyReviewTime,
    if (firstWeekOutcome != null) 'firstWeekOutcome': firstWeekOutcome,
    'firstWeekActions': firstWeekActions.map((a) => a.toJson()).toList(),
  };
}

class ProjectOperatingSetup {
  const ProjectOperatingSetup({
    required this.projectId,
    required this.workspaceId,
    required this.status,
    this.targetCustomer,
    this.problemStatement,
    this.evidenceLevel,
    this.recommendedStage,
    this.selectedStage,
    this.stageDurationWeeks,
    this.stageTargetDate,
    this.weeklyReviewWeekday,
    this.weeklyReviewTime,
    this.firstWeekOutcome,
    this.firstWeekActions = const [],
    this.updatedAt,
  });

  final String projectId;
  final String workspaceId;
  final OperatingSetupStatus status;
  final String? targetCustomer;
  final String? problemStatement;
  final KickoffEvidenceLevel? evidenceLevel;
  final ProjectLifecycleStage? recommendedStage;
  final ProjectLifecycleStage? selectedStage;
  final int? stageDurationWeeks;
  final DateTime? stageTargetDate;
  final int? weeklyReviewWeekday;
  final String? weeklyReviewTime;
  final String? firstWeekOutcome;
  final List<FirstWeekActionDraft> firstWeekActions;
  final DateTime? updatedAt;

  bool get isInitialLoop =>
      status == OperatingSetupStatus.active &&
      (selectedStage == ProjectLifecycleStage.p0Discovery ||
          selectedStage == ProjectLifecycleStage.p1ProblemValidation);

  factory ProjectOperatingSetup.fromJson(Map<String, dynamic> json) {
    return ProjectOperatingSetup(
      projectId: json['projectId']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      status: OperatingSetupStatus.fromWire(json['status']?.toString()),
      targetCustomer: json['targetCustomer'] as String?,
      problemStatement: json['problemStatement'] as String?,
      evidenceLevel: KickoffEvidenceLevel.tryFromWire(
        json['evidenceLevel'] as String?,
      ),
      recommendedStage: ProjectLifecycleStage.tryFromWire(
        json['recommendedStage'] as String?,
      ),
      selectedStage: ProjectLifecycleStage.tryFromWire(
        json['selectedStage'] as String?,
      ),
      stageDurationWeeks: json['stageDurationWeeks'] is num
          ? (json['stageDurationWeeks'] as num).toInt()
          : null,
      stageTargetDate: json['stageTargetDate'] != null
          ? DateTime.tryParse(json['stageTargetDate'].toString())
          : null,
      weeklyReviewWeekday: json['weeklyReviewWeekday'] is num
          ? (json['weeklyReviewWeekday'] as num).toInt()
          : null,
      weeklyReviewTime: json['weeklyReviewTime'] as String?,
      firstWeekOutcome: json['firstWeekOutcome'] as String?,
      firstWeekActions:
          (json['firstWeekActions'] as List?)
              ?.map(
                (e) => FirstWeekActionDraft(
                  id: e['id']?.toString(),
                  title: (e['title'] ?? '').toString(),
                ),
              )
              .toList() ??
          const [],
      updatedAt: json['updatedAt'] != null
          ? DateTime.tryParse(json['updatedAt'].toString())
          : null,
    );
  }
}
