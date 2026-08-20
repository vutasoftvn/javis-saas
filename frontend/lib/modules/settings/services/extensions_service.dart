import 'dart:convert';
import 'package:http/http.dart' as http;

class ExtensionsService {
  final String baseUrl;
  final String workspaceId;

  ExtensionsService({required this.baseUrl, required this.workspaceId});

  Future<List<dynamic>> getExtensions() async {
    final response = await http.get(Uri.parse('$baseUrl/api/v1/workspaces/$workspaceId/extensions'));
    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return json['extensions'] as List<dynamic>;
    } else {
      throw Exception('Failed to load extensions');
    }
  }

  Future<void> updateExtensionStatus(String extensionId, String status) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/workspaces/$workspaceId/extensions/$extensionId/status'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'status': status}),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to update extension status');
    }
  }
}
