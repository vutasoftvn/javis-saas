import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/routing/module_routes.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  test('resolveLegacyDashboardTarget covers every call site used by HubCommandMixin/HubVoiceMixin', () {
    // Xem hub_voice_mixin.dart:123-158 và hub_command_mixin.dart:350-353 —
    // các targetTab thật đang được gọi trong codebase.
    final usedTargetTabs = {1, 3, 24, 25, 26, 27, 28, 0, 13};
    for (final tab in usedTargetTabs) {
      final path = resolveLegacyDashboardTarget(tab);
      expect(path, isNotEmpty);
      expect(path == '/hub' || path.startsWith('/work/'), isTrue,
          reason: 'targetTab $tab phải map ra 1 route hợp lệ, nhận được "$path"');
    }
  });
}
