// GENERATED — KHÔNG SỬA TAY.
// Nguồn: shared/contracts/enums.json · Sinh bởi: scripts/gen-contracts.mjs
// Đổi enum ⇒ sửa JSON nguồn rồi chạy `node scripts/gen-contracts.mjs` và commit.
// ignore_for_file: constant_identifier_names, lines_longer_than_80_chars

/// Vòng đời trưởng thành của Workspace — độc lập với Project và Legal Entity. Cấm alias: company_stage, ventureStage, S0_GENESIS..S5_SCALE.
enum WorkspaceLifecycleStage {
  w0Idea('W0_IDEA'),
  w1ProblemValidation('W1_PROBLEM_VALIDATION'),
  w2SolutionValidation('W2_SOLUTION_VALIDATION'),
  w3MvpBuild('W3_MVP_BUILD'),
  w4ProductMarketFit('W4_PRODUCT_MARKET_FIT'),
  w5Scale('W5_SCALE');

  const WorkspaceLifecycleStage(this.wire);
  final String wire;

  static WorkspaceLifecycleStage fromWire(String v) => values.firstWhere(
        (e) => e.wire == v,
        orElse: () => throw ArgumentError('Unknown WorkspaceLifecycleStage wire value: $v'),
      );

  static WorkspaceLifecycleStage? tryFromWire(String? v) {
    if (v == null) return null;
    for (final e in values) {
      if (e.wire == v) return e;
    }
    return null;
  }

  String toApi() => wire;
}

/// Vòng đời của một Project bên trong Workspace — độc lập với Workspace stage. Prefix P bắt buộc.
enum ProjectLifecycleStage {
  p0Discovery('P0_DISCOVERY'),
  p1ProblemValidation('P1_PROBLEM_VALIDATION'),
  p2SolutionValidation('P2_SOLUTION_VALIDATION'),
  p3BuildValidate('P3_BUILD_VALIDATE'),
  p4GoToMarket('P4_GO_TO_MARKET'),
  p5OperateGrowth('P5_OPERATE_GROWTH'),
  p6ScaleGovern('P6_SCALE_GOVERN');

  const ProjectLifecycleStage(this.wire);
  final String wire;

  static ProjectLifecycleStage fromWire(String v) => values.firstWhere(
        (e) => e.wire == v,
        orElse: () => throw ArgumentError('Unknown ProjectLifecycleStage wire value: $v'),
      );

  static ProjectLifecycleStage? tryFromWire(String? v) {
    if (v == null) return null;
    for (final e in values) {
      if (e.wire == v) return e;
    }
    return null;
  }

  String toApi() => wire;
}

/// Trạng thái vận hành của Workspace.
enum WorkspaceStatus {
  active('ACTIVE'),
  archived('ARCHIVED'),
  suspended('SUSPENDED');

  const WorkspaceStatus(this.wire);
  final String wire;

  static WorkspaceStatus fromWire(String v) => values.firstWhere(
        (e) => e.wire == v,
        orElse: () => throw ArgumentError('Unknown WorkspaceStatus wire value: $v'),
      );

  static WorkspaceStatus? tryFromWire(String? v) {
    if (v == null) return null;
    for (final e in values) {
      if (e.wire == v) return e;
    }
    return null;
  }

  String toApi() => wire;
}

/// Trạng thái vận hành của Project.
enum ProjectStatus {
  active('ACTIVE'),
  paused('PAUSED'),
  completed('COMPLETED'),
  archived('ARCHIVED');

  const ProjectStatus(this.wire);
  final String wire;

  static ProjectStatus fromWire(String v) => values.firstWhere(
        (e) => e.wire == v,
        orElse: () => throw ArgumentError('Unknown ProjectStatus wire value: $v'),
      );

  static ProjectStatus? tryFromWire(String? v) {
    if (v == null) return null;
    for (final e in values) {
      if (e.wire == v) return e;
    }
    return null;
  }

  String toApi() => wire;
}

/// Chế độ vận hành Runtime Fabric của Workspace. Không gộp thành một cờ online=true.
enum RuntimeMode {
  localOnly('LOCAL_ONLY'),
  remoteAccess('REMOTE_ACCESS'),
  cloudContinuity('CLOUD_CONTINUITY');

