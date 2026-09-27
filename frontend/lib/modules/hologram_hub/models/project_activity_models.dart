import 'dart:convert';
import 'package:get/get.dart';
import '../../../../core/localization/locale_controller.dart';
import '../../../../core/localization/supported_locale.dart';

/// Mô hình durable project activity event từ API projection
class ProjectActivityEvent {
  final String eventId;
  final String workspaceId;
  final String projectId;
  final int projectSequence;
  final String kind; // run.queued, run.completed, tool.requested, etc.
  final String? phase; // pending, in_progress, completed, failed
  final String? status;
  final String? actorId;
  final String? actorKind; // ai, human, system, principal
  final String? correlationId;
  final String? sourceType; // run, message, tool, approval, task, decision
  final String? sourceId;
  final String? sourceVersion;
  final String? summary; // redacted, safe for UI
  final Map<String, dynamic> summaryData;
  final String? classification; // internal, restricted, public
  final String? integrityHash;
  final DateTime? occurredAt;
  final DateTime? recordedAt;

  ProjectActivityEvent({
    required this.eventId,
    required this.workspaceId,
    required this.projectId,
    required this.projectSequence,
    required this.kind,
    this.phase,
    this.status,
    this.actorId,
    this.actorKind,
    this.correlationId,
    this.sourceType,
    this.sourceId,
    this.sourceVersion,
    this.summary,
    Map<String, dynamic>? summaryData,
    this.classification,
    this.integrityHash,
    this.occurredAt,
    this.recordedAt,
  }) : summaryData = summaryData ?? {};

  /// Group events by kind category (chat, run, tool, approval, decision, task, risk)
  String get category {
    if (kind.startsWith('chat.')) return 'Chat';
    if (kind.startsWith('run.')) return 'Run';
    if (kind.startsWith('tool.')) return 'Tool';
    if (kind.startsWith('approval.')) return 'Approval';
    if (kind.startsWith('decision.')) return 'Decision';
    if (kind.startsWith('task.')) return 'Task';
    if (kind.startsWith('risk.')) return 'Risk';
    return 'System';
  }

  String get icon {
    switch (category) {
      case 'Chat':
        return 'chat';
      case 'Run':
        return 'play_circle';
      case 'Tool':
        return 'settings';
      case 'Approval':
        return 'check_circle';
      case 'Decision':
        return 'lightbulb';
      case 'Task':
        return 'assignment';
      case 'Risk':
        return 'warning';
      default:
        return 'info';
    }
  }

  /// Trích xuất Run ID nếu có từ summaryData hoặc sourceId
  String? get runId {
    if (summaryData.containsKey('run_id') && summaryData['run_id'] != null) {
      return summaryData['run_id']?.toString();
    }
    if (sourceType == 'run' && sourceId != null && sourceId!.isNotEmpty) {
      return sourceId;
    }
    return null;
  }

  /// Short Run ID gọn gàng để hiển thị (ví dụ: #d2773537)
  String? get shortRunId {
    final rid = runId;
    if (rid == null || rid.isEmpty) return null;
    if (rid.startsWith('run_')) {
      final hex = rid.substring(4);
      return hex.length > 8 ? '#${hex.substring(0, 8)}' : '#$hex';
    }
    return rid.length > 10 ? '#${rid.substring(0, 8)}' : '#$rid';
  }

  /// Profile / Role của Agent tham gia nếu có
  String? get agentProfile {
    if (summaryData.containsKey('agent_profile') && summaryData['agent_profile'] != null) {
      return summaryData['agent_profile']?.toString();
    }
    if (summaryData.containsKey('role') && summaryData['role'] != null) {
      return summaryData['role']?.toString();
    }
    if ((actorKind?.toLowerCase() == 'agent' || actorKind?.toLowerCase() == 'ai') &&
        actorId != null &&
        actorId!.isNotEmpty) {
      return actorId;
    }
    return null;
  }

  /// Tên bước thực thi nếu có
  String? get stepName {
    if (summaryData.containsKey('step_name') && summaryData['step_name'] != null) {
      return summaryData['step_name']?.toString();
    }
    return null;
  }

