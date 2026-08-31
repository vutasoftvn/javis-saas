import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_exception.dart';
import 'package:frontend/core/network/api_response_decoder.dart';

class SampleItem {
  final String id;
  final String title;

  SampleItem({required this.id, required this.title});

  factory SampleItem.fromJson(Map<String, dynamic> json) => SampleItem(
        id: json['id'] as String,
        title: json['title'] as String,
      );
}

void main() {
  group('ApiResponseDecoder', () {
    test('decodeItem successfully decodes a JSON map', () {
      final json = {'id': '123', 'title': 'Test'};
      final item = ApiResponseDecoder.decodeItem(json, SampleItem.fromJson);
      expect(item.id, '123');
      expect(item.title, 'Test');
    });

    test('decodeItem unwraps "data" envelope if present', () {
      final json = {
        'data': {'id': '456', 'title': 'Enveloped'}
      };
      final item = ApiResponseDecoder.decodeItem(json, SampleItem.fromJson);
      expect(item.id, '456');
      expect(item.title, 'Enveloped');
    });

    test('decodeItem throws MalformedResponseException when json is invalid', () {
      expect(
        () => ApiResponseDecoder.decodeItem('not-a-map', SampleItem.fromJson),
        throwsA(isA<MalformedResponseException>()),
      );
    });

    test('decodeList successfully decodes a JSON list', () {
      final json = [
        {'id': '1', 'title': 'First'},
        {'id': '2', 'title': 'Second'}
      ];
      final items = ApiResponseDecoder.decodeList(json, SampleItem.fromJson);
      expect(items.length, 2);
      expect(items[0].id, '1');
      expect(items[1].title, 'Second');
    });

    test('decodeList unwraps "data" or "items" envelope if present', () {
      final json = {
        'data': [
          {'id': '10', 'title': 'Enveloped Item'}
        ]
      };
      final items = ApiResponseDecoder.decodeList(json, SampleItem.fromJson);
      expect(items.length, 1);
      expect(items.first.id, '10');
    });

    test('decodeList returns empty list when json is null and fallbackToEmpty is true', () {
      final items = ApiResponseDecoder.decodeList(null, SampleItem.fromJson, fallbackToEmpty: true);
      expect(items, isEmpty);
    });

    test('decodeList throws MalformedResponseException when json is invalid and fallbackToEmpty is false', () {
      expect(
        () => ApiResponseDecoder.decodeList('not-a-list', SampleItem.fromJson, fallbackToEmpty: false),
        throwsA(isA<MalformedResponseException>()),
      );
    });
  });
}
