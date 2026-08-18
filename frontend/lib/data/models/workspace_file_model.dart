class WorkspaceFileModel {
  final String relativePath;
  final String category;
  final bool isProtected;
  final int sizeBytes;

  WorkspaceFileModel({
    required this.relativePath,
    required this.category,
    required this.isProtected,
    required this.sizeBytes,
  });

  factory WorkspaceFileModel.fromJson(Map<String, dynamic> json) {
    return WorkspaceFileModel(
      relativePath: json['relative_path'] ?? '',
      category: json['category'] ?? 'root',
      isProtected: json['is_protected'] ?? false,
      sizeBytes: json['size_bytes'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'relative_path': relativePath,
      'category': category,
      'is_protected': isProtected,
      'size_bytes': sizeBytes,
    };
  }
}
