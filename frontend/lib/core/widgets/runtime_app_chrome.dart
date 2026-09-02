/// Task 5 — khung ứng dụng DUY NHẤT hiển thị [RemoteAccessBanner], đặt phía
/// trên toàn bộ nội dung shell (Dashboard/Hub). Banner chỉ xuất hiện Ở ĐÂY —
/// không lặp lại rải rác ở từng view con — và đọc trạng thái từ
/// `RemoteAccessController`, chính là bản sao được `SessionController`
/// đồng bộ mỗi lần commit (§Task 4/5), không tự parse JSON picker riêng.
library;

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../modules/remote_access/controllers/remote_access_controller.dart';
import '../../modules/remote_access/widgets/remote_access_banner.dart';

class RuntimeAppChrome extends StatelessWidget {
  const RuntimeAppChrome({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    // `RemoteAccessController` có thể chưa được đăng ký (vd. màn hình demo
    // không qua session thật) — coi như không có banner. Chỉ bọc `Obx` khi
    // controller thật sự tồn tại: `Obx` không cho phép build mà KHÔNG đọc
    // observable nào bên trong (ném lỗi "improper use of GetX"), nên nhánh
    // "chưa đăng ký" phải render banner tĩnh thay vì gọi `Obx` rỗng.
    final registered = Get.isRegistered<RemoteAccessController>();
    return Column(
      children: [
        registered
            ? Obx(() => RemoteAccessBanner(
                  status: Get.find<RemoteAccessController>().status.value,
                ))
            : const RemoteAccessBanner(status: null),
        Expanded(child: child),
      ],
    );
  }
}
