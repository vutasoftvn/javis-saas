import 'dart:convert';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/models/workspace_file_model.dart';

class WorkspaceService {
  static Future<List<WorkspaceFileModel>> listFiles({String companyId = '1'}) async {
    try {
      final res = await ApiClient.get('/workspace/files?company_id=$companyId');
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        final files = data['files'] as List? ?? [];
        return files.map((e) => WorkspaceFileModel.fromJson(e)).toList();
      }
    } catch (_) {}
    return [];
  }

  static Future<String?> readFile(String relativePath, {String companyId = '1'}) async {
    try {
      final encoded = Uri.encodeComponent(relativePath);
      final res = await ApiClient.get('/workspace/file?relative_path=$encoded&company_id=$companyId');
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        return data['content'] as String?;
      }
    } catch (_) {}
    return null;
  }

  static Future<bool> writeFile(String relativePath, String content, {String companyId = '1'}) async {
    try {
      final res = await ApiClient.post(
        '/workspace/file',
        body: {
          'relative_path': relativePath,
          'content': content,
          'company_id': companyId,
        },
      );
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  static Future<String?> resetToDefault(String relativePath, {String companyId = '1'}) async {
    try {
      final res = await ApiClient.post(
        '/workspace/reset-default',
        body: {
          'relative_path': relativePath,
          'company_id': companyId,
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
