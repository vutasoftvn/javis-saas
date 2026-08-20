import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Local Projection Cache Tests', () {
    test('có thể lưu và đọc projection từ local database (SQLite/Isar/Hive)', () {
      // TODO: Test lưu projection (chỉ state + cursor, không có secret)
    });

    test('phát hiện cursor gap và yêu cầu full rebuild', () {
      // Nếu current cursor là 5, mà server trả về event từ 10, phải fetch lại từ 0
    });

    test('có thể tự phục hồi nếu local db bị xóa', () {
      // Nếu db trống, tự động sync từ cursor 0
    });
  });
}
