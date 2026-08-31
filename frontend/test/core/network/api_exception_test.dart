import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_exception.dart';

void main() {
  group('ApiException Hierarchy', () {
    test('ApiException.fromStatusCode maps 400 to BadRequestException', () {
      final exc = ApiException.fromStatusCode(400, 'Invalid parameter');
      expect(exc, isA<BadRequestException>());
      expect(exc.statusCode, 400);
      expect(exc.message, 'Invalid parameter');
    });

    test('ApiException.fromStatusCode maps 401 to UnauthorizedException', () {
      final exc = ApiException.fromStatusCode(401, 'Token expired');
      expect(exc, isA<UnauthorizedException>());
      expect(exc.statusCode, 401);
      expect(exc.message, 'Token expired');
    });

    test('ApiException.fromStatusCode maps 403 to ForbiddenException', () {
      final exc = ApiException.fromStatusCode(403, 'Permission denied');
      expect(exc, isA<ForbiddenException>());
      expect(exc.statusCode, 403);
      expect(exc.message, 'Permission denied');
    });

    test('ApiException.fromStatusCode maps 404 to NotFoundException', () {
      final exc = ApiException.fromStatusCode(404, 'Resource not found');
      expect(exc, isA<NotFoundException>());
      expect(exc.statusCode, 404);
      expect(exc.message, 'Resource not found');
    });

    test('ApiException.fromStatusCode maps 409 to ConflictException', () {
      final exc = ApiException.fromStatusCode(409, 'Conflict state');
      expect(exc, isA<ConflictException>());
      expect(exc.statusCode, 409);
      expect(exc.message, 'Conflict state');
    });

    test('ApiException.fromStatusCode maps 500 to ServerException', () {
      final exc = ApiException.fromStatusCode(500, 'Internal server error');
      expect(exc, isA<ServerException>());
      expect(exc.statusCode, 500);
      expect(exc.message, 'Internal server error');
    });

    test('NetworkConnectionException has correct default message and null statusCode', () {
      final exc = const NetworkConnectionException();
      expect(exc.statusCode, isNull);
      expect(exc.message, contains('Network connection'));
    });

    test('ApiException.toString formats message and statusCode cleanly', () {
      final exc = ApiException.fromStatusCode(404, 'User not found');
      expect(exc.toString(), contains('NotFoundException(404): User not found'));
    });
  });
}
