class ProjectionCache {
  // Placeholder cho local database (như Isar, Hive, hoặc SQLite)
  
  void saveProjection(String runId, Map<String, dynamic> projectionData, String cursor) {
    // Chỉ lưu state, không lưu event raw
  }
  
  Map<String, dynamic>? getProjection(String runId) {
    return null;
  }
  
  bool isCursorGap(String localCursor, String serverCursor) {
    // Logic kiểm tra gap
    return false;
  }
}
