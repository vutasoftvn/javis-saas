import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../core/network/api_client.dart';

class AgentPlatformService {
  /// Lấy danh sách Agents trong Platform
  Future<List<Map<String, dynamic>>> getAgents() async {
    try {
      final res = await ApiClient.get('/agent-platform/agents');
      if (res.statusCode == 200) {
        final List<dynamic> data = jsonDecode(res.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('AgentPlatformService.getAgents error: $e');
    }
    return [];
  }

  /// Lấy danh sách Tools (Local, MCP, A2A, n8n, Sandbox)
  Future<List<Map<String, dynamic>>> getTools({String? transport}) async {
    try {
      final query = transport != null ? '?transport=$transport' : '';
      final res = await ApiClient.get('/agent-platform/tools$query');
      if (res.statusCode == 200) {
        final List<dynamic> data = jsonDecode(res.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('AgentPlatformService.getTools error: $e');
    }
    return [];
  }

  /// Lấy ma trận phân quyền Agent <-> Tool
  Future<List<Map<String, dynamic>>> getPermissions({int? agentId}) async {
    try {
      final query = agentId != null ? '?agent_id=$agentId' : '';
      final res = await ApiClient.get('/agent-platform/permissions$query');
      if (res.statusCode == 200) {
        final List<dynamic> data = jsonDecode(res.body);
        return data.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('AgentPlatformService.getPermissions error: $e');
    }
    return [];
  }

  /// Cập nhật quyền hạn Agent đối với Tool
  Future<Map<String, dynamic>?> setPermission({
    required int agentId,
    required int toolId,
    required bool allowExecute,
    required bool requiresApproval,
  }) async {
    try {
      final res = await ApiClient.post(
        '/agent-platform/permissions',
        body: {
          'agent_id': agentId,
          'tool_id': toolId,
          'allow_execute': allowExecute,
          'requires_approval': requiresApproval,
        },
      );
      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('AgentPlatformService.setPermission error: $e');
    }
    return null;
  }

  /// Lấy nội dung Prompt và phiên bản
  Future<Map<String, dynamic>?> getPrompt(String key) async {
    try {
      final res = await ApiClient.get('/agent-platform/prompts/$key');
      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('AgentPlatformService.getPrompt error: $e');
    }
    return null;
  }

  /// Cập nhật Prompt và tạo version mới
  Future<Map<String, dynamic>?> updatePrompt({
    required String key,
    required String newContent,
    String? changeNote,
  }) async {
    try {
      final res = await ApiClient.put(
        '/agent-platform/prompts/$key',
        body: {
          'new_content': newContent,
          'change_note': changeNote,
        },
      );
      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('AgentPlatformService.updatePrompt error: $e');
    }
    return null;
  }

  /// Khôi phục Prompt về bản mặc định gốc từ Factory Manifests
  Future<Map<String, dynamic>?> restoreDefaultPrompt(String key) async {
    try {
      final res = await ApiClient.post('/agent-platform/prompts/$key/restore-default');
      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('AgentPlatformService.restoreDefaultPrompt error: $e');
    }
    return null;
  }

  /// Kiểm thử phân loại Intent Router
  Future<Map<String, dynamic>?> testRouting(String message) async {
    try {
      final res = await ApiClient.post(
        '/agent-platform/routing/test',
        body: {'message': message},
      );
      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('AgentPlatformService.testRouting error: $e');
    }
    return null;
  }
}
