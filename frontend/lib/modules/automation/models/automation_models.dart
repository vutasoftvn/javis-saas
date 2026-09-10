// COSA Automation MVP — Flutter models (Task 7 / 8).
// Parsed straight from the standard mvpItem / mvpList envelope. No status is
// ever inferred from free text.

enum AutomationCardStatus { ready, setupRequired, suspended, unavailable, forbidden }

AutomationCardStatus automationCardStatusFrom(String lifecycle, bool configured) {
  switch (lifecycle) {
    case 'PUBLISHED':
      return AutomationCardStatus.ready;
    case 'SUSPENDED':
      return AutomationCardStatus.suspended;
    case 'RETIRED':
      return AutomationCardStatus.unavailable;
    case 'DRAFT':
    default:
      return configured ? AutomationCardStatus.setupRequired : AutomationCardStatus.setupRequired;
  }
}

class AutomationConfigField {
  const AutomationConfigField({
    required this.key,
    required this.label,
    required this.type,
    required this.required,
    this.enumValues = const [],
    this.help,
  });

  final String key;
  final String label;
  final String type;
  final bool required;
  final List<String> enumValues;
  final String? help;

  factory AutomationConfigField.fromJson(Map<String, dynamic> j) => AutomationConfigField(
        key: j['key'] as String,
        label: j['label'] as String? ?? j['key'] as String,
        type: j['type'] as String? ?? 'string',
        required: j['required'] as bool? ?? false,
        enumValues:
            (j['enumValues'] as List<dynamic>? ?? const []).map((e) => e.toString()).toList(),
        help: j['help'] as String?,
      );
}

class AutomationRevisionView {
  const AutomationRevisionView({
    required this.id,
    required this.revisionNo,
    required this.revisionHash,
    required this.published,
    required this.configuration,
  });

  final String id;
  final int revisionNo;
  final String revisionHash;
  final bool published;
  final Map<String, dynamic> configuration;

  factory AutomationRevisionView.fromJson(Map<String, dynamic> j) => AutomationRevisionView(
        id: j['id'].toString(),
        revisionNo: (j['revisionNo'] as num).toInt(),
        revisionHash: j['revisionHash'] as String? ?? '',
        published: j['published'] as bool? ?? false,
        configuration: (j['configuration'] as Map<String, dynamic>?) ?? const {},
      );
}

class AutomationDefinitionView {
  const AutomationDefinitionView({
    required this.id,
    required this.automationKey,
    required this.title,
    required this.purpose,
    required this.domain,
    required this.lifecycleState,
    required this.configured,
    required this.configFields,
    required this.currentRevision,
    required this.draftRevision,
  });

  final String? id;
  final String automationKey;
  final String title;
  final String purpose;
  final String domain;
  final String lifecycleState;
  final bool configured;
  final List<AutomationConfigField> configFields;
  final AutomationRevisionView? currentRevision;
  final AutomationRevisionView? draftRevision;

  AutomationCardStatus get cardStatus => automationCardStatusFrom(lifecycleState, configured);

  factory AutomationDefinitionView.fromJson(Map<String, dynamic> j) => AutomationDefinitionView(
        id: j['id']?.toString(),
        automationKey: j['automationKey'] as String,
        title: j['title'] as String? ?? j['automationKey'] as String,
        purpose: j['purpose'] as String? ?? '',
        domain: j['domain'] as String? ?? '',
        lifecycleState: j['lifecycleState'] as String? ?? 'DRAFT',
        configured: j['configured'] as bool? ?? false,
        configFields: (j['configFields'] as List<dynamic>? ?? const [])
            .map((e) => AutomationConfigField.fromJson(e as Map<String, dynamic>))
            .toList(),
        currentRevision: j['currentRevision'] == null
            ? null
            : AutomationRevisionView.fromJson(j['currentRevision'] as Map<String, dynamic>),
        draftRevision: j['draftRevision'] == null
            ? null
            : AutomationRevisionView.fromJson(j['draftRevision'] as Map<String, dynamic>),
      );
}

class AutomationInvocationView {
  const AutomationInvocationView({
    required this.id,
    required this.automationKey,
    required this.state,
    required this.version,
    required this.agentRunId,
    required this.createdAt,
  });

