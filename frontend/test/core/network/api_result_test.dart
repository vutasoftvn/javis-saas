import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';

void main() {
  group('ApiResponseMeta strict parsing', () {
    test('parses populated data state with valid ISO timestamp and sources', () {
      final json = {
        'data_state': 'populated',
        'observed_at': '2026-08-31T12:00:00.000Z',
        'sources': [
          {
            'kind': 'company_db',
            'ref': 'strategy.initiatives',
            'observed_at': '2026-08-31T12:00:00.000Z',
          }
        ]
      };

      final meta = ApiResponseMeta.fromJson(json);
      expect(meta.dataState, equals(ApiDataState.populated));
      expect(meta.observedAt, equals(DateTime.parse('2026-08-31T12:00:00.000Z')));
      expect(meta.sources.length, equals(1));
      expect(meta.sources.first.kind, equals('company_db'));
      expect(meta.sources.first.ref, equals('strategy.initiatives'));
      expect(meta.sources.first.observedAt, equals(DateTime.parse('2026-08-31T12:00:00.000Z')));
    });

    test('parses empty data state without fallback', () {
      final json = {
        'data_state': 'empty',
        'observed_at': '2026-08-31T12:30:00.000Z',
        'sources': <Map<String, dynamic>>[],
      };

      final meta = ApiResponseMeta.fromJson(json);
      expect(meta.dataState, equals(ApiDataState.empty));
      expect(meta.sources, isEmpty);
    });

    test('throws FormatException on missing or invalid observed_at', () {
      final jsonMissing = {
        'data_state': 'populated',
        'sources': <Map<String, dynamic>>[],
      };
      expect(() => ApiResponseMeta.fromJson(jsonMissing), throwsA(isA<FormatException>()));

      final jsonInvalid = {
        'data_state': 'populated',
        'observed_at': 'not-a-timestamp',
        'sources': <Map<String, dynamic>>[],
      };
      expect(() => ApiResponseMeta.fromJson(jsonInvalid), throwsA(isA<FormatException>()));
    });

    test('throws FormatException on invalid data_state', () {
      final json = {
        'data_state': 'unexpected_state',
        'observed_at': '2026-08-31T12:00:00.000Z',
      };
      expect(() => ApiResponseMeta.fromJson(json), throwsA(isA<FormatException>()));
    });

    test('throws FormatException on invalid source ref', () {
      final jsonMissingKind = {
        'data_state': 'populated',
        'observed_at': '2026-08-31T12:00:00.000Z',
        'sources': [
          {'ref': 'agent.runs'}
        ]
      };
      expect(() => ApiResponseMeta.fromJson(jsonMissingKind), throwsA(isA<FormatException>()));

      final jsonInvalidSourceItem = {
        'data_state': 'populated',
        'observed_at': '2026-08-31T12:00:00.000Z',
        'sources': ['string_instead_of_map']
      };
      expect(() => ApiResponseMeta.fromJson(jsonInvalidSourceItem), throwsA(isA<FormatException>()));
    });
  });

  group('ApiResult type matching and pattern matching', () {
    test('ApiSuccess provides typed data, meta, and value accessors', () {
      const meta = ApiResponseMeta(
        dataState: ApiDataState.populated,
        observedAt: _StaticDateTime(),
      );
      const result = ApiSuccess<String>(data: 'test_payload', meta: meta);

      expect(result.isSuccess, isTrue);
      expect(result.isFailure, isFalse);
      expect(result.dataOrNull, equals('test_payload'));
      expect(result.value, equals('test_payload'));
      expect(result.failureOrNull, isNull);

      final mapped = result.when(
        success: (data, meta) => 'ok: $data',
        failure: (f) => 'err: ${f.message}',
      );
      expect(mapped, equals('ok: test_payload'));
    });

    test('ApiFailure provides failure details and pattern matching', () {
      const detail = ApiFailureDetail(
        code: ApiFailureCode.notFound,
        statusCode: 404,
        message: 'Resource not found',
        endpointId: 'ep_test',
      );
      const result = ApiFailure<String>(detail);

      expect(result.isSuccess, isFalse);
      expect(result.isFailure, isTrue);
      expect(result.dataOrNull, isNull);
      expect(result.failureOrNull, equals(detail));

      final mapped = result.when(
        success: (data, meta) => 'ok: $data',
        failure: (f) => 'err: ${f.code.name}',
      );
      expect(mapped, equals('err: notFound'));
    });
  });
}

class _StaticDateTime implements DateTime {
  const _StaticDateTime();

  @override
  bool isAfter(DateTime other) => false;
  @override
  bool isBefore(DateTime other) => false;
  @override
  bool isAtSameMomentAs(DateTime other) => true;
  @override
  int compareTo(DateTime other) => 0;
  @override
  String toIso8601String() => '2026-08-31T12:00:00.000Z';
  @override
  String toString() => '2026-08-31 12:00:00.000Z';
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
