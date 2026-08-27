import 'dart:convert';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/models/workspace_file_model.dart';

class WorkspaceService {
  static Future<List<WorkspaceFileModel>> listFiles() async {
    try {
      final res = await ApiClient.get('/workspace/files');
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        final files = data['files'] as List? ?? [];
        return files.map((e) => WorkspaceFileModel.fromJson(e)).toList();
      }
    } catch (_) {}
    return [];
  }

  static Future<String?> readFile(String relativePath) async {
    try {
      final encoded = Uri.encodeComponent(relativePath);
      final res = await ApiClient.get('/workspace/file?relative_path=$encoded');
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        return data['content'] as String?;
      }
    } catch (_) {}
    return null;
  }

  static Future<bool> writeFile(String relativePath, String content) async {
    try {
      final res = await ApiClient.post(
        '/workspace/file',
        body: {
          'relative_path': relativePath,
          'content': content,
        },
      );
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  static Future<String?> resetToDefault(String relativePath) async {
    try {
      final res = await ApiClient.post(
        '/workspace/reset-default',
        body: {
          'relative_path': relativePath,
        },
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        return data['content'] as String?;
      }
    } catch (_) {}
    return null;
  }
}