  final String id;
  final String automationKey;
  final String state;
  final int version;
  final String? agentRunId;
  final String createdAt;

  bool get isTerminal => const {'COMPLETED', 'FAILED', 'CANCELLED'}.contains(state);
  bool get isCancellable =>
      const {'REQUESTED', 'QUEUED', 'LEASED', 'RUNNING', 'WAITING_APPROVAL', 'BLOCKED'}
          .contains(state);

  factory AutomationInvocationView.fromJson(Map<String, dynamic> j) => AutomationInvocationView(
        id: j['id'].toString(),
        automationKey: j['automationKey'] as String? ?? '',
        state: j['state'] as String? ?? 'REQUESTED',
        version: (j['version'] as num?)?.toInt() ?? 1,
        agentRunId: j['agentRunId'] as String?,
        createdAt: j['createdAt'] as String? ?? '',
      );
}

class AutomationRunStep {
  const AutomationRunStep({
    required this.name,
    required this.state,
    required this.retryCount,
    this.policyDecision,
    this.failureReason,
    this.evidenceRef,
  });

  final String name;
  final String state;
  final int retryCount;
  final String? policyDecision;
  final String? failureReason;
  final String? evidenceRef;

  factory AutomationRunStep.fromJson(Map<String, dynamic> j) => AutomationRunStep(
        name: j['name'] as String? ?? '',
        state: j['state'] as String? ?? 'UNKNOWN',
        retryCount: (j['retryCount'] as num?)?.toInt() ?? 0,
        policyDecision: j['policyDecision'] as String?,
        failureReason: j['failureReason'] as String?,
        evidenceRef: j['evidenceRef'] as String?,
      );
}

class AutomationRunInspector {
  const AutomationRunInspector({
    required this.invocationId,
    required this.automationKey,
    required this.revisionNo,
    required this.revisionHash,
    required this.state,
    required this.steps,
    required this.evidenceRefs,
    required this.sourceHealth,
    this.failureReason,
  });

  final String invocationId;
  final String automationKey;
  final int revisionNo;
  final String revisionHash;
  final String state;
  final List<AutomationRunStep> steps;
  final List<String> evidenceRefs;
  final String sourceHealth;
  final String? failureReason;

  factory AutomationRunInspector.fromJson(Map<String, dynamic> j) => AutomationRunInspector(
        invocationId: j['invocationId'].toString(),
        automationKey: j['automationKey'] as String? ?? '',
        revisionNo: (j['revisionNo'] as num?)?.toInt() ?? 0,
        revisionHash: j['revisionHash'] as String? ?? '',
        state: j['state'] as String? ?? 'REQUESTED',
        steps: (j['steps'] as List<dynamic>? ?? const [])
            .map((e) => AutomationRunStep.fromJson(e as Map<String, dynamic>))
            .toList(),
        evidenceRefs:
            (j['evidenceRefs'] as List<dynamic>? ?? const []).map((e) => e.toString()).toList(),
        sourceHealth: j['sourceHealth'] as String? ?? 'unknown',
        failureReason: j['failureReason'] as String?,
      );
}

enum NeedsYouKind { approvalRequired, needsInput, blocked, localRuntimeUnavailable, failed }

NeedsYouKind needsYouKindFrom(String raw) => switch (raw) {
      'APPROVAL_REQUIRED' => NeedsYouKind.approvalRequired,
      'NEEDS_INPUT' => NeedsYouKind.needsInput,
      'BLOCKED' => NeedsYouKind.blocked,
      'LOCAL_RUNTIME_UNAVAILABLE' => NeedsYouKind.localRuntimeUnavailable,
      _ => NeedsYouKind.failed,
    };

class NeedsYouItem {
  const NeedsYouItem({
    required this.invocationId,
    required this.automationKey,
    required this.kind,
    required this.observedAt,
  });

  final String invocationId;
  final String automationKey;
  final NeedsYouKind kind;
  final String observedAt;

  factory NeedsYouItem.fromJson(Map<String, dynamic> j) => NeedsYouItem(
        invocationId: j['invocationId'].toString(),
        automationKey: j['automationKey'] as String? ?? '',
        kind: needsYouKindFrom(j['kind'] as String? ?? 'FAILED'),
        observedAt: j['observedAt'] as String? ?? '',
      );
}
