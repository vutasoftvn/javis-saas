class ChatAttachment {
  final String id;
  final String? messageId;
  final String objectRef;
  final String mediaType;
  final String fileName;
  final int size;
  final String? knowledgeIngestStatus;

  ChatAttachment({
    required this.id,
    this.messageId,
    required this.objectRef,
    required this.mediaType,
    required this.fileName,
    required this.size,
    this.knowledgeIngestStatus,
  });

  factory ChatAttachment.fromJson(Map<String, dynamic> json) {
    return ChatAttachment(
      id: json['id']?.toString() ?? '',
      messageId: json['message_id']?.toString(),
      objectRef: json['object_ref']?.toString() ?? '',
      mediaType: json['media_type']?.toString() ?? 'application/octet-stream',
      fileName: json['file_name']?.toString() ?? 'file',
      size: (json['size'] is num) ? (json['size'] as num).toInt() : 0,
      knowledgeIngestStatus: json['knowledge_ingest_status']?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'message_id': messageId,
        'object_ref': objectRef,
        'media_type': mediaType,
        'file_name': fileName,
        'size': size,
        'knowledge_ingest_status': knowledgeIngestStatus,
      };
}

class ChatMessage {
  final String id;
  final String conversationId;
  final String role; // user, assistant, system, tool
  String content;
  final String? runId;
  final String? parentMessageId;
  String status; // started, completed, failed
  final DateTime createdAt;
  final List<ChatAttachment> attachments;

  ChatMessage({
    required this.id,
    required this.conversationId,
    required this.role,
    required this.content,
    this.runId,
    this.parentMessageId,
    this.status = 'completed',
    required this.createdAt,
    this.attachments = const [],
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id']?.toString() ?? '',
      conversationId: json['conversation_id']?.toString() ?? '',
      role: json['role']?.toString() ?? 'user',
      content: json['content']?.toString() ?? '',
      runId: json['run_id']?.toString(),
      parentMessageId: json['parent_message_id']?.toString(),
      status: json['status']?.toString() ?? 'completed',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
      attachments: (json['attachments'] as List<dynamic>?)
              ?.map((a) => ChatAttachment.fromJson(a as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'conversation_id': conversationId,
        'role': role,
        'content': content,
        'run_id': runId,
        'parent_message_id': parentMessageId,
        'status': status,
        'created_at': createdAt.toIso8601String(),
        'attachments': attachments.map((a) => a.toJson()).toList(),
      };
}

class ChatConversation {
  final String id;
  final String companyId;
  final String workspaceId;
  final String createdByPrincipal;
  String title;
  String? activeAgentProfile;
  final DateTime createdAt;
  DateTime updatedAt;
  DateTime? archivedAt;
  List<ChatMessage> messages;

  ChatConversation({
    required this.id,
    required this.companyId,
    required this.workspaceId,
    required this.createdByPrincipal,
    required this.title,
    this.activeAgentProfile,
    required this.createdAt,
    required this.updatedAt,
    this.archivedAt,
    this.messages = const [],
  });

  bool get isArchived => archivedAt != null;

  factory ChatConversation.fromJson(Map<String, dynamic> json) {
    return ChatConversation(
      id: json['id']?.toString() ?? '',
      companyId: json['company_id']?.toString() ?? '',
      workspaceId: json['workspace_id']?.toString() ?? '',
      createdByPrincipal: json['created_by_principal']?.toString() ?? '',
      title: json['title']?.toString() ?? 'New Conversation',
      activeAgentProfile: json['active_agent_profile']?.toString(),
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
      archivedAt: json['archived_at'] != null
          ? DateTime.tryParse(json['archived_at'].toString())
          : null,
      messages: (json['messages'] as List<dynamic>?)
              ?.map((m) => ChatMessage.fromJson(m as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}

class ChatToolActivity {
  final String toolName;
  String status; // started, completed, failed
  final Map<String, dynamic>? arguments;
  dynamic result;
  String? error;

  ChatToolActivity({
    required this.toolName,
    this.status = 'started',
    this.arguments,
    this.result,
    this.error,
  });
}

class ChatApproval {
  final String id;
  final String? runId;
  final String action;
  final String subject;
  final String requester;
  String status; // PENDING, APPROVED, DENIED
  String? reason;
  DateTime? decidedAt;

  ChatApproval({
    required this.id,
    this.runId,
    required this.action,
    required this.subject,
    required this.requester,
    this.status = 'PENDING',
    this.reason,
    this.decidedAt,
  });

  factory ChatApproval.fromJson(Map<String, dynamic> json) {
    return ChatApproval(
      id: json['id']?.toString() ?? json['approval_id']?.toString() ?? '',
      runId: json['run_id']?.toString(),
      action: json['action']?.toString() ?? 'tool_call',
      subject: json['subject']?.toString() ?? '',
      requester: json['requester']?.toString() ?? 'agent',
      status: json['status']?.toString() ?? 'PENDING',
      reason: json['reason']?.toString(),
      decidedAt: json['decided_at'] != null
          ? DateTime.tryParse(json['decided_at'].toString())
          : null,
    );
  }
}
