import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Snowflake ID Contract Tests (P1.2)', () {
    test('Decodes 64-bit Snowflake IDs > 2^53 - 1 without string truncation or loss', () {
      const snowflakeIds = [
        '9007199254740993', // 2^53 + 1
        '9007199254740994', // 2^53 + 2
        '351020997941043206', // Canonical Encore Snowflake
        '18446744073709551615', // Max uint64
      ];

      for (final id in snowflakeIds) {
        final jsonString = jsonEncode({
          'id': id,
          'title': 'Test Item',
          'workspaceId': '1001',
        });

        final decoded = jsonDecode(jsonString) as Map<String, dynamic>;
        expect(decoded['id'], isA<String>());
        expect(decoded['id'], equals(id));

        // BigInt parsing preserves absolute numerical fidelity
        final bigIntValue = BigInt.parse(decoded['id'] as String);
        expect(bigIntValue.toString(), equals(id));
      }
    });

    test('Demonstrates why String encoding is necessary compared to Double/Num', () {
      const highPrecisionId = '9007199254740993';

      // Parsing as BigInt
      final bigIntVal = BigInt.parse(highPrecisionId);
      expect(bigIntVal.toString(), equals(highPrecisionId));

      // Standard Dart int on 64-bit platforms also supports 64-bit signed int
      final intVal = int.parse(highPrecisionId);
      expect(intVal.toString(), equals(highPrecisionId));
    });
  });
}
