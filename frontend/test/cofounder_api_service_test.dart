import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/cofounder_api_service.dart';

/// G2 P0.8 / G3 §10.4: chatWithCoFounder used to collapse every failure to
/// `null`, which the caller then displayed as a fabricated "I've noted this
/// and I'm coordinating..." message. It must now throw
/// CoFounderChatException so the caller can render a real error.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});

  late http.Client originalClient;
  setUp(() {
    originalClient = ApiClient.client;
  });
  tearDown(() {
    ApiClient.client = originalClient;
  });

  test('chatWithCoFounder returns the decoded body on HTTP 200', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"intent": "GREETING", "message": "Hello there"}', 200);
    });

    final result = await CoFounderApiService.chatWithCoFounder(message: 'hello');

    expect(result['message'], 'Hello there');
  });

  test('chatWithCoFounder throws CoFounderChatException on a non-200 status', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"detail": "internal error"}', 500);
    });

    expect(
      () => CoFounderApiService.chatWithCoFounder(message: 'tìm 20 khách hàng'),
      throwsA(isA<CoFounderChatException>()),
    );
  });

  test('chatWithCoFounder throws CoFounderChatException on a network failure', () async {
    ApiClient.client = MockClient((request) async {
      throw const SocketExceptionStub();
    });

    expect(
      () => CoFounderApiService.chatWithCoFounder(message: 'chào'),
      throwsA(isA<CoFounderChatException>()),
    );
  });

  test('chatWithCoFounder throws CoFounderChatException on malformed JSON', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('not json', 200);
    });

    expect(
      () => CoFounderApiService.chatWithCoFounder(message: 'chào'),
      throwsA(isA<CoFounderChatException>()),
    );
  });
}

/// Minimal stand-in for a network-layer exception (avoids pulling in
/// dart:io's SocketException, which isn't available on web test targets).
class SocketExceptionStub implements Exception {
  const SocketExceptionStub();
  @override
  String toString() => 'SocketExceptionStub: connection failed';
}
