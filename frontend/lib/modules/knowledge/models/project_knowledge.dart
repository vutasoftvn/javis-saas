class ProjectKnowledgeCitation {
  final String documentId;
  final String versionId;
  final String chunkId;
  final String title;
  final String excerpt;

  const ProjectKnowledgeCitation({
    required this.documentId,
    required this.versionId,
    required this.chunkId,
    required this.title,
    required this.excerpt,
  });

  factory ProjectKnowledgeCitation.fromJson(Map<String, dynamic> json) {
    return ProjectKnowledgeCitation(
      documentId: json['documentId']?.toString() ?? '',
      versionId: json['versionId']?.toString() ?? '',
      chunkId: json['chunkId']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      excerpt: json['excerpt']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'documentId': documentId,
    'versionId': versionId,
    'chunkId': chunkId,
    'title': title,
    'excerpt': excerpt,
  };
}

class ProjectKnowledgeItem {
  final String text;
  final List<ProjectKnowledgeCitation> citations;

  const ProjectKnowledgeItem({
    required this.text,
    required this.citations,
  });

  factory ProjectKnowledgeItem.fromJson(Map<String, dynamic> json) {
    final list = json['citations'] as List? ?? [];
    return ProjectKnowledgeItem(
      text: json['text']?.toString() ?? '',
      citations: list
          .whereType<Map<String, dynamic>>()
          .map((e) => ProjectKnowledgeCitation.fromJson(e))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'text': text,
    'citations': citations.map((e) => e.toJson()).toList(),
  };
}

class ProjectKnowledgeSearchResult {
  final List<ProjectKnowledgeItem> items;
  final List<ProjectKnowledgeCitation> citations;

  const ProjectKnowledgeSearchResult({
    required this.items,
    required this.citations,
  });

  factory ProjectKnowledgeSearchResult.fromJson(Map<String, dynamic> json) {
    final itemsList = json['items'] as List? ?? [];
    final citationsList = json['citations'] as List? ?? [];
    return ProjectKnowledgeSearchResult(
      items: itemsList
          .whereType<Map<String, dynamic>>()
          .map((e) => ProjectKnowledgeItem.fromJson(e))
          .toList(),
      citations: citationsList
          .whereType<Map<String, dynamic>>()
          .map((e) => ProjectKnowledgeCitation.fromJson(e))
          .toList(),
    );
  }
}
