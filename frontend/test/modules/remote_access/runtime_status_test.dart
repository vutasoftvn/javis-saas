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

  // Fix-review (2026-09-02, final review I-3) — CLOUD_CONTINUITY dùng CHUNG
  // quy tắc với REMOTE_ACCESS trong MutationGate (cùng đi qua node/relay từ
  // xa có thể offline độc lập) nhưng trước fix, RuntimeStatus chỉ đặc cách
  // remoteAccess ⇒ một workspace CLOUD_CONTINUITY+OFFLINE bị gate chặn
  // (blockedOffline) nhưng banner không hiện gì — dead UI.
  group('CLOUD_CONTINUITY — cùng bộ quy tắc read-only/offline/banner với REMOTE_ACCESS', () {
    test('OFFLINE ⇒ read-only + offline + banner', () {
      final s = RuntimeStatus(mode: RuntimeMode.cloudContinuity, presence: NodePresence.offline);
      expect(s.isReadOnly, isTrue);
      expect(s.isOffline, isTrue);
      expect(s.needsBanner, isTrue);
    });

    test('DEGRADED ⇒ read-only + degraded + banner', () {
      final s = RuntimeStatus(mode: RuntimeMode.cloudContinuity, presence: NodePresence.degraded);
      expect(s.isReadOnly, isTrue);
      expect(s.isDegraded, isTrue);
      expect(s.needsBanner, isTrue);
    });

    test('ONLINE ⇒ không read-only, không banner', () {
      final s = RuntimeStatus(mode: RuntimeMode.cloudContinuity, presence: NodePresence.online);
      expect(s.isReadOnly, isFalse);
      expect(s.needsBanner, isFalse);
    });
  });

  // Fix-review (2026-09-02, final review I-3) — mode lạ/không nhận diện được
  // fail-closed giống hệt nhánh mặc định của MutationGate (không bao giờ rơi
  // qua "an toàn để đọc/ghi live" mặc định).
  test('mode unknown ⇒ fail-closed sang read-only + offline + banner, không phụ thuộc presence', () {
    final s = RuntimeStatus(mode: RuntimeMode.unknown, presence: NodePresence.online);
    expect(s.isReadOnly, isTrue);
    expect(s.isOffline, isTrue);
    expect(s.needsBanner, isTrue);
    expect(s.bannerMessage, contains('Không xác định được chế độ runtime'));
  });

  // Fix-review (2026-09-02, final review I-1) — `modeSource` phải đi tới tận
  // RuntimeStatus (trước đây dừng ở SessionSnapshot) để banner có thể hedge
  // ngôn từ khi giá trị mode chỉ là suy đoán, chưa xác minh.
  group('modeSource — hedge banner khi giá trị mode chỉ là suy đoán', () {
    test('modeSource == inferred ⇒ bannerMessage hedge rõ ràng', () {
      final s = RuntimeStatus(
        mode: RuntimeMode.remoteAccess,
        presence: NodePresence.offline,
        modeSource: 'inferred',
      );
      expect(s.isModeInferred, isTrue);
      expect(s.bannerMessage, contains('suy đoán'));
    });

    test('modeSource == configured ⇒ bannerMessage KHÔNG hedge', () {
      final s = RuntimeStatus(
        mode: RuntimeMode.remoteAccess,
        presence: NodePresence.offline,
        modeSource: 'configured',
      );
      expect(s.isModeInferred, isFalse);
      expect(s.bannerMessage, isNot(contains('suy đoán')));
    });

    test('modeSource == null (chưa rõ nguồn) ⇒ coi như suy đoán, vẫn hedge', () {
      final s = RuntimeStatus(mode: RuntimeMode.remoteAccess, presence: NodePresence.offline);
      expect(s.isModeInferred, isTrue);
      expect(s.bannerMessage, contains('suy đoán'));
    });

    test('fromJson đọc modeSource cả camelCase lẫn snake_case', () {
      final a = RuntimeStatus.fromJson({
        'runtimeMode': 'REMOTE_ACCESS',
        'presence': 'OFFLINE',
        'modeSource': 'inferred',
      });
      expect(a.modeSource, 'inferred');

      final b = RuntimeStatus.fromJson({
        'runtime_mode': 'REMOTE_ACCESS',
        'presence_status': 'OFFLINE',
        'mode_source': 'configured',
      });
      expect(b.modeSource, 'configured');
    });
  });
}