  const RuntimeMode(this.wire);
  final String wire;

  static RuntimeMode fromWire(String v) => values.firstWhere(
        (e) => e.wire == v,
        orElse: () => throw ArgumentError('Unknown RuntimeMode wire value: $v'),
      );

  static RuntimeMode? tryFromWire(String? v) {
    if (v == null) return null;
    for (final e in values) {
      if (e.wire == v) return e;
    }
    return null;
  }

  String toApi() => wire;
}

/// Phạm vi dữ liệu được sync ra ngoài host. Credentials không bao giờ sync raw.
enum SyncPolicy {
  controlMetadataOnly('CONTROL_METADATA_ONLY'),
  selectiveEncrypted('SELECTIVE_ENCRYPTED'),
  fullEncrypted('FULL_ENCRYPTED');

  const SyncPolicy(this.wire);
  final String wire;

  static SyncPolicy fromWire(String v) => values.firstWhere(
        (e) => e.wire == v,
        orElse: () => throw ArgumentError('Unknown SyncPolicy wire value: $v'),
      );

  static SyncPolicy? tryFromWire(String? v) {
    if (v == null) return null;
    for (final e in values) {
      if (e.wire == v) return e;
    }
    return null;
  }

  String toApi() => wire;
}

/// Trạng thái đồng bộ hiện tại của Workspace.
enum SyncStatus {
  localOnly('LOCAL_ONLY'),
  pending('PENDING'),
  inSync('IN_SYNC'),
  conflict('CONFLICT'),
  error('ERROR');

  const SyncStatus(this.wire);
  final String wire;

  static SyncStatus fromWire(String v) => values.firstWhere(
        (e) => e.wire == v,
        orElse: () => throw ArgumentError('Unknown SyncStatus wire value: $v'),
      );

  static SyncStatus? tryFromWire(String? v) {
    if (v == null) return null;
    for (final e in values) {
      if (e.wire == v) return e;
    }
    return null;
  }

  String toApi() => wire;
}

/// Vòng đời pháp nhân — KHÔNG map thành Workspace stage. Bỏ REGISTRATION_READINESS.
enum LegalEntityStatus {
  draft('DRAFT'),
  registrationPreparation('REGISTRATION_PREPARATION'),
  registeredUnverified('REGISTERED_UNVERIFIED'),
  verified('VERIFIED'),
  suspended('SUSPENDED'),
  dissolved('DISSOLVED');

  const LegalEntityStatus(this.wire);
  final String wire;

  static LegalEntityStatus fromWire(String v) => values.firstWhere(
        (e) => e.wire == v,
        orElse: () => throw ArgumentError('Unknown LegalEntityStatus wire value: $v'),
      );

  static LegalEntityStatus? tryFromWire(String? v) {
    if (v == null) return null;
    for (final e in values) {
      if (e.wire == v) return e;
    }
    return null;
  }

  String toApi() => wire;
}

const Map<String, String> legacyWorkspaceStageToCanonical = {
  'S0_GENESIS': 'W0_IDEA',
  'S1_PROBLEM_VALIDATION': 'W1_PROBLEM_VALIDATION',
  'S2_SOLUTION_VALIDATION': 'W2_SOLUTION_VALIDATION',
  'S3_MVP_BUILD': 'W3_MVP_BUILD',
  'S4_PRODUCT_MARKET_FIT': 'W4_PRODUCT_MARKET_FIT',
  'S5_SCALE': 'W5_SCALE',
};

const Map<String, String> legacyProjectStageToCanonical = {
  'S0_EXPLORE': 'P0_DISCOVERY',
  'S1_PROBLEM_VALIDATION': 'P1_PROBLEM_VALIDATION',
  'S2_SOLUTION_VALIDATION': 'P2_SOLUTION_VALIDATION',
  'S3_BUSINESS_VALIDATION': 'P3_BUILD_VALIDATE',
  'S4_GO_TO_MARKET': 'P4_GO_TO_MARKET',
  'S5_OPERATE_GROWTH': 'P5_OPERATE_GROWTH',
  'S6_SCALE_GOVERN': 'P6_SCALE_GOVERN',
};
