import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/routing/app_pages.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';

void main() {
  test('/hub route builds HologramHubView directly, not wrapped in AppShell', () {
    final hubPage = AppPages.routes.firstWhere((p) => p.name == AppRoutes.hub);
    final widget = hubPage.page();
    expect(widget, isA<HologramHubView>());
  });
}
