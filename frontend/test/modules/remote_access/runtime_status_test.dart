// M5 §5 — RuntimeStatus parsing + read-only / offline / staleness semantics.
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/remote_access/models/runtime_status.dart';

void main() {
  test('parse camelCase + snake_case', () {
    final a = RuntimeStatus.fromJson({
      'runtimeMode': 'REMOTE_ACCESS',
      'presence': 'ONLINE',
      'lastHeartbeatAt': '2026-08-29T10:00:00Z',
    });
    expect(a.mode, RuntimeMode.remoteAccess);
    expect(a.presence, NodePresence.online);
    expect(a.lastHeartbeatAt, isNotNull);

    final b = RuntimeStatus.fromJson({
      'runtime_mode': 'LOCAL_ONLY',
      'presence_status': 'OFFLINE',
    });
    expect(b.mode, RuntimeMode.localOnly);
    expect(b.presence, NodePresence.offline);
  });

  test('LOCAL_ONLY không bao giờ read-only / offline / cần banner', () {
    final s = RuntimeStatus(mode: RuntimeMode.localOnly, presence: NodePresence.offline);
    expect(s.isReadOnly, isFalse);
    expect(s.isOffline, isFalse);
    expect(s.needsBanner, isFalse);
  });

  test('REMOTE_ACCESS + OFFLINE ⇒ read-only + offline + banner + staleness label', () {
    final s = RuntimeStatus(
      mode: RuntimeMode.remoteAccess,
      presence: NodePresence.offline,
      asOf: DateTime.utc(2026, 8, 29, 9, 30),
    );
    expect(s.isReadOnly, isTrue);
    expect(s.isOffline, isTrue);
    expect(s.needsBanner, isTrue);
    expect(s.stalenessLabel, contains('Dữ liệu tính đến'));
    expect(s.bannerMessage, contains('Không tự chuyển sang cloud'));
  });

  test('REMOTE_ACCESS + DEGRADED ⇒ read-only + degraded, không offline', () {
    final s = RuntimeStatus(mode: RuntimeMode.remoteAccess, presence: NodePresence.degraded);
    expect(s.isDegraded, isTrue);
    expect(s.isOffline, isFalse);
    expect(s.isReadOnly, isTrue);
    expect(s.needsBanner, isTrue);
  });

  test('REMOTE_ACCESS + ONLINE ⇒ không read-only, không banner', () {
    final s = RuntimeStatus(mode: RuntimeMode.remoteAccess, presence: NodePresence.online);
    expect(s.isReadOnly, isFalse);
    expect(s.needsBanner, isFalse);
    expect(s.stalenessLabel, isNull);
  });

  test('wire round-trip mode/presence', () {
    expect(RuntimeStatus.modeWire(RuntimeMode.remoteAccess), 'REMOTE_ACCESS');
    expect(RuntimeStatus.presenceWire(NodePresence.degraded), 'DEGRADED');
  });
}
