import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/chat_panel_content.dart';
import 'package:frontend/modules/workforce/models/workforce_mvp_models.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

// Thẻ duyệt hành động agent ngay trong chat (spec 2026-09-27-chat-business-actions §4.5).

class _FakeWorkforce implements WorkforceMvpService {
  _FakeWorkforce({this.succeed = true});

  final bool succeed;
  final calls = <(String, bool)>[];

  @override
  Future<ApiResult<WorkforceApprovalDecision>> decideApproval(
    String approvalId, {
    required bool approved,
    String? reason,
  }) async {
    calls.add((approvalId, approved));
    if (!succeed) {
      return const ApiFailure(
        ApiFailureDetail(code: ApiFailureCode.invalidRequest, message: 'x'),
      );
    }
    return ApiSuccess(
      data: WorkforceApprovalDecision(
        approvalId: approvalId,
        runId: 'r1',
        status: approved ? 'approved' : 'denied',
        decidedAt: DateTime.utc(2026, 9, 27),
      ),
      meta: ApiResponseMeta(
        dataState: ApiDataState.empty,
        observedAt: DateTime.utc(2026, 9, 27),
      ),
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Map<String, String> _card({String status = 'pending'}) => {
  'role': 'approval',
  'approval_id': 'ap1',
  'title': 'Tạo mục tiêu mới cho COSA',
  'detail': 'Tăng trưởng Q4 (chiến thuật)',
  'status': status,
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  Future<void> pumpPanel(
    WidgetTester tester,
    FounderCommandCenterController c,
  ) async {
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ChatPanelContent(controller: c, onClose: () {}),
        ),
      ),
    );
    await tester.pump();
  }

  testWidgets(
    'shows the summary with approve/reject and never the approval id',
    (tester) async {
      final controller = Get.put(
        FounderCommandCenterController(workforceMvpService: _FakeWorkforce()),
      );
      controller.chatMessages.add(_card());
      await pumpPanel(tester, controller);

      expect(find.text('Tạo mục tiêu mới cho COSA'), findsOneWidget);
      expect(find.text('Tăng trưởng Q4 (chiến thuật)'), findsOneWidget);
      expect(find.textContaining('ap1'), findsNothing);
      expect(find.text('Duyệt'), findsOneWidget);
      expect(find.text('Từ chối'), findsOneWidget);
    },
  );

  testWidgets(
    'approve calls the decision endpoint and shows the resolved label',
    (tester) async {
      final fake = _FakeWorkforce();
      final controller = Get.put(
        FounderCommandCenterController(workforceMvpService: fake),
      );
      controller.chatMessages.add(_card());
      await pumpPanel(tester, controller);

      await tester.tap(find.text('Duyệt'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(fake.calls, [('ap1', true)]);
      expect(find.text('Duyệt'), findsNothing);
      expect(find.text('Đã duyệt'), findsOneWidget);
      // Run resume -> bong bóng trả lời của agent quay lại chờ nội dung.
      expect(controller.isChatLoading.value, isTrue);
      expect(controller.chatMessages.last['role'], 'cosa');
    },
  );

  testWidgets('reject calls the decision endpoint with approved=false', (
    tester,
  ) async {
    final fake = _FakeWorkforce();
    final controller = Get.put(
      FounderCommandCenterController(workforceMvpService: fake),
    );
    controller.chatMessages.add(_card());
    await pumpPanel(tester, controller);

    await tester.tap(find.text('Từ chối'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(fake.calls, [('ap1', false)]);
    expect(find.text('Đã từ chối'), findsOneWidget);
  });

  testWidgets('failed decision keeps the card pending', (tester) async {
    final controller = Get.put(
      FounderCommandCenterController(
        workforceMvpService: _FakeWorkforce(succeed: false),
      ),
    );
    controller.chatMessages.add(_card());
    await pumpPanel(tester, controller);

    await tester.tap(find.text('Duyệt'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(controller.chatMessages.first['status'], 'pending');
    expect(find.text('Duyệt'), findsOneWidget);
  });

  testWidgets('resolved and expired cards hide the buttons', (tester) async {
    final controller = Get.put(
      FounderCommandCenterController(workforceMvpService: _FakeWorkforce()),
    );
    controller.chatMessages.add(_card(status: 'expired'));
    await pumpPanel(tester, controller);

    expect(find.text('Duyệt'), findsNothing);
    expect(find.text('Hết hạn'), findsOneWidget);
  });
}