  /// Format tên Agent rõ ràng, không trộn lẫn ngôn ngữ (Việt hoàn toàn hoặc Anh hoàn toàn)
  static String formatAgentProfile(String? profile, {bool isEn = false}) {
    if (profile == null || profile.isEmpty) return '';
    final p = profile.toLowerCase().trim();
    switch (p) {
      case 'operations':
      case 'agent_ops':
        return isEn ? 'Operations' : 'Vận hành';
      case 'marketing':
      case 'growth_marketer':
        return isEn ? 'Marketing' : 'Tiếp thị & Tăng trưởng';
      case 'engineering':
      case 'tech_lead':
        return isEn ? 'Engineering' : 'Kỹ thuật';
      case 'finance':
      case 'financial_analyst':
        return isEn ? 'Finance' : 'Tài chính';
      case 'legal':
        return isEn ? 'Legal' : 'Pháp lý';
      case 'sales':
        return isEn ? 'Sales' : 'Kinh doanh';
      case 'chief_of_staff':
        return isEn ? 'Chief of Staff' : 'Chánh văn phòng';
      default:
        return profile
            .split(RegExp(r'[_ -]'))
            .where((w) => w.isNotEmpty)
            .map((w) => '${w[0].toUpperCase()}${w.substring(1)}')
            .join(' ');
    }
  }

  /// Format loại sự kiện rõ ràng, thuần ngôn ngữ theo locale
  String formatKind({bool isEn = false}) {
    final k = kind.toLowerCase().trim();
    switch (k) {
      case 'run.queued':
        return isEn ? 'Run queued' : 'Đưa vào hàng đợi thực thi';
      case 'run.started':
        return isEn ? 'Run started' : 'Bắt đầu thực thi';
      case 'run.completed':
        return isEn ? 'Run completed' : 'Thực thi hoàn thành';
      case 'run.failed':
        return isEn ? 'Run failed' : 'Thực thi thất bại';
      case 'run.cancelled':
        return isEn ? 'Run cancelled' : 'Đã hủy thực thi';
      case 'run.waiting_approval':
        return isEn ? 'Waiting for approval' : 'Chờ phê duyệt thực thi';
      case 'run.checkpointed':
        return isEn ? 'Checkpoint saved' : 'Lưu điểm kiểm tra';
      case 'chat.accepted':
        return isEn ? 'Chat message accepted' : 'Tiếp nhận hội thoại';
      case 'agent.chat_message':
        return isEn ? 'Agent message' : 'Tin nhắn từ Trợ lý';
      case 'tool.requested':
        return isEn ? 'Tool call requested' : 'Yêu cầu gọi công cụ';
      case 'tool.policy_allowed':
        return isEn ? 'Tool allowed' : 'Công cụ được chấp thuận';
      case 'tool.policy_denied':
        return isEn ? 'Tool denied by policy' : 'Công cụ bị từ chối';
      case 'approval.requested':
        return isEn ? 'Approval requested' : 'Yêu cầu phê duyệt';
      case 'approval.resolved':
        return isEn ? 'Approval resolved' : 'Đã xử lý phê duyệt';
      case 'task.created':
        return isEn ? 'Task created' : 'Tạo nhiệm vụ mới';
      case 'task.completed':
        return isEn ? 'Task completed' : 'Nhiệm vụ hoàn thành';
      case 'work_package.created':
        return isEn ? 'Work package created' : 'Tạo gói công việc';
      case 'decision.recorded':
        return isEn ? 'Decision recorded' : 'Ghi nhận quyết định';
      case 'evidence.linked':
        return isEn ? 'Evidence linked' : 'Liên kết chứng cứ';
      case 'risk.raised':
        return isEn ? 'Risk identified' : 'Phát hiện rủi ro';
      case 'risk.resolved':
        return isEn ? 'Risk resolved' : 'Rủi ro đã giải quyết';
      case 'system.delivery':
        return isEn ? 'System notification' : 'Thông báo hệ thống';
      default:
        if (k.startsWith('run.')) {
          return isEn ? 'Run execution' : 'Tiến trình thực thi';
        }
        return kind;
    }
  }

