class DiagnosticCheckItem {
  final String category;
  final String name;
  final String status; // 'healthy', 'unhealthy', 'warning', 'optional'
  final String message;

  DiagnosticCheckItem({
    required this.category,
    required this.name,
    required this.status,
    required this.message,
  });

  factory DiagnosticCheckItem.fromJson(Map<String, dynamic> json) {
    return DiagnosticCheckItem(
      category: json['category'] ?? 'general',
      name: json['name'] ?? '',
      status: json['status'] ?? 'healthy',
      message: json['message'] ?? '',
    );
  }
}

class DoctorReportModel {
  final String status;
  final List<DiagnosticCheckItem> checks;

  DoctorReportModel({
    required this.status,
    required this.checks,
  });

  factory DoctorReportModel.fromJson(Map<String, dynamic> json) {
    var rawChecks = json['checks'] as List? ?? [];
    return DoctorReportModel(
      status: json['status'] ?? 'healthy',
      checks: rawChecks.map((e) => DiagnosticCheckItem.fromJson(e)).toList(),
    );
  }
}
