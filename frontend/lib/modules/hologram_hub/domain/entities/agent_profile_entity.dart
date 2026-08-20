class AgentProfileEntity {
  final String id;
  final String name;
  final String role;
  final String description;
  final String modelPolicy;
  final List<String> skills;
  final List<String> tools;

  const AgentProfileEntity({
    required this.id,
    required this.name,
    required this.role,
    required this.description,
    this.modelPolicy = "reasoning",
    this.skills = const [],
    this.tools = const [],
  });
}
