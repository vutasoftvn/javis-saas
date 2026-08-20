class AgentModel {
  final String id;
  final String name;
  final String role;
  final String department;
  final String status;
  final String model;
  final double temperature;
  final double successRate;
  final int totalRuns;
  final String? avatarUrl;
  final String? systemPrompt;
  final List<String> skills;
  final String? reportsTo;

  const AgentModel({
    required this.id,
    required this.name,
    required this.role,
    this.department = 'General',
    this.status = 'active',
    this.model = 'gpt-4o',
    this.temperature = 0.7,
    this.successRate = 1.0,
    this.totalRuns = 0,
    this.avatarUrl,
    this.systemPrompt,
    this.skills = const [],
    this.reportsTo,
  });

  factory AgentModel.fromJson(Map<String, dynamic> json) {
    return AgentModel(
      id: json['id']?.toString() ?? json['agent_id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Unnamed Agent',
      role: json['role']?.toString() ?? 'Specialist',
      department: json['department']?.toString() ?? 'General',
      status: json['status']?.toString() ?? 'active',
      model: json['model']?.toString() ?? json['model_name']?.toString() ?? 'gpt-4o',
      temperature: (json['temperature'] as num?)?.toDouble() ?? 0.7,
      successRate: (json['success_rate'] as num?)?.toDouble() ?? 1.0,
      totalRuns: (json['total_runs'] as num?)?.toInt() ?? 0,
      avatarUrl: json['avatar_url']?.toString(),
      systemPrompt: json['system_prompt']?.toString(),
      skills: (json['skills'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      reportsTo: json['reports_to']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'role': role,
      'department': department,
      'status': status,
      'model': model,
      'temperature': temperature,
      'success_rate': successRate,
      'total_runs': totalRuns,
      'avatar_url': avatarUrl,
      'system_prompt': systemPrompt,
      'skills': skills,
      'reports_to': reportsTo,
    };
  }
}

class AgentRunModel {
  final String id;
  final String agentId;
  final String? agentName;
  final String prompt;
  final String? output;
  final String status;
  final String? model;
  final double? latencyMs;
  final int? tokensUsed;
  final DateTime? createdAt;

  const AgentRunModel({
    required this.id,
    required this.agentId,
    this.agentName,
    required this.prompt,
    this.output,
    this.status = 'completed',
    this.model,
    this.latencyMs,
    this.tokensUsed,
    this.createdAt,
  });

  factory AgentRunModel.fromJson(Map<String, dynamic> json) {
    return AgentRunModel(
      id: json['id']?.toString() ?? '',
      agentId: json['agent_id']?.toString() ?? '',
      agentName: json['agent_name']?.toString(),
      prompt: json['prompt']?.toString() ?? json['input']?.toString() ?? '',
      output: json['output']?.toString() ?? json['result']?.toString(),
      status: json['status']?.toString() ?? 'completed',
      model: json['model']?.toString(),
      latencyMs: (json['latency_ms'] as num?)?.toDouble(),
      tokensUsed: (json['tokens_used'] as num?)?.toInt(),
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'agent_id': agentId,
      'agent_name': agentName,
      'prompt': prompt,
      'output': output,
      'status': status,
      'model': model,
      'latency_ms': latencyMs,
      'tokens_used': tokensUsed,
      'created_at': createdAt?.toIso8601String(),
    };
  }
}
