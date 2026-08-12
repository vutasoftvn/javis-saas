import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/services/feature_flags_controller.dart';

class _FakeFeatureFlagsLoader implements FeatureFlagsLoader {
  @override
  Future<Map<String, bool>> load() async => {'finance_function_v13': true};
}

void main() {
  test('loads flags and treats missing flags as disabled', () async {
    final controller = FeatureFlagsController(loader: _FakeFeatureFlagsLoader());

    await controller.load();

    expect(controller.isEnabled('finance_function_v13'), isTrue);
    expect(controller.isEnabled('legal_function_v13'), isFalse);
  });
}
