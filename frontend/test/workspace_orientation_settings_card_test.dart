import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/settings/models/workspace_orientation.dart';
import 'package:frontend/modules/settings/services/workspace_orientation_service.dart';
import 'package:frontend/modules/settings/views/widgets/workspace_orientation_settings_card.dart';

class FakeWorkspaceOrientationService extends WorkspaceOrientationService {
  FakeWorkspaceOrientationService({
    this.initialOrientation,
    this.fetchError,
    this.saveError,
  }) {
    if (initialOrientation != null) {
      currentOrientation = initialOrientation!;
    }
  }

  WorkspaceOrientation currentOrientation = const WorkspaceOrientation(
    workspaceId: 'ws_1',
    vision: null,
    mission: null,
    coreValues: null,
  );

  final WorkspaceOrientation? initialOrientation;
  final Exception? fetchError;
  final Exception? saveError;

  String? lastSavedVision;
  String? lastSavedMission;
  String? lastSavedCoreValues;
  int updateCallCount = 0;

  @override
  Future<WorkspaceOrientation> fetch(String workspaceId) async {
    if (fetchError != null) throw fetchError!;
    return currentOrientation;
  }

  @override
  Future<WorkspaceOrientation> update(
    String workspaceId, {
    required String? vision,
    required String? mission,
    required String? coreValues,
  }) async {
    if (saveError != null) throw saveError!;
    updateCallCount++;
    lastSavedVision = vision;
    lastSavedMission = mission;
    lastSavedCoreValues = coreValues;
    currentOrientation = WorkspaceOrientation(
      workspaceId: workspaceId,
      vision: vision,
      mission: mission,
      coreValues: coreValues,
    );
    return currentOrientation;
  }
}

void main() {
  Widget buildTestWidget({
    WorkspaceOrientationService? service,
    Future<String?> Function()? readWorkspaceId,
  }) {
    return MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(
          child: WorkspaceOrientationSettingsCard(
            service: service,
            readWorkspaceId: readWorkspaceId,
          ),
        ),
      ),
    );
  }

  group('WorkspaceOrientationSettingsCard', () {
    testWidgets('null workspace ID renders Chưa chọn workspace and no form fields',
        (tester) async {
      await tester.pumpWidget(
        buildTestWidget(
          readWorkspaceId: () async => null,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Chưa chọn workspace'), findsOneWidget);
      expect(find.byType(TextField), findsNothing);
    });

    testWidgets(
        'fetched all-null orientation renders Chưa xác định and a voluntary Thêm định hướng action',
        (tester) async {
      final fakeService = FakeWorkspaceOrientationService(
        initialOrientation: const WorkspaceOrientation(
          workspaceId: 'ws_1',
          vision: null,
          mission: null,
          coreValues: null,
        ),
      );

      await tester.pumpWidget(
        buildTestWidget(
          service: fakeService,
          readWorkspaceId: () async => 'ws_1',
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Chưa xác định'), findsOneWidget);
      expect(find.text('Thêm định hướng'), findsOneWidget);
      expect(find.byType(TextField), findsNothing);
    });

    testWidgets('saving only Mission sends vision null, Mission text, and coreValues null',
        (tester) async {
      final fakeService = FakeWorkspaceOrientationService(
        initialOrientation: const WorkspaceOrientation(
          workspaceId: 'ws_1',
          vision: null,
          mission: null,
          coreValues: null,
        ),
      );

      await tester.pumpWidget(
        buildTestWidget(
          service: fakeService,
          readWorkspaceId: () async => 'ws_1',
        ),
      );
      await tester.pumpAndSettle();

      // Click Thêm định hướng
      await tester.tap(find.text('Thêm định hướng'));
      await tester.pumpAndSettle();

      expect(find.byType(TextField), findsNWidgets(3));

      // Enter text only in Mission field (second text field)
      final missionFinder = find.widgetWithText(TextField, 'Vấn đề/kết quả đang hướng tới (Mission)');
      if (missionFinder.evaluate().isNotEmpty) {
        await tester.enterText(missionFinder, 'Chỉ làm Mission');
      } else {
        // Fallback finder by index
        await tester.enterText(find.byType(TextField).at(1), 'Chỉ làm Mission');
      }
      await tester.pumpAndSettle();

      // Tap Lưu thay đổi
      await tester.tap(find.text('Lưu thay đổi'));
      await tester.pumpAndSettle();

      expect(fakeService.updateCallCount, 1);
      expect(fakeService.lastSavedVision, isNull);
      expect(fakeService.lastSavedMission, 'Chỉ làm Mission');
      expect(fakeService.lastSavedCoreValues, isNull);
    });

    testWidgets('Xóa định hướng calls update with three null fields and returns to truthful empty state',
        (tester) async {
      final fakeService = FakeWorkspaceOrientationService(
        initialOrientation: const WorkspaceOrientation(
          workspaceId: 'ws_1',
          vision: 'Tầm nhìn cũ',
          mission: 'Sứ mệnh cũ',
          coreValues: 'Giá trị cốt lõi cũ',
        ),
      );

      await tester.pumpWidget(
        buildTestWidget(
          service: fakeService,
          readWorkspaceId: () async => 'ws_1',
        ),
      );
      await tester.pumpAndSettle();

      // Should be in filled state, with Xóa định hướng button
      expect(find.text('Xóa định hướng'), findsOneWidget);

      await tester.tap(find.text('Xóa định hướng'));
      await tester.pumpAndSettle();

      expect(fakeService.updateCallCount, 1);
      expect(fakeService.lastSavedVision, isNull);
      expect(fakeService.lastSavedMission, isNull);
      expect(fakeService.lastSavedCoreValues, isNull);

      // Now truthful empty state
      expect(find.text('Chưa xác định'), findsOneWidget);
    });

    testWidgets('fetch or save error renders a visible error message and keeps the user in Settings',
        (tester) async {
      final fakeService = FakeWorkspaceOrientationService(
        fetchError: WorkspaceOrientationException('Không thể tải định hướng'),
      );

      await tester.pumpWidget(
        buildTestWidget(
          service: fakeService,
          readWorkspaceId: () async => 'ws_1',
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('Không thể tải định hướng'), findsOneWidget);
      expect(find.text('Thử lại'), findsOneWidget);
    });
  });
}
