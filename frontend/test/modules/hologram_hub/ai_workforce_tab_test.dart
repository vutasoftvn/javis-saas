// Fix-review (2026-09-02, final review I-2 / I-3):
//  - I-2: `FounderCommandCenterController.workforceState` (Task 3) was set to
//    `WorkforceLoadState.unavailable` on failure, but nothing in the widget
//    tree read it — the tab silently rendered an empty grid indistinguishable
//    from "workspace legitimately has zero packs". Prove the widget now
//    renders an honest unavailable message when `loadState` says so.
//  - I-3: `cofounder_api_service.dart` hard-codes `isCore: false` for every
//    composition entry, so `coreDomains` is now permanently empty. The old
//    static header "5 CORE DOMAIN WORKFORCE" asserted a count the real data
//    can never produce. Prove the header is derived from the data instead.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/data/models/workforce_pack_model.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/ai_workforce_tab.dart';

WorkforcePackModel _pack(String key, {bool isCore = false}) {
  return WorkforcePackModel(
    key: key,
    name: key,
    category: isCore ? 'DOMAIN' : 'OPTIONAL_DOMAIN',
    isCore: isCore,
    isActive: true,
  );
}

Future<void> _pumpTab(
  WidgetTester tester, {
  required List<WorkforcePackModel> packs,
  WorkforceLoadState? loadState,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: AiWorkforceTab(
          packs: packs,
          onTogglePack: (_, _) {},
          loadState: loadState,
        ),
      ),
    ),
  );
}

void main() {
  testWidgets(
    'renders an honest unavailable message when loadState is unavailable, '
    'not a silently-empty grid',
    (tester) async {
      await _pumpTab(
        tester,
        packs: const [],
        loadState: WorkforceLoadState.unavailable,
      );

      expect(
        find.textContaining('Không tải được danh sách AI Workforce'),
        findsOneWidget,
      );
      expect(find.text('5 CORE DOMAIN WORKFORCE (Luôn kích hoạt)'), findsNothing);
    },
  );

  testWidgets(
    'header no longer asserts a fixed "5 CORE DOMAIN" claim when the real '
    'composition data marks every pack as non-core',
    (tester) async {
      await _pumpTab(
        tester,
        packs: [_pack('sales', isCore: false), _pack('marketing', isCore: false)],
      );

      expect(find.text('5 CORE DOMAIN WORKFORCE (Luôn kích hoạt)'), findsNothing);
      expect(
        find.textContaining('CORE DOMAIN WORKFORCE (chưa có dữ liệu phân loại)'),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'header count reflects the actual number of core packs when present',
    (tester) async {
      await _pumpTab(
        tester,
        packs: [
          _pack('sales', isCore: true),
          _pack('cfo', isCore: true),
          _pack('marketing', isCore: false),
        ],
      );

      expect(find.textContaining('2 CORE DOMAIN WORKFORCE'), findsOneWidget);
    },
  );

  testWidgets(
    'renders normally (unchanged behavior) when loadState is not passed',
    (tester) async {
      await _pumpTab(tester, packs: const []);

      expect(
        find.textContaining('Không tải được danh sách AI Workforce'),
        findsNothing,
      );
    },
  );
}
