import 'dart:io';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Legacy Route and Fallback Guard', () {
    const prohibitedPatterns = [
      "stringWorkspaceId() ?? '1'",
      "projectId?.toString() ?? '1'",
      "int.tryParse(weeklyCommitmentId) ?? 0",
      "if (response.statusCode == 404) return []",
      "final fallbackResp = await ApiClient.get(",
    ];

    // MVP client services to be audited for legacy fallback expressions
    final auditedFiles = [
      'lib/core/network/mvp_request_client.dart',
      'lib/core/network/api_result.dart',
      'lib/core/network/mvp_endpoints.g.dart',
    ];

    for (final relativePath in auditedFiles) {
      test('no prohibited fallback patterns in $relativePath', () {
        final file = File(relativePath);
        if (!file.existsSync()) return;

        final content = file.readAsStringSync();
        for (final pattern in prohibitedPatterns) {
          expect(
            content.contains(pattern),
            isFalse,
            reason: 'Found prohibited fallback expression: "$pattern" in $relativePath',
          );
        }
      });
    }
  });
}