  /// Format tác nhân kích hoạt / thực hiện sự kiện
  String formatActor({bool isEn = false}) {
    final kindLower = (actorKind ?? '').toLowerCase().trim();
    final id = actorId?.trim() ?? '';

    if (kindLower.isEmpty && id.isEmpty) {
      final ap = agentProfile;
      if (ap != null && ap.isNotEmpty) {
        final name = formatAgentProfile(ap, isEn: isEn);
        return isEn ? 'AI Assistant: $name' : 'Trợ lý: $name';
      }
      return isEn ? 'Automated System' : 'Hệ thống tự động';
    }

    if (kindLower == 'principal' || kindLower == 'human' || kindLower == 'user') {
      final userLabel = isEn ? 'User' : 'Người dùng';
      if (id.isNotEmpty) {
        final cleanId = id.replaceFirst(RegExp(r'^user:?', caseSensitive: false), '');
        final shortId = cleanId.length > 8 ? cleanId.substring(cleanId.length - 6) : cleanId;
        return '$userLabel ($shortId)';
      }
      return userLabel;
    }

    if (kindLower == 'agent' || kindLower == 'ai') {
      final agentLabel = isEn ? 'AI Assistant' : 'Trợ lý';
      final formattedId = formatAgentProfile(id, isEn: isEn);
      return formattedId.isNotEmpty ? '$agentLabel: $formattedId' : agentLabel;
    }

    if (kindLower == 'system') {
      return isEn ? 'Automated System' : 'Hệ thống tự động';
    }

    if (kindLower.isNotEmpty && id.isNotEmpty) {
      return '$kindLower: $id';
    }
    return id.isNotEmpty ? id : (isEn ? 'System' : 'Hệ thống');
  }

  /// Format trạng thái để hiển thị badge rõ ràng
  String? formatStatus({bool isEn = false}) {
    final s = (status ?? phase ?? '').toLowerCase();
    if (s.isEmpty) {
      if (kind == 'run.queued') return isEn ? 'Queued' : 'Hàng đợi';
      if (kind == 'run.started') return isEn ? 'Running' : 'Đang chạy';
      if (kind == 'run.completed') return isEn ? 'Completed' : 'Hoàn thành';
      if (kind == 'run.failed') return isEn ? 'Failed' : 'Thất bại';
      if (kind == 'run.cancelled') return isEn ? 'Cancelled' : 'Đã hủy';
      if (kind == 'run.waiting_approval') return isEn ? 'Needs Approval' : 'Chờ duyệt';
      return null;
    }
    switch (s) {
      case 'completed':
      case 'success':
      case 'resolved':
      case 'execution_complete':
        return isEn ? 'Completed' : 'Hoàn thành';
      case 'in_progress':
      case 'running':
      case 'started':
        return isEn ? 'Running' : 'Đang chạy';
      case 'pending':
      case 'queued':
      case 'waiting':
        return isEn ? 'Queued' : 'Hàng đợi';
      case 'waiting_approval':
        return isEn ? 'Needs Approval' : 'Chờ duyệt';
      case 'failed':
      case 'error':
      case 'denied':
        return isEn ? 'Failed' : 'Thất bại';
      case 'cancelled':
        return isEn ? 'Cancelled' : 'Đã hủy';
      default:
        return s;
    }
  }

  /// Tiêu đề hiển thị thân thiện, giải mã từ raw map/json nếu có
  String getFormattedTitle({bool isEn = false}) {
    if (summary != null &&
        summary!.isNotEmpty &&
        !summary!.trim().startsWith('{') &&
        summary != '(no summary)') {
      return summary!;
    }

    if (summaryData.containsKey('title') && summaryData['title'] != null) {
      final t = summaryData['title'].toString().trim();
      if (t.isNotEmpty) return t;
    }

    final agent = agentProfile;
    final agentName = formatAgentProfile(agent, isEn: isEn);
    final kName = formatKind(isEn: isEn);

    if (agentName.isNotEmpty) {
      return '$agentName: $kName';
    }

    if (stepName != null && stepName!.isNotEmpty) {
      return isEn ? 'Step: $stepName' : 'Bước: $stepName';
    }

    return kName;
  }

