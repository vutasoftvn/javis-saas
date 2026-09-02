/// Task 5 — cổng gate DUY NHẤT cho mọi mutation nghiệp vụ (Approvals/Tasks/
/// Workflows, ...) trước khi gọi service. Nguồn sự thật là
/// `SessionController.active.value.runtime` — KHÔNG đọc theo từng UI toggle
/// riêng lẻ (mỗi widget tự giữ một biến `isOffline` local dễ lệch pha với
/// nhau). Nguyên tắc lõi (plan Global Constraints): REMOTE_ACCESS với node
/// OFFLINE không được gửi business request và không được fallback cloud.
library;

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../session/session_controller.dart';
import '../session/session_snapshot.dart';

enum MutationPermission { allowed, confirmDegraded, blockedOffline, blockedReadOnly }

abstract interface class MutationGate {
  MutationPermission check({required bool isMutation});
}

/// Cài đặt duy nhất dùng trong app thật. Đọc `SessionController.active`
/// (server-authoritative kể từ Task 3/4) thay vì tự giữ state riêng.
class SessionMutationGate implements MutationGate {
  SessionMutationGate({SessionController? sessionController})
      : _injected = sessionController;

  final SessionController? _injected;
  SessionController get _session => _injected ?? Get.find<SessionController>();

  static const _modeRemoteAccess = 'REMOTE_ACCESS';
  static const _presenceOnline = 'ONLINE';
  static const _presenceDegraded = 'DEGRADED';
  static const _presenceOffline = 'OFFLINE';
  static const _sourceConfigured = 'configured';

  @override
  MutationPermission check({required bool isMutation}) {
    final runtime = _session.active.value?.runtime;

    // Chưa có session nào được xác minh (chưa login / vừa logout giữa
    // chừng) ⇒ không có gì để tin, chặn ở phía an toàn nhất thay vì suy diễn
    // "chắc là ổn".
    if (runtime == null) {
      return isMutation
          ? MutationPermission.blockedOffline
          : MutationPermission.blockedReadOnly;
    }

    return isMutation ? _checkMutation(runtime) : _checkRead(runtime);
  }

  MutationPermission _checkRead(SessionRuntimeInfo runtime) {
    if (runtime.mode == _modeRemoteAccess && runtime.presenceStatus != _presenceOnline) {
      return MutationPermission.blockedReadOnly;
    }
    return MutationPermission.allowed;
  }

  MutationPermission _checkMutation(SessionRuntimeInfo runtime) {
    // (1) REMOTE_ACCESS + OFFLINE luôn chặn cứng, KHÔNG có ngoại lệ theo
    // `modeSource`. Đây là nguyên tắc lõi của kế hoạch: dù tín hiệu là suy
    // đoán ('inferred', xem `SessionRuntimeInfo.modeSource`) hay đã xác minh
    // ('configured'), một khi hệ thống báo OFFLINE thì không được hạ nó
    // xuống ngang với LOCAL_ONLY rồi cho mutation lọt qua — thà chặn nhầm
    // còn hơn gửi nhầm business request khi node có thể thật sự offline.
    if (runtime.mode == _modeRemoteAccess && runtime.presenceStatus == _presenceOffline) {
      return MutationPermission.blockedOffline;
    }

    if (runtime.mode == _modeRemoteAccess && runtime.presenceStatus == _presenceDegraded) {
      return MutationPermission.confirmDegraded;
    }

    if (runtime.mode == _modeRemoteAccess && runtime.presenceStatus == _presenceOnline) {
      // `modeSource == 'inferred'` nghĩa là `cosa` hiện CHƯA có adapter đọc
      // canonical runtime_mode thật từ `services/company` — giá trị
      // REMOTE_ACCESS/ONLINE này chỉ là heuristic suy đoán theo presence, có
      // thể sai. Không cho nó có cùng mức tin cậy như config đã xác minh:
      // bắt xác nhận rõ ràng của người dùng thay vì âm thầm "allowed".
      if (runtime.modeSource != _sourceConfigured) {
        return MutationPermission.confirmDegraded;
      }
      return MutationPermission.allowed;
    }

    // LOCAL_ONLY (hoặc mode lạ khác REMOTE_ACCESS): `ApiClient.resolveUri`
    // không áp dụng relay routing / offline-guard cho nhánh này, nên rủi ro
    // lớn nhất khi suy đoán sai (`modeSource == 'inferred'` nhưng thực tế là
    // REMOTE_ACCESS+OFFLINE) là request đi thẳng ra local port thật và tự
    // thất bại bằng lỗi kết nối mạng — KHÔNG có đường fallback cloud nào để
    // âm thầm chạy nhầm. Vì vậy không cần hạ permission ở nhánh này.
    return MutationPermission.allowed;
  }
}

/// UI helper — text giải thích khi control bị vô hiệu hoá vì
/// [MutationPermission.blockedOffline]/[MutationPermission.blockedReadOnly].
/// Hiển thị TRƯỚC khi người dùng bấm (tooltip trên control đã disable), KHÔNG
/// phải error toast SAU khi bấm.
extension MutationPermissionUi on MutationPermission {
  bool get isHardBlocked =>
      this == MutationPermission.blockedOffline || this == MutationPermission.blockedReadOnly;

  String get blockedTooltip {
    switch (this) {
      case MutationPermission.blockedOffline:
        return 'Node workspace đang offline (REMOTE_ACCESS) — không thể gửi thao tác này lúc này, hệ thống không tự chuyển sang cloud.';
      case MutationPermission.blockedReadOnly:
        return 'Đang ở chế độ chỉ đọc — không thể thực hiện thao tác này lúc này.';
      case MutationPermission.confirmDegraded:
      case MutationPermission.allowed:
        return '';
    }
  }
}

/// Dialog xác nhận dùng chung cho mọi mutation surface khi gate trả về
/// [MutationPermission.confirmDegraded] — đặt tên rõ điều kiện runtime hiện
/// tại và bắt xác nhận tường minh, không tự động coi "im lặng" là đồng ý.
Future<bool> confirmDegradedMutation(
  BuildContext context, {
  required String actionLabel,
}) async {
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Xác nhận thao tác khi runtime chưa ổn định'),
      content: Text(
        'Kết nối tới runtime node của workspace đang chập chờn hoặc chưa được '
        'xác minh đầy đủ (chỉ là suy đoán, không phải cấu hình đã xác nhận). '
        'Bạn có chắc chắn muốn tiếp tục "$actionLabel"?',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(false),
          child: const Text('Hủy'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(ctx).pop(true),
          child: const Text('Vẫn tiếp tục'),
        ),
      ],
    ),
  );
  return confirmed ?? false;
}
