import 'api_exception.dart';

/// Helper utility for safe, consistent JSON decoding of API responses.
///
/// Handles unwrapping of standard response envelopes (`data`, `items`)
/// and maps parsing errors to typed [MalformedResponseException].
class ApiResponseDecoder {
  ApiResponseDecoder._();

  /// Decode a single item of type [T] from dynamic JSON payload.
  ///
  /// Automatically unwraps `{ "data": ... }` envelope if present.
  static T decodeItem<T>(
    dynamic json,
    T Function(Map<String, dynamic>) fromJson,
  ) {
    if (json == null) {
      throw const MalformedResponseException('Response body is null');
    }

    dynamic target = json;
    if (target is Map<String, dynamic> && target.containsKey('data') && target['data'] is Map<String, dynamic>) {
      target = target['data'];
    }

    if (target is! Map<String, dynamic>) {
      throw MalformedResponseException(
        'Expected Map<String, dynamic> but received ${target.runtimeType}',
      );
    }

    try {
      return fromJson(target);
    } catch (e) {
      throw MalformedResponseException(
        'Failed to decode ${T.toString()}: $e',
      );
    }
  }

  /// Decode a list of items of type [T] from dynamic JSON payload.
  ///
  /// Automatically unwraps `{ "data": [...] }` or `{ "items": [...] }` envelopes if present.
  /// If [fallbackToEmpty] is true and [json] is null or not a valid list, returns `[]`.
  static List<T> decodeList<T>(
    dynamic json,
    T Function(Map<String, dynamic>) fromJson, {
    bool fallbackToEmpty = true,
  }) {
    if (json == null) {
      if (fallbackToEmpty) return <T>[];
      throw const MalformedResponseException('Response body is null');
    }

    dynamic listSource = json;
    if (listSource is Map<String, dynamic>) {
      if (listSource['data'] is List) {
        listSource = listSource['data'];
      } else if (listSource['items'] is List) {
        listSource = listSource['items'];
      }
    }

    if (listSource is! List) {
      if (fallbackToEmpty) return <T>[];
      throw MalformedResponseException(
        'Expected List but received ${listSource.runtimeType}',
      );
    }

    try {
      return listSource
          .whereType<Map<String, dynamic>>()
          .map((item) => fromJson(item))
          .toList();
    } catch (e) {
      throw MalformedResponseException(
        'Failed to decode list of ${T.toString()}: $e',
      );
    }
  }
}
