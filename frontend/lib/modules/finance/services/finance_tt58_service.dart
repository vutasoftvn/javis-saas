class FinanceTT58Service {
  @Deprecated('Chế độ TT58/2024 không còn hiệu lực hoặc chưa được kích hoạt.')
  Future<Map<String, dynamic>?> getFounderLiteMetrics() async {
    throw UnimplementedError('Chế độ kế toán TT58/2024 không khả dụng trên môi trường hiện tại.');
  }

  @Deprecated('Chế độ TT58/2024 không còn hiệu lực hoặc chưa được kích hoạt.')
  Future<Map<String, dynamic>?> createAndPostDocument({
    required String documentNo,
    required String documentType,
    required double amount,
    required String direction,
    required String description,
    String category = 'DOANH_THU',
  }) async {
    throw UnimplementedError('Chế độ kế toán TT58/2024 không khả dụng trên môi trường hiện tại.');
  }

  @Deprecated('Chế độ TT58/2024 không còn hiệu lực hoặc chưa được kích hoạt.')
  Future<Map<String, dynamic>?> voidDocument(String documentId, String reason) async {
    throw UnimplementedError('Chế độ kế toán TT58/2024 không khả dụng trên môi trường hiện tại.');
  }

  @Deprecated('Chế độ TT58/2024 không còn hiệu lực hoặc chưa được kích hoạt.')
  Future<Map<String, dynamic>?> getReportB01() async {
    throw UnimplementedError('Chế độ kế toán TT58/2024 không khả dụng trên môi trường hiện tại.');
  }

  @Deprecated('Chế độ TT58/2024 không còn hiệu lực hoặc chưa được kích hoạt.')
  Future<Map<String, dynamic>?> getReportB02() async {
    throw UnimplementedError('Chế độ kế toán TT58/2024 không khả dụng trên môi trường hiện tại.');
  }

  @Deprecated('Chế độ TT58/2024 không còn hiệu lực hoặc chưa được kích hoạt.')
  Future<Map<String, dynamic>?> getReportB03() async {
    throw UnimplementedError('Chế độ kế toán TT58/2024 không khả dụng trên môi trường hiện tại.');
  }

  @Deprecated('Chế độ TT58/2024 không còn hiệu lực hoặc chưa được kích hoạt.')
  Future<Map<String, dynamic>?> getReportF01() async {
    throw UnimplementedError('Chế độ kế toán TT58/2024 không khả dụng trên môi trường hiện tại.');
  }
}
