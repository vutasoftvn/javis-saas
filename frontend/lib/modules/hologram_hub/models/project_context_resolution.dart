enum ProjectContextResolutionKind {
  stored,
  defaulted,
  missing,
  stale,
}

class ProjectContextResolution {
  const ProjectContextResolution({
    required this.kind,
    this.project,
  });

  final ProjectContextResolutionKind kind;
  final dynamic project;

  String? get projectId {
    if (project == null) return null;
    if (project is Map) {
      return project['id']?.toString();
    }
    try {
      return (project as dynamic).id?.toString();
    } catch (_) {
      return null;
    }
  }
}
