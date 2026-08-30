// Academy models — isolated from strategy, evidence, gate, and lifecycle state.
//
// INVARIANTS:
// - No lifecycleStage, projectId, evidenceId, gateEvaluationId, or pilotId
// - Every simulation result carries synthetic = true and a disclaimer
// - Template exports have kind = 'academy_template_draft' and are not evidence

class AcademyProgram {
  final String id;
  final String slug;
  final String title;
  final String description;
  final String version;
  final int moduleCount;
  final int lessonCount;
  final bool published;

  const AcademyProgram({
    required this.id,
    required this.slug,
    required this.title,
    required this.description,
    required this.version,
    required this.moduleCount,
    required this.lessonCount,
    required this.published,
  });

  factory AcademyProgram.fromJson(Map<String, dynamic> json) => AcademyProgram(
        id: json['id'].toString(),
        slug: json['slug'] as String,
        title: json['title'] as String,
        description: (json['description'] as String?) ?? '',
        version: (json['version'] as String?) ?? '1.0.0',
        moduleCount: (json['moduleCount'] as int?) ?? 0,
        lessonCount: (json['lessonCount'] as int?) ?? 0,
        published: (json['published'] as bool?) ?? false,
      );
}

class AcademyLesson {
  final String id;
  final String moduleId;
  final String title;
  final int order;
  final String practiceType;

  const AcademyLesson({
    required this.id,
    required this.moduleId,
    required this.title,
    required this.order,
    required this.practiceType,
  });

  factory AcademyLesson.fromJson(Map<String, dynamic> json) => AcademyLesson(
        id: json['id'].toString(),
        moduleId: json['moduleId'].toString(),
        title: json['title'] as String,
        order: (json['order'] as int?) ?? 0,
        practiceType: (json['practiceType'] as String?) ?? 'reading',
      );
}

enum AcademyEnrollmentStatus { notStarted, inProgress, completed }

class AcademyEnrollment {
  final String id;
  final String workspaceId;
  final String programId;
  final int completedLessons;
  final AcademyEnrollmentStatus status;

  // INVARIANT: no lifecycleStage, projectId, or evidenceId
  const AcademyEnrollment({
    required this.id,
    required this.workspaceId,
    required this.programId,
    required this.completedLessons,
    required this.status,
  });

  factory AcademyEnrollment.fromJson(Map<String, dynamic> json) {
    final statusStr = (json['status'] as String?) ?? 'NOT_STARTED';
    final status = switch (statusStr) {
      'IN_PROGRESS' => AcademyEnrollmentStatus.inProgress,
      'COMPLETED' => AcademyEnrollmentStatus.completed,
      _ => AcademyEnrollmentStatus.notStarted,
    };
    return AcademyEnrollment(
      id: json['id'].toString(),
      workspaceId: json['workspaceId'].toString(),
      programId: json['programId'].toString(),
      completedLessons: (json['completedLessons'] as int?) ?? 0,
      status: status,
    );
  }
}

/// A simulation result — always synthetic, always carries disclaimer.
class AcademySimulationResult {
  final String attemptId;
  final String artifactRef;
  final bool synthetic;
  final String disclaimer;
  final String scenarioVersion;

  const AcademySimulationResult({
    required this.attemptId,
    required this.artifactRef,
    required this.synthetic,
    required this.disclaimer,
    required this.scenarioVersion,
  });

  factory AcademySimulationResult.fromJson(Map<String, dynamic> json) =>
      AcademySimulationResult(
        attemptId: json['attemptId'].toString(),
        artifactRef: json['artifactRef'] as String,
        synthetic: (json['synthetic'] as bool?) ?? true,
        disclaimer: (json['disclaimer'] as String?) ??
            'Đây là kết quả mô phỏng học tập, không phải evidence thực.',
        scenarioVersion: (json['scenarioVersion'] as String?) ?? '1.0.0',
      );

  /// INVARIANT: artifactRef always starts with 'academy-artifact://'
  bool get isValidAcademyArtifact => artifactRef.startsWith('academy-artifact://');
}

/// Template export result — always kind='academy_template_draft', never Evidence.
class AcademyTemplateExportResult {
  final String id;
  final String kind;
  final String academySourceRef;
  final String disclaimer;
  final Map<String, dynamic> body;

  const AcademyTemplateExportResult({
    required this.id,
    required this.kind,
    required this.academySourceRef,
    required this.disclaimer,
    required this.body,
  });

  /// INVARIANT: kind is always 'academy_template_draft'
  bool get isTemplateDraft => kind == 'academy_template_draft';

  factory AcademyTemplateExportResult.fromJson(Map<String, dynamic> json) =>
      AcademyTemplateExportResult(
        id: json['id'].toString(),
        kind: (json['kind'] as String?) ?? 'academy_template_draft',
        academySourceRef: json['academySourceRef'] as String,
        disclaimer: json['disclaimer'] as String,
        body: (json['body'] as Map<String, dynamic>?) ?? {},
      );
}
