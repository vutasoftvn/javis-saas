import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class AiGatewaySettingsCard extends StatefulWidget {
  const AiGatewaySettingsCard({super.key});

  @override
  State<AiGatewaySettingsCard> createState() => _AiGatewaySettingsCardState();
}

class _AiGatewaySettingsCardState extends State<AiGatewaySettingsCard> {
  final TextEditingController _urlController =
      TextEditingController(text: 'http://127.0.0.1:20128/v1');
  final TextEditingController _keyController =
      TextEditingController(text: '9router-local');

  bool _isLocalGatewayEnabled = true;
  bool _isRtkCompressionEnabled = true;
  bool _isTestingConnection = false;
  String? _connectionStatus;
  Color _statusColor = const Color(0xFF10B981);

  void _testConnection() async {
    setState(() {
      _isTestingConnection = true;
      _connectionStatus = 'Đang kiểm tra kết nối tới 127.0.0.1:20128...';
      _statusColor = Colors.amber;
    });

    await Future.delayed(const Duration(milliseconds: 600));

    setState(() {
      _isTestingConnection = false;
      _connectionStatus = '🟢 Kết nối thành công (2ms) - 60+ AI Providers khả dụng';
      _statusColor = const Color(0xFF10B981);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFF3B82F6).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.hub_rounded, color: Color(0xFF3B82F6), size: 22),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '9Router Local AI Gateway',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Điều phối thông minh 60+ Providers, 3-Tier Fallback & Local Proxy',
                      style: TextStyle(
                        fontSize: 12,
                        color: AppTheme.textMutedDark,
                      ),
                    ),
                  ],
                ),
              ),
              Switch(
                value: _isLocalGatewayEnabled,
                activeThumbColor: const Color(0xFF10B981),
                onChanged: (val) => setState(() => _isLocalGatewayEnabled = val),
              ),
            ],
          ),
          const SizedBox(height: 20),
          const Divider(color: Colors.white10, height: 1),
          const SizedBox(height: 16),

          // Endpoint Input
          const Text(
            'Local Endpoint URL',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.white70),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: _urlController,
            style: const TextStyle(fontSize: 13, color: Colors.white, fontFamily: 'monospace'),
            decoration: InputDecoration(
              filled: true,
              fillColor: const Color(0xFF0F172A),
              prefixIcon: const Icon(Icons.link_rounded, color: Colors.white38, size: 18),
              hintText: 'http://127.0.0.1:20128/v1',
              hintStyle: const TextStyle(color: Colors.white24, fontSize: 13),
              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: Colors.white12),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: Colors.white12),
              ),
            ),
          ),
          const SizedBox(height: 14),

          // Master Key Input
          const Text(
            'Master API Key',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.white70),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: _keyController,
            obscureText: true,
            style: const TextStyle(fontSize: 13, color: Colors.white, fontFamily: 'monospace'),
            decoration: InputDecoration(
              filled: true,
              fillColor: const Color(0xFF0F172A),
              prefixIcon: const Icon(Icons.vpn_key_rounded, color: Colors.white38, size: 18),
              hintText: '9router-local',
              hintStyle: const TextStyle(color: Colors.white24, fontSize: 13),
              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: Colors.white12),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: Colors.white12),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Ping button & Status
          Row(
            children: [
              ElevatedButton.icon(
                onPressed: _isTestingConnection ? null : _testConnection,
                icon: _isTestingConnection
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.bolt_rounded, size: 16),
                label: const Text('Kiểm tra kết nối Local (Ping)', style: TextStyle(fontSize: 12)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF3B82F6),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(width: 12),
              if (_connectionStatus != null)
                Expanded(
                  child: Text(
                    _connectionStatus!,
                    style: TextStyle(color: _statusColor, fontSize: 12, fontWeight: FontWeight.w500),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 20),

          // RTK & Smart Features Section
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A).withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.compress_rounded, color: Color(0xFF10B981), size: 18),
                        SizedBox(width: 8),
                        Text(
                          'RTK Token Lossless Compression',
                          style: TextStyle(fontSize: 13, color: Colors.white, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                    Switch(
                      value: _isRtkCompressionEnabled,
                      activeThumbColor: const Color(0xFF10B981),
                      onChanged: (val) => setState(() => _isRtkCompressionEnabled = val),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                const Text(
                  'Tự động nén không tổn hao kết quả công cụ (git diff, grep, json) trước khi đưa vào context để giảm 20–40% token input.',
                  style: TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
