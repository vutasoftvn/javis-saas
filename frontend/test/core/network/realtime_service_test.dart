// Task 8 — chứng minh hai bug cốt lõi của SSE layer cũ đã được sửa:
// (1) parser cũ dispatch trên TỪNG dòng `data:` riêng lẻ thay vì gom hết các
//     dòng `data:` của một frame rồi decode JSON đúng một lần khi gặp dòng
//     trống (ranh giới frame theo SSE spec) — vỡ mọi payload JSON nhiều dòng.
// (2) reconnect cũ không biết workspace nào đang active, có thể gửi
//     `Last-Event-ID` của workspace A lên request mở stream cho workspace B.
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/realtime_service.dart';
import 'package:frontend/core/services/secure_storage_service.dart';

import '../services/fakes/fake_secret_store.dart';

/// Ghi lại header `Last-Event-ID` của lần mở SSE gần nhất — `null` khi lần
/// đó không gửi header này. Trả về một stream KHÔNG BAO GIỜ đóng để
/// `RealtimeService` không tự lên lịch reconnect thật giữa các assertion của
/// test (tránh Timer treo lại sau khi test kết thúc).
class _RecordingSseClient extends http.BaseClient {
  String? lastEventId;
  final List<StreamController<List<int>>> _openControllers = [];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    lastEventId = request.headers['Last-Event-ID'];
    final controller = StreamController<List<int>>();
    _openControllers.add(controller);
    return http.StreamedResponse(controller.stream, 200);
  }

  void closeAll() {
    for (final c in _openControllers) {
      if (!c.isClosed) c.close();
    }
    _openControllers.clear();
  }
}

RealtimeEnvelope _envelope({String? id, String event = 'approval.updated'}) =>
    RealtimeEnvelope(event: event, data: const {}, id: id);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());
  });

  tearDown(() {
    SecureStorageService.resetForTest();
  });

  group('parseSse — frame accumulation', () {
    test('joins multiline data and dispatches only on a blank line', () {
      final events = parseSse(
        'id: 42\nevent: approval.updated\ndata: {"id":\ndata: "a1"}\n\n',
      );

      expect(events, hasLength(1));
      expect(events.single.id, '42');
      expect(events.single.event, 'approval.updated');
      expect(events.single.data['id'], 'a1');
    });

    test('does NOT dispatch on every data: line — only on the blank line', () {
      // Trước Task 8, parser cũ dispatch ngay khi thấy một dòng `data:` (và
      // thử jsonDecode dòng đó riêng lẻ) — với payload nhiều dòng, dòng đầu
      // tiên `{"id":` không phải JSON hợp lệ một mình nên sẽ sinh ra một
      // envelope rác kiểu {'raw': '{"id":'} trước cả khi gặp dòng trống.
      // Parser đúng chỉ được sinh ra ĐÚNG MỘT envelope cho cả frame.
      final events = parseSse(
        'event: approval.updated\ndata: {"id":\ndata: "a1"}\n\n',
      );
      expect(events, hasLength(1));
    });

    test('multiple frames in one raw block each dispatch once', () {
      final events = parseSse(
        'id: 1\nevent: a\ndata: {"x":1}\n\n'
        'id: 2\nevent: b\ndata: {"x":2}\n\n',
      );
      expect(events, hasLength(2));
      expect(events[0].id, '1');
      expect(events[0].event, 'a');
      expect(events[0].data['x'], 1);
      expect(events[1].id, '2');
      expect(events[1].event, 'b');
      expect(events[1].data['x'], 2);
    });
  });

  group('RealtimeService — workspace-scoped reconnect', () {
    late http.Client originalClient;
    late _RecordingSseClient client;
    late RealtimeService service;

    setUp(() {
      originalClient = ApiClient.client;
      client = _RecordingSseClient();
      ApiClient.client = client;
      service = RealtimeService();
      service.resetForTest();
    });

    tearDown(() {
      service.stop(clearCheckpoint: true);
      client.closeAll();
      ApiClient.client = originalClient;
    });

    test('reconnect sends the last event id only for the same workspace', () async {
      await service.connectForWorkspace('a');
      service.acceptForTest(_envelope(id: '42'));
      await service.reconnectForTest();
      expect(client.lastEventId, '42');

      await service.connectForWorkspace('b');
      expect(client.lastEventId, isNull);
    });

    test('first connect for a workspace never sends a stale checkpoint', () async {
      await service.connectForWorkspace('workspace-x');
      expect(client.lastEventId, isNull);
    });
  });

  group('RealtimeService — auth failure lifecycle', () {
    late http.Client originalClient;
    late RealtimeService service;

    setUp(() {
      originalClient = ApiClient.client;
      service = RealtimeService();
      service.resetForTest();
    });

    tearDown(() {
      service.stop(clearCheckpoint: true);
      ApiClient.client = originalClient;
    });

    test('401 stops reconnect attempts and notifies the auth-failure hook', () async {
      ApiClient.client = MockClient((request) async => http.Response('', 401));

      var authFailureCalls = 0;
      service.setAuthFailureHandler(() => authFailureCalls++);

      await service.connectForWorkspace('a');

      expect(authFailureCalls, 1);
      expect(service.isConnected, isFalse);

      // Không được tự lên lịch reconnect sau 401 — chờ một khoảng rồi kiểm
      // tra handler không bị gọi thêm lần nào (nếu có timer treo, test sẽ
      // fail vì "pending timer" khi kết thúc thay vì assertion này).
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(authFailureCalls, 1);
    });
  });
}
