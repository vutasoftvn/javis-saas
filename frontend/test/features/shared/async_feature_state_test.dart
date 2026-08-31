import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/_shared/public.dart';

void main() {
  group('AsyncFeatureState Tests', () {
    test('FeatureData holds parsed value and truthful metadata', () {
      final meta = ApiResponseMeta(
        dataState: ApiDataState.populated,
        observedAt: DateTime.parse('2026-08-31T12:00:00.000Z'),
        sources: [const ApiSourceRef(kind: 'company_db', ref: 'strategy.canvases')],
      );

      final state = FeatureData<List<String>>(['item_1', 'item_2'], meta);
      expect(state.value, hasLength(2));
      expect(state.meta.dataState, ApiDataState.populated);
      expect(state.meta.sources.first.kind, 'company_db');
    });

    test('FeatureFailure preserves failure detail explicitly', () {
      const failure = ApiFailureDetail(
        code: ApiFailureCode.forbidden,
        message: 'Access denied to workspace',
      );

      const state = FeatureFailure<String>(failure);
      expect(state.failure.code, ApiFailureCode.forbidden);
      expect(state.failure.message, 'Access denied to workspace');
    });

    test('FeatureNotObserved retains reason and sourceKind without invented date', () {
      const state = FeatureNotObserved<int>('No heartbeat recorded', 'agent_db');
      expect(state.reason, 'No heartbeat recorded');
      expect(state.sourceKind, 'agent_db');
    });
  });
}
