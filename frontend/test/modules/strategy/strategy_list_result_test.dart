import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/strategy/models/strategy_list_result.dart';

void main() {
  group('StrategyListResult', () {
    test('success carries the decoded items and no error/unavailable flag', () {
      const result = StrategyListResult<Map<String, dynamic>>.success([
        {'id': '1'},
      ]);

      expect(result.items, hasLength(1));
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNull);
      expect(result.isFailure, isFalse);
    });

    test('unavailable carries no items and no error message', () {
      const result = StrategyListResult<Map<String, dynamic>>.unavailable();

      expect(result.items, isEmpty);
      expect(result.isUnavailable, isTrue);
      expect(result.errorMessage, isNull);
      expect(result.isFailure, isFalse);
    });

    test('failure carries no items but an actionable error message', () {
      const result = StrategyListResult<Map<String, dynamic>>.failure('Yêu cầu thất bại (500)');

      expect(result.items, isEmpty);
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, 'Yêu cầu thất bại (500)');
      expect(result.isFailure, isTrue);
    });
  });
}
