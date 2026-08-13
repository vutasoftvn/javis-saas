import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/finance_service.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class _Client extends http.BaseClient {
  String? requestedUri;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    requestedUri = request.url.toString();
    return http.StreamedResponse(
      Stream.value(utf8.encode('{"templates":[{"code":"S1-DNSN"}]}')),
      200,
    );
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
  });

  test('getBooks calls the finance books templates endpoint', () async {
    final client = _Client();
    ApiClient.client = client;

    final books = await FinanceService().getBooks();

    expect(books, [{'code': 'S1-DNSN'}]);
    expect(client.requestedUri, contains('/finance/books/templates?workspace_id=workspace-1'));
  });
}
