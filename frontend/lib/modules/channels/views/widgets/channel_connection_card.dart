import 'package:flutter/material.dart';

class ChannelConnectionCard extends StatefulWidget {
  final String title;
  final String channelKey;
  final IconData icon;
  final Color primaryColor;
  final String description;
  final bool isConnected;
  final Future<Map<String, dynamic>?> Function()? onTestConnection;

  const ChannelConnectionCard({
    super.key,
    required this.title,
    required this.channelKey,
    required this.icon,
    required this.primaryColor,
    required this.description,
    this.isConnected = false,
    this.onTestConnection,
  });

  @override
  State<ChannelConnectionCard> createState() => _ChannelConnectionCardState();
}

class _ChannelConnectionCardState extends State<ChannelConnectionCard> {
  bool _isTesting = false;
  String? _testResult;
  bool? _testSuccess;

  Future<void> _handleTest() async {
    if (widget.onTestConnection == null) return;
    setState(() {
      _isTesting = true;
      _testResult = null;
    });

    try {
      final res = await widget.onTestConnection!();
      if (res != null) {
        final status = res['status']?.toString();
        setState(() {
          _testSuccess = (status == 'success');
          _testResult = res['message']?.toString() ?? (status == 'success' ? 'Kết nối thành công!' : 'Kết nối thất bại');
        });
      }
    } finally {
      setState(() {
        _isTesting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: widget.primaryColor.withValues(alpha: 0.25),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: widget.primaryColor.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: widget.primaryColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(widget.icon, color: widget.primaryColor, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.title,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      widget.description,
                      style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: widget.isConnected
                      ? const Color(0xFF10B981).withValues(alpha: 0.15)
                      : const Color(0xFF64748B).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: widget.isConnected ? const Color(0xFF10B981) : const Color(0xFF64748B),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      widget.isConnected ? 'SẴN SÀNG' : 'CHƯA CẤU HÌNH',
                      style: TextStyle(
                        color: widget.isConnected ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                        fontSize: 9,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (_testResult != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: (_testSuccess == true ? const Color(0xFF10B981) : const Color(0xFFEF4444)).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: (_testSuccess == true ? const Color(0xFF10B981) : const Color(0xFFEF4444)).withValues(alpha: 0.3),
                ),
              ),
              child: Text(
                _testResult!,
                style: TextStyle(
                  color: _testSuccess == true ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                  fontSize: 11,
                ),
              ),
            ),
          ],
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              if (widget.onTestConnection != null)
                OutlinedButton.icon(
                  onPressed: _isTesting ? null : _handleTest,
                  icon: _isTesting
                      ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.cable_rounded, size: 14),
                  label: const Text('Kiểm tra kết nối', style: TextStyle(fontSize: 11)),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white,
                    side: const BorderSide(color: Color(0xFF334155)),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
