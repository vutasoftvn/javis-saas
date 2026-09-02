// Task 10 — helper dùng chung cho test golden/accessibility ở 3 bậc width
// (compact 390 / medium 834 / expanded 1440). Đặt tại đây thay vì lặp lại
// trong từng file test — nhiều test ở `test/golden` và `test/accessibility`
// cùng cần pump một widget ở một `width` cụ thể rồi dọn lại kích thước mặc
// định của binding sau khi test xong.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

/// Pump [child] bên trong một `GetMaterialApp` với view có kích thước vật lý
/// cố định bằng [width] (chiều cao giữ cố định 1200 — đủ cho hầu hết nội
/// dung cuộn được, tránh false-positive overflow theo chiều dọc không liên
/// quan tới bậc layout đang test).
Future<void> pumpAtWidth(
  WidgetTester tester,
  Widget child,
  double width, {
  double height = 1200,
}) async {
  final view = tester.view;
  view.physicalSize = Size(width, height);
  view.devicePixelRatio = 1.0;
  addTearDown(view.resetPhysicalSize);
  addTearDown(view.resetDevicePixelRatio);

  await tester.pumpWidget(
    GetMaterialApp(
      debugShowCheckedModeBanner: false,
      home: Scaffold(body: child),
    ),
  );
  // Không dùng `pumpAndSettle` ở đây — nhiều view có spinner tải dữ liệu
  // (`CircularProgressIndicator`) chạy animation vô hạn khi gọi service thật
  // thất bại/không trả lời trong môi trường test (không có network thật),
  // khiến `pumpAndSettle` không bao giờ ổn định và timeout. Hai lần pump với
  // một khoảng thời gian ngắn là đủ để layout/Obx ổn định cho mục đích test
  // responsive (không cần animation hoàn tất).
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 100));
}

/// 3 bậc width chuẩn dùng cho golden/accessibility test — khớp đúng ranh
/// giới của `layoutForWidth` (compact < 600, medium < 1024, expanded còn
/// lại), lấy giá trị đại diện an toàn cho từng bậc (không phải giá trị biên).
const double kCompactWidth = 390;
const double kMediumWidth = 834;
const double kExpandedWidth = 1440;