  /// Safe to show in UI without exposing raw tokens or prompts
  String get displaySummary {
    if (summary != null &&
        summary!.isNotEmpty &&
        !summary!.trim().startsWith('{') &&
        summary != '(no summary)') {
      return summary!;
    }
    bool isEn = false;
    try {
      if (Get.isRegistered<LocaleController>()) {
        isEn = Get.find<LocaleController>().current.value == SupportedLocale.enUS;
      } else if (Get.locale != null) {
        isEn = Get.locale?.languageCode != 'vi';
      }
    } catch (_) {}
    return getFormattedTitle(isEn: isEn);
  }

  factory ProjectActivityEvent.fromJson(Map<String, dynamic> json) {
    Map<String, dynamic> parsedSummaryData = {};
    String? rawSummaryString;

    final rawSummary = json['summary'];
    if (rawSummary is Map) {
      parsedSummaryData = Map<String, dynamic>.from(rawSummary);
    } else if (rawSummary is String) {
      rawSummaryString = rawSummary;
      final trimmed = rawSummary.trim();
      if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
          (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
        try {
          final decoded = jsonDecode(trimmed);
          if (decoded is Map) {
            parsedSummaryData = Map<String, dynamic>.from(decoded);
          }
        } catch (_) {}
      }
    }

    return ProjectActivityEvent(
      eventId: json['event_id']?.toString() ?? '',
      workspaceId: json['workspace_id']?.toString() ?? '',
      projectId: json['project_id']?.toString() ?? '',
      projectSequence: (json['project_sequence'] is num)
          ? (json['project_sequence'] as num).toInt()
          : 0,
      kind: json['kind']?.toString() ?? 'unknown',
      phase: json['phase']?.toString(),
      status: json['status']?.toString(),
      actorId: json['actor_id']?.toString(),
      actorKind: json['actor_kind']?.toString(),
      correlationId: json['correlation_id']?.toString(),
      sourceType: json['source_type']?.toString(),
      sourceId: json['source_id']?.toString(),
      sourceVersion: json['source_version']?.toString(),
      summary: rawSummaryString ?? (parsedSummaryData.isEmpty ? (rawSummary?.toString()) : null),
      summaryData: parsedSummaryData,
      classification: json['classification']?.toString(),
      integrityHash: json['integrity_hash']?.toString(),
      occurredAt: json['occurred_at'] != null
          ? DateTime.tryParse(json['occurred_at'].toString())
          : null,
      recordedAt: json['recorded_at'] != null
          ? DateTime.tryParse(json['recorded_at'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'event_id': eventId,
        'workspace_id': workspaceId,
        'project_id': projectId,
        'project_sequence': projectSequence,
        'kind': kind,
        if (phase != null) 'phase': phase,
        if (status != null) 'status': status,
        if (actorId != null) 'actor_id': actorId,
        if (actorKind != null) 'actor_kind': actorKind,
        if (correlationId != null) 'correlation_id': correlationId,
        if (sourceType != null) 'source_type': sourceType,
        if (sourceId != null) 'source_id': sourceId,
        if (sourceVersion != null) 'source_version': sourceVersion,
        if (summary != null) 'summary': summary,
        if (summaryData.isNotEmpty) 'summary_data': summaryData,
        if (classification != null) 'classification': classification,
        if (integrityHash != null) 'integrity_hash': integrityHash,
        if (occurredAt != null) 'occurred_at': occurredAt?.toIso8601String(),
        if (recordedAt != null) 'recorded_at': recordedAt?.toIso8601String(),
      };
}

/// Response từ activity list endpoint
class ProjectActivityListResponse {
  final List<ProjectActivityEvent> items;
  final int total;

  ProjectActivityListResponse({
    required this.items,
    required this.total,
  });

  factory ProjectActivityListResponse.fromJson(Map<String, dynamic> json) {
    return ProjectActivityListResponse(
      items: (json['items'] as List<dynamic>?)
              ?.map((item) =>
                  ProjectActivityEvent.fromJson(item as Map<String, dynamic>))
              .toList() ??
          [],
      total: (json['total'] is num) ? (json['total'] as num).toInt() : 0,
    );
  }
}
