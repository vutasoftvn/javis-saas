import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/legal/controllers/legal_obligation_controller.dart';
import 'package:frontend/modules/legal/services/legal_service.dart';
import 'package:frontend/modules/legal/views/widgets/obligation_list_view.dart';

class MockFlowLegalService extends LegalService {
  final List<Map<String, dynamic>> mockInstances = [
    {
      'id': 'ob_open_1',
      'title': 'Khai thuế GTGT Quý 1',
      'status': 'OPEN',
      'periodKey': '2026-Q1',
      'dueDate': '2026-04-30',
    },
    {
      'id': 'ob_progress_1',
      'title': 'Nộp báo cáo tài chính năm',
      'status': 'IN_PROGRESS',
      'periodKey': '2025',
      'dueDate': '2026-03-31',
    },
    {
      'id': 'ob_done_1',
      'title': 'Đăng ký thay đổi thông tin doanh nghiệp',
      'status': 'FULFILLED',
      'periodKey': '2026-02',
      'dueDate': '2026-02-15',
    },
  ];

  @override
  Future<List<dynamic>> getObligationInstances({String? status}) async {
    return mockInstances;
  }

  @override
  Future<Map<String, dynamic>?> transitionObligationInstance(
    String id, {
    required String toStatus,
    String? expectedFromStatus,
    List<String>? evidenceRefs,
    String? evidenceArtifactId,
    String? rationale,
  }) async {
    final item = mockInstances.firstWhere((e) => e['id'] == id);
    item['status'] = toStatus;
    return item;
  }
}

void main() {
  setUp(() {
    Get.reset();
  });

  testWidgets('renders obligation list and supports status transitions', (tester) async {
    final mockService = MockFlowLegalService();
    Get.put(LegalObligationController(service: mockService));

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ObligationListView(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Verify titles rendered
    expect(find.text('Khai thuế GTGT Quý 1'), findsOneWidget);
    expect(find.text('Nộp báo cáo tài chính năm'), findsOneWidget);
    expect(find.text('Đăng ký thay đổi thông tin doanh nghiệp'), findsOneWidget);

    // Verify status buttons
    expect(find.text('Bắt đầu thực hiện'), findsOneWidget);
    expect(find.text('Hoàn thành (Kèm chứng từ)'), findsOneWidget);
    expect(find.text('Đã hoàn thành'), findsOneWidget);

    // Tap "Bắt đầu thực hiện"
    await tester.tap(find.text('Bắt đầu thực hiện'));
    await tester.pumpAndSettle();

    // The item status is now transitioned
    expect(mockService.mockInstances.firstWhere((e) => e['id'] == 'ob_open_1')['status'], 'IN_PROGRESS');
  });
}
