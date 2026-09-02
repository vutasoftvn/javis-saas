// Task 5 — MutationGate là cổng DUY NHẤT trước mọi mutation nghiệp vụ
// (Approvals/Tasks/Workflows), đọc `SessionController.active.runtime` — không
// đọc UI toggle riêng lẻ. Ma trận test này chứng minh:
//   1) REMOTE_ACCESS + OFFLINE luôn chặn cứng (không bao giờ "allowed"),
//      kể cả khi `modeSource == 'inferred'` (tín hiệu suy đoán).
//   2) `modeSource == 'inferred'` không được có cùng mức tin cậy như
//      `'configured'` — REMOTE_ACCESS/ONLINE suy đoán phải yêu cầu xác nhận
//      rõ ràng (confirmDegraded), không âm thầm "allowed".
//   3) Gate chặn xảy ra TRƯỚC khi có bất kỳ lời gọi HTTP nào — mô phỏng đúng
//      pattern gọi thật trong ApprovalsController/TasksController/
//      WorkflowsController (check gate trước, chỉ gọi ApiClient khi allowed).
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/runtime/mutation_gate.dart';
import 'package:frontend/core/session/session_controller.dart';
import 'package:frontend/core/session/session_snapshot.dart';

SessionSnapshot _snapshot({
  required String mode,
  required String modeSource,
  required String presence,
}) =>
    SessionSnapshot(
      userId: 'user-1',
      workspaceId: 'workspace-1',
      role: 'founder',
      runtime: SessionRuntimeInfo(
        mode: mode,
        modeSource: modeSource,
        presenceStatus: presence,
        lastHeartbeatAt: null,
        asOf: DateTime.utc(2026, 9, 2),
      ),
      capabilities: const [],
    );

