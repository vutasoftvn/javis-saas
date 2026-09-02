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

  static const _modeLocalOnly = 'LOCAL_ONLY';
  static const _modeRemoteAccess = 'REMOTE_ACCESS';
  static const _modeCloudContinuity = 'CLOUD_CONTINUITY';
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
    // REMOTE_ACCESS và CLOUD_CONTINUITY đều đi qua một node/relay có thể
    // rớt kết nối — không ONLINE ⇒ chỉ đọc (banner "chỉ đọc" + as_of), không
    // giả vờ dữ liệu là live. LOCAL_ONLY không có khái niệm node từ xa nên
    // không áp dụng nhánh này.
    if ((runtime.mode == _modeRemoteAccess || runtime.mode == _modeCloudContinuity) &&
        runtime.presenceStatus != _presenceOnline) {
      return MutationPermission.blockedReadOnly;
    }
    if (runtime.mode != _modeLocalOnly &&
        runtime.mode != _modeRemoteAccess &&
        runtime.mode != _modeCloudContinuity) {
      // Giá trị mode không nhận diện được (chưa tồn tại hôm nay, hoặc lỗi
      // parse) ⇒ fail-closed: không giả định là "chắc ổn để đọc live".
      return MutationPermission.blockedReadOnly;
    }
    return MutationPermission.allowed;
  }

  MutationPermission _checkMutation(SessionRuntimeInfo runtime) {
    switch (runtime.mode) {
      // REMOTE_ACCESS và CLOUD_CONTINUITY dùng CHUNG một quy tắc: cả hai đều
      // định tuyến business traffic qua một relay/node từ xa có thể offline
      // độc lập với địa chỉ company backend cấu hình sẵn — không có cách nào
      // để "gửi thẳng" an toàn khi node đó không ONLINE.
      // `services/cosa/services/workspace-settings.service.ts` (Task 3) trả
      // `CLOUD_CONTINUITY` với `runtimeModeSource` LUÔN LUÔN là 'inferred'
      // khi workspace có cloud node đăng ký — runtime-router.service.ts xác
      // nhận state này có thể hợp lệ resolve về OFFLINE (cả local lẫn cloud
      // đều down). ApiClient hiện KHÔNG có nhánh routing/offline-guard riêng
      // cho CLOUD_CONTINUITY (chỉ check `== 'REMOTE_ACCESS'`) — nghĩa là nếu
      // gate không tự chặn ở đây, một mutation trong trạng thái này sẽ đi
      // thẳng KHÔNG qua bất kỳ offline-guard nào ở tầng dưới. Gate phải là
      // tuyến phòng thủ duy nhất cho case này cho tới khi ApiClient được bổ
      // sung nhánh riêng.
      case _modeRemoteAccess:
      case _modeCloudContinuity:
        return _checkRelayedMutation(runtime);

      case _modeLocalOnly:
        // `modeSource == 'inferred'` nghĩa là giá trị LOCAL_ONLY này chỉ là
        // suy đoán, CHƯA được xác minh bằng canonical config
        // (`services/company`). Review Task 5 chỉ ra: nếu trạng thái THẬT
        // sự là REMOTE_ACCESS+OFFLINE (relay bị chặn có chủ đích vì node đó
        // không đáng tin để gửi thẳng) nhưng bị suy đoán nhầm thành
        // LOCAL_ONLY, gate cũ sẽ cho mutation lọt qua "allowed" và
        // `ApiClient.resolveUri` gửi THẲNG tới `baseUrl` — một địa chỉ công
        // ty CÓ THẬT, không phải lỗi kết nối vô hại như giả định ban đầu.
        // Đây chính là failure mode "âm thầm gửi request lẽ ra phải bị
        // chặn" — không được để nó tồn tại. Xử lý giống hệt
        // REMOTE_ACCESS/ONLINE + inferred: bắt xác nhận rõ ràng thay vì
        // âm thầm "allowed".
        if (runtime.modeSource != _sourceConfigured) {
          return MutationPermission.confirmDegraded;
        }
        return MutationPermission.allowed;

      default:
        // Giá trị mode không nhận diện được (mode mới trong tương lai, hoặc
        // lỗi parse) ⇒ fail-closed: KHÔNG rơi qua "allowed" mặc định. Một
        // mode lạ có thể mang ngữ nghĩa routing hoàn toàn khác mà gate chưa
        // biết cách xử lý an toàn.
        return MutationPermission.blockedOffline;
    }
  }

  /// Quy tắc dùng chung cho mọi mode có khái niệm "node/relay từ xa có thể
  /// offline độc lập" (REMOTE_ACCESS, CLOUD_CONTINUITY).
  MutationPermission _checkRelayedMutation(SessionRuntimeInfo runtime) {
    // (1) OFFLINE luôn chặn cứng, KHÔNG có ngoại lệ theo `modeSource`. Đây
    // là nguyên tắc lõi của kế hoạch: dù tín hiệu là suy đoán ('inferred',
    // xem `SessionRuntimeInfo.modeSource`) hay đã xác minh ('configured'),
    // một khi hệ thống báo OFFLINE thì không được hạ nó xuống ngang với
    // LOCAL_ONLY rồi cho mutation lọt qua — thà chặn nhầm còn hơn gửi nhầm
    // business request khi node có thể thật sự offline.
    if (runtime.presenceStatus == _presenceOffline) {
      return MutationPermission.blockedOffline;
    }

    if (runtime.presenceStatus == _presenceDegraded) {
      return MutationPermission.confirmDegraded;
    }

    if (runtime.presenceStatus == _presenceOnline) {
      // `modeSource == 'inferred'` nghĩa là `cosa` hiện CHƯA có adapter đọc
      // canonical runtime_mode thật từ `services/company` — giá trị
      // ONLINE này chỉ là heuristic suy đoán theo presence, có thể sai.
      // Không cho nó có cùng mức tin cậy như config đã xác minh: bắt xác
      // nhận rõ ràng của người dùng thay vì âm thầm "allowed".
      if (runtime.modeSource != _sourceConfigured) {
        return MutationPermission.confirmDegraded;
      }
      return MutationPermission.allowed;
    }

    // Giá trị presence không nhận diện được ⇒ cũng fail-closed thay vì
    // "allowed" mặc định.
    return MutationPermission.blockedOffline;
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
