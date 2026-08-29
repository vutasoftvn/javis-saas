import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../core/network/api_client.dart';

class EntitlementProvider extends ChangeNotifier {
  Map<String, dynamic> _features = {};
  Map<String, dynamic> _limits = {};
  bool _isLoading = false;
  String? _loadedWorkspaceId;

  Map<String, dynamic> get features => _features;
  Map<String, dynamic> get limits => _limits;
  bool get isLoading => _isLoading;
  String? get loadedWorkspaceId => _loadedWorkspaceId;

  /// Fail-closed: returns false if not loaded, error, or not present
  bool hasFeature(String key) {
    return _features[key] == true;
  }

  dynamic getLimit(String key) {
    return _limits[key];
  }

  Future<void> load(String platformWorkspaceId) async {
    _isLoading = true;
    notifyListeners();

    try {
      final res = await ApiClient.get('/platform/workspaces/$platformWorkspaceId/entitlement');
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        if (data is Map<String, dynamic>) {
          _features = data['features'] is Map ? Map<String, dynamic>.from(data['features'] as Map) : {};
          _limits = data['limits'] is Map ? Map<String, dynamic>.from(data['limits'] as Map) : {};
          _loadedWorkspaceId = platformWorkspaceId;
        }
      } else {
        _features = {};
        _limits = {};
      }
    } catch (_) {
      _features = {};
      _limits = {};
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void setEntitlementForTesting({
    required Map<String, dynamic> features,
    Map<String, dynamic>? limits,
  }) {
    _features = features;
    _limits = limits ?? {};
    notifyListeners();
  }

  void reset() {
    _features = {};
    _limits = {};
    _loadedWorkspaceId = null;
    _isLoading = false;
    notifyListeners();
  }
}
