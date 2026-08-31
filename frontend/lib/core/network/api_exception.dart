/// Standard hierarchy of API exceptions used across all frontend services.
///
/// Eliminates ad-hoc exception throwing and provides strongly-typed
/// error classification for UI error handling.
abstract class ApiException implements Exception {
  const ApiException(this.message, [this.statusCode]);

  final String message;
  final int? statusCode;

  /// Factory constructor to map HTTP status code to appropriate [ApiException] subclass.
  factory ApiException.fromStatusCode(int statusCode, String message) {
    switch (statusCode) {
      case 400:
        return BadRequestException(message, statusCode);
      case 401:
        return UnauthorizedException(message, statusCode);
      case 403:
        return ForbiddenException(message, statusCode);
      case 404:
        return NotFoundException(message, statusCode);
      case 409:
        return ConflictException(message, statusCode);
      case 500:
      case 502:
      case 503:
      case 504:
        return ServerException(message, statusCode);
      default:
        return UnknownApiException(message, statusCode);
    }
  }

  @override
  String toString() {
    final codeStr = statusCode != null ? '($statusCode)' : '';
    return '$runtimeType$codeStr: $message';
  }
}

/// 400 Bad Request
class BadRequestException extends ApiException {
  const BadRequestException([
    String message = 'Bad request',
    int? statusCode = 400,
  ]) : super(message, statusCode);
}

/// 401 Unauthorized
class UnauthorizedException extends ApiException {
  const UnauthorizedException([
    String message = 'Unauthorized',
    int? statusCode = 401,
  ]) : super(message, statusCode);
}

/// 403 Forbidden
class ForbiddenException extends ApiException {
  const ForbiddenException([
    String message = 'Forbidden',
    int? statusCode = 403,
  ]) : super(message, statusCode);
}

/// 404 Not Found
class NotFoundException extends ApiException {
  const NotFoundException([
    String message = 'Resource not found',
    int? statusCode = 404,
  ]) : super(message, statusCode);
}

/// 409 Conflict
class ConflictException extends ApiException {
  const ConflictException([
    String message = 'Conflict state',
    int? statusCode = 409,
  ]) : super(message, statusCode);
}

/// 5xx Server Error
class ServerException extends ApiException {
  const ServerException([
    String message = 'Internal server error',
    int? statusCode = 500,
  ]) : super(message, statusCode);
}

/// Network connectivity failure (no connection, timeout, etc.)
class NetworkConnectionException extends ApiException {
  const NetworkConnectionException([
    String message = 'Network connection failed. Please check your internet.',
  ]) : super(message, null);
}

/// Parsing / JSON deserialization failure
class MalformedResponseException extends ApiException {
  const MalformedResponseException([
    String message = 'Malformed response payload from server.',
  ]) : super(message, null);
}

/// Generic / unclassified exception
class UnknownApiException extends ApiException {
  const UnknownApiException([
    String message = 'An unknown API error occurred.',
    int? statusCode,
  ]) : super(message, statusCode);
}
