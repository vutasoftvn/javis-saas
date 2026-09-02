import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/marketing/services/marketing_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'workspace-1',
    });
  });

  test('MarketingApiException stores status code and message', () {
    final ex = MarketingApiException(404, 'Không tìm thấy brain');
    expect(ex.statusCode, 404);
    expect(ex.message, 'Không tìm thấy brain');
    expect(ex.toString(), 'Không tìm thấy brain');
  });

  test('MarketingService instantiate cleanly', () {
    final service = MarketingService();
    expect(service, isNotNull);
  });
}