/// Mô phỏng đúng pattern gọi thật ở các controller mutation (Approvals/
/// Tasks/Workflows §Task 5): check gate TRƯỚC, chỉ gọi ApiClient khi
/// [MutationPermission.allowed] — không có nhánh nào âm thầm gọi HTTP khi bị
/// chặn hoặc khi confirmDegraded chưa được người dùng xác nhận.
Future<void> _attemptGatedBusinessPost(MutationGate gate) async {
  final permission = gate.check(isMutation: true);
  if (permission == MutationPermission.allowed) {
    await ApiClient.post('/operations/tasks/1/status', body: {'status': 'done'});
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late SessionController session;
  late SessionMutationGate gate;
  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    session = SessionController();
    gate = SessionMutationGate(sessionController: session);
    ApiClient.setBaseUrl('http://company.local');
    ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE');
  });

  tearDown(() {
    ApiClient.client = realClient;
    ApiClient.clearRuntimeContext();
  });

  group('no active session — chưa xác minh gì cả ⇒ chặn bảo toàn', () {
    test('mutation bị chặn khi chưa có session active', () {
      expect(gate.check(isMutation: true), MutationPermission.blockedOffline);
    });

    test('read bị đánh dấu read-only khi chưa có session active', () {
      expect(gate.check(isMutation: false), MutationPermission.blockedReadOnly);
    });
  });

  group('LOCAL_ONLY', () {
    test('modeSource == configured ⇒ allowed', () {
      session.seedForTest(_snapshot(mode: 'LOCAL_ONLY', modeSource: 'configured', presence: 'ONLINE'));
      expect(gate.check(isMutation: true), MutationPermission.allowed);
    });

    // Fix review Task 5 (Important #1) — trước đây nhánh này trả "allowed"
    // vô điều kiện với lý do "không có route cloud để lọt sai". Sai: nếu
    // trạng thái THẬT SỰ là REMOTE_ACCESS+OFFLINE (relay bị chặn có chủ đích)
    // nhưng bị suy đoán nhầm thành LOCAL_ONLY, `ApiClient.resolveUri` gửi
    // THẲNG business request tới `baseUrl` — một địa chỉ company backend CÓ
    // THẬT, không phải lỗi kết nối vô hại. Đây là failure mode "âm thầm gửi
    // request lẽ ra phải bị chặn". modeSource == 'inferred' phải hạ xuống
    // confirmDegraded, giống hệt REMOTE_ACCESS/ONLINE + inferred.
    test('modeSource == inferred ⇒ confirmDegraded, KHÔNG âm thầm allowed '
        '(có thể thực ra là REMOTE_ACCESS+OFFLINE bị suy đoán nhầm)', () {
      session.seedForTest(_snapshot(mode: 'LOCAL_ONLY', modeSource: 'inferred', presence: 'ONLINE'));
      expect(gate.check(isMutation: true), MutationPermission.confirmDegraded);
    });
  });

  // Fix review Task 5 (Important #2) — CLOUD_CONTINUITY là mode thứ ba có
  // thật (session_snapshot.dart, workspace-settings.service.ts trả về với
  // runtimeModeSource LUÔN LUÔN 'inferred'), có thể resolve về OFFLINE
  // (runtime-router.service.ts). `ApiClient` không có nhánh routing/
  // offline-guard riêng cho mode này — trước fix, gate rơi qua nhánh mặc
  // định "allowed" vô điều kiện bất kể presence, tức KHÔNG có tầng phòng thủ
  // nào chặn một mutation khi cả local lẫn cloud đều down.
  group('CLOUD_CONTINUITY — cùng quy tắc với REMOTE_ACCESS (node/relay từ xa)', () {
    test('OFFLINE ⇒ blockedOffline bất kể modeSource', () {
      session.seedForTest(_snapshot(mode: 'CLOUD_CONTINUITY', modeSource: 'configured', presence: 'OFFLINE'));
      expect(gate.check(isMutation: true), MutationPermission.blockedOffline);

      session.seedForTest(_snapshot(mode: 'CLOUD_CONTINUITY', modeSource: 'inferred', presence: 'OFFLINE'));
      expect(gate.check(isMutation: true), MutationPermission.blockedOffline);
    });

    test('DEGRADED ⇒ confirmDegraded', () {
      session.seedForTest(_snapshot(mode: 'CLOUD_CONTINUITY', modeSource: 'configured', presence: 'DEGRADED'));
      expect(gate.check(isMutation: true), MutationPermission.confirmDegraded);
    });

    test('ONLINE + modeSource == inferred (giá trị thực tế hôm nay theo Task 3) ⇒ confirmDegraded', () {
      session.seedForTest(_snapshot(mode: 'CLOUD_CONTINUITY', modeSource: 'inferred', presence: 'ONLINE'));
      expect(gate.check(isMutation: true), MutationPermission.confirmDegraded);
    });

    test('ONLINE + modeSource == configured ⇒ allowed', () {
      session.seedForTest(_snapshot(mode: 'CLOUD_CONTINUITY', modeSource: 'configured', presence: 'ONLINE'));
      expect(gate.check(isMutation: true), MutationPermission.allowed);
    });

    test('read khi không ONLINE ⇒ blockedReadOnly', () {
      session.seedForTest(_snapshot(mode: 'CLOUD_CONTINUITY', modeSource: 'configured', presence: 'OFFLINE'));
      expect(gate.check(isMutation: false), MutationPermission.blockedReadOnly);
    });
  });

  group('mode/presence lạ (chưa nhận diện được) — fail-closed', () {
    test('mode lạ ⇒ blockedOffline, KHÔNG rơi qua allowed mặc định', () {
      session.seedForTest(_snapshot(mode: 'SOME_FUTURE_MODE', modeSource: 'configured', presence: 'ONLINE'));
      expect(gate.check(isMutation: true), MutationPermission.blockedOffline);
    });

    test('presence lạ trong REMOTE_ACCESS ⇒ blockedOffline, không allowed', () {
      session.seedForTest(_snapshot(mode: 'REMOTE_ACCESS', modeSource: 'configured', presence: 'SOME_FUTURE_PRESENCE'));
      expect(gate.check(isMutation: true), MutationPermission.blockedOffline);
    });
  });

  group('REMOTE_ACCESS + ONLINE', () {
    test('modeSource == configured ⇒ allowed', () {
      session.seedForTest(_snapshot(mode: 'REMOTE_ACCESS', modeSource: 'configured', presence: 'ONLINE'));
      expect(gate.check(isMutation: true), MutationPermission.allowed);
    });

    test('modeSource == inferred ⇒ confirmDegraded, KHÔNG âm thầm allowed như đã xác minh', () {
      session.seedForTest(_snapshot(mode: 'REMOTE_ACCESS', modeSource: 'inferred', presence: 'ONLINE'));
      expect(gate.check(isMutation: true), MutationPermission.confirmDegraded);
    });
  });

  group('REMOTE_ACCESS + DEGRADED', () {
    test('luôn confirmDegraded bất kể modeSource', () {
      session.seedForTest(_snapshot(mode: 'REMOTE_ACCESS', modeSource: 'configured', presence: 'DEGRADED'));
      expect(gate.check(isMutation: true), MutationPermission.confirmDegraded);

      session.seedForTest(_snapshot(mode: 'REMOTE_ACCESS', modeSource: 'inferred', presence: 'DEGRADED'));
      expect(gate.check(isMutation: true), MutationPermission.confirmDegraded);
    });
  });

  group('REMOTE_ACCESS + OFFLINE — nguyên tắc lõi, không có ngoại lệ', () {
    test('modeSource == configured ⇒ blockedOffline', () {
      session.seedForTest(_snapshot(mode: 'REMOTE_ACCESS', modeSource: 'configured', presence: 'OFFLINE'));
      expect(gate.check(isMutation: true), MutationPermission.blockedOffline);
    });

    test('modeSource == inferred ⇒ VẪN blockedOffline — không được hạ xuống '
        'như thể LOCAL_ONLY chỉ vì tín hiệu là suy đoán (carried-forward Task 4)', () {
      session.seedForTest(_snapshot(mode: 'REMOTE_ACCESS', modeSource: 'inferred', presence: 'OFFLINE'));
      expect(gate.check(isMutation: true), MutationPermission.blockedOffline);
    });

    test('read ⇒ blockedReadOnly (không chặn cứng như mutation nhưng không giả vờ live)', () {
      session.seedForTest(_snapshot(mode: 'REMOTE_ACCESS', modeSource: 'configured', presence: 'OFFLINE'));
      expect(gate.check(isMutation: false), MutationPermission.blockedReadOnly);
    });
  });

  test('remote offline blocks a business POST before HTTP', () async {
    session.seedForTest(_snapshot(mode: 'REMOTE_ACCESS', modeSource: 'configured', presence: 'OFFLINE'));

    final recorded = <http.BaseRequest>[];
    ApiClient.client = MockClient((request) async {
      recorded.add(request);
      return http.Response('{}', 200);
    });

    final result = gate.check(isMutation: true);
    expect(result, MutationPermission.blockedOffline);

    await _attemptGatedBusinessPost(gate);

    expect(recorded, isEmpty);
  });
}
