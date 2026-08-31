import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';

void main() {
  group('ApiResult and ApiResponseMeta', () {
    test('parses populated ApiResponseMeta correctly', () {
      final json = {
        'data_state': 'populated',
        'observed_at': '2026-08-31T12:00:00.000Z',
        'sources': [
          {
            'kind': 'company_db',
            'ref': 'strategy.canvases',
            'observed_at': '2026-08-31T12:00:00.000Z',
          }
        ],
      };

      final meta = ApiResponseMeta.fromJson(json);
      expect(meta.dataState, ApiDataState.populated);
      expect(meta.sources.length, 1);
      expect(meta.sources.first.kind, 'company_db');
      expect(meta.sources.first.ref, 'strategy.canvases');
    });

    test('parses empty ApiResponseMeta correctly', () {
      final json = {
        'data_state': 'empty',
        'observed_at': '2026-08-31T12:00:00.000Z',
        'sources': [],
      };

      final meta = ApiResponseMeta.fromJson(json);
      expect(meta.dataState, ApiDataState.empty);
      expect(meta.sources, isEmpty);
    });

    test('throws FormatException on invalid data_state', () {
      final json = {
        'data_state': 'unavailable',
        'observed_at': '2026-08-31T12:00:00.000Z',
      };

      expect(() => ApiResponseMeta.fromJson(json), throwsFormatException);
    });

    test('ApiResult.when correctly dispatches success and failure', () {
      final success = ApiSuccess<String>(
        data: 'hello',
        meta: ApiResponseMeta(
          dataState: ApiDataState.populated,
          observedAt: DateTime.now(),
        ),
      );

      final dispatched = success.when(
        success: (data, meta) => 'ok: $data',
        failure: (f) => 'fail: ${f.code}',
      );
      expect(dispatched, 'ok: hello');

      const failure = ApiFailure<String>(
        ApiFailureDetail(
          code: ApiFailureCode.forbidden,
          message: 'Access denied',
        ),
      );

      final failDispatched = failure.when(
        success: (data, meta) => 'ok: $data',
        failure: (f) => 'fail: ${f.code.name}',
      );
      expect(failDispatched, 'fail: forbidden');
    });
  });
}
