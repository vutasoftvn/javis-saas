import 'package:flutter/material.dart';

class AgentTestRunDrawer extends StatefulWidget {
  final Map<String, dynamic> agent;
  final Function(String prompt, String? modelOverride, double temperature) onExecute;
  final bool isLoading;
  final Map<String, dynamic>? result;
  final VoidCallback onClose;

  const AgentTestRunDrawer({
    super.key,
    required this.agent,
    required this.onExecute,
    required this.isLoading,
    this.result,
    required this.onClose,
  });

  @override
  State<AgentTestRunDrawer> createState() => _AgentTestRunDrawerState();
}

class _AgentTestRunDrawerState extends State<AgentTestRunDrawer> {
  final TextEditingController _promptController = TextEditingController();
  String? _selectedModel;
  double _temperature = 0.2;

  final List<Map<String, String>> _availableModels = [
    {'label': 'Mặc định theo cấu hình Agent', 'value': ''},
    {'label': 'Claude 3.5 Sonnet (Anthropic)', 'value': 'claude-3-5-sonnet-20241022'},
    {'label': 'DeepSeek R1 Reasoner (DeepSeek)', 'value': 'deepseek-reasoner'},
    {'label': 'Gemini 2.0 Flash (Google)', 'value': 'gemini-2.0-flash'},
    {'label': 'Llama 3.2 3B (Local Ollama)', 'value': 'llama3.2:latest'},
  ];

  @override
  void initState() {
    super.initState();
    _promptController.text = 'Hãy tóm tắt và đánh giá nhiệm vụ ưu tiên tuần này.';
  }

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final agentName = widget.agent['name'] ?? 'Agent';
    final agentKey = widget.agent['key'] ?? '';
    final defaultProfile = widget.agent['default_model_profile'] ?? 'reasoning';

    return Container(
      width: 480,
      height: double.infinity,
      color: const Color(0xFF0F172A),
      child: Column(
        children: [
          // Drawer Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            decoration: const BoxDecoration(
              color: Color(0xFF1E293B),
              border: Border(bottom: BorderSide(color: Color(0xFF334155))),
            ),
            child: Row(
              children: [
                const Icon(Icons.terminal_rounded, color: Colors.blueAccent, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Test Run: $agentName',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        'key: $agentKey | profile: $defaultProfile',
                        style: TextStyle(color: Colors.grey.shade400, fontSize: 11.5),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: widget.onClose,
                  icon: const Icon(Icons.close_rounded, color: Colors.grey),
                ),
              ],
            ),
          ),

          // Body Form & Result View
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                // Model Override Dropdown
                const Text(
                  'Chọn Model Runtime Override',
                  style: TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF334155)),
                  ),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<String>(
                      value: _selectedModel ?? '',
                      dropdownColor: const Color(0xFF1E293B),
                      isExpanded: true,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      items: _availableModels.map((m) {
                        return DropdownMenuItem<String>(
                          value: m['value']!,
                          child: Text(m['label']!),
                        );
                      }).toList(),
                      onChanged: (val) {
                        setState(() {
                          _selectedModel = val;
                        });
                      },
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                // Temperature Slider
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Temperature (Độ sáng tạo)',
                      style: TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600),
                    ),
                    Text(
                      _temperature.toStringAsFixed(2),
                      style: const TextStyle(color: Colors.blueAccent, fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
                SliderTheme(
                  data: SliderTheme.of(context).copyWith(
                    activeTrackColor: Colors.blueAccent,
                    inactiveTrackColor: const Color(0xFF334155),
                    thumbColor: Colors.blueAccent,
                    overlayColor: Colors.blueAccent.withValues(alpha: 0.2),
                  ),
                  child: Slider(
                    value: _temperature,
                    min: 0.0,
                    max: 1.0,
                    divisions: 20,
                    onChanged: (val) {
                      setState(() {
                        _temperature = val;
                      });
                    },
                  ),
                ),

                const SizedBox(height: 12),

                // User Prompt Input
                const Text(
                  'Câu lệnh thực thi (User Prompt)',
                  style: TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _promptController,
                  maxLines: 4,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'Nhập prompt kiểm thử...',
                    hintStyle: TextStyle(color: Colors.grey.shade600),
                    filled: true,
                    fillColor: const Color(0xFF1E293B),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: Color(0xFF334155)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: Color(0xFF334155)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: Colors.blueAccent),
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                // Submit Button
                ElevatedButton.icon(
                  onPressed: widget.isLoading
                      ? null
                      : () {
                          if (_promptController.text.trim().isNotEmpty) {
                            widget.onExecute(
                              _promptController.text.trim(),
                              _selectedModel?.isNotEmpty == true ? _selectedModel : null,
                              _temperature,
                            );
                          }
                        },
                  icon: widget.isLoading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.play_arrow_rounded, color: Colors.white),
                  label: Text(
                    widget.isLoading ? 'Đang thực thi...' : 'Chạy thử nghiệm (Run Test)',
                    style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, color: Colors.white),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blueAccent,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),

                const SizedBox(height: 24),

                // Results Section
                if (widget.result != null) ...[
                  const Divider(color: Color(0xFF334155)),
                  const SizedBox(height: 12),
                  const Text(
                    'Kết quả thực thi (Execution Output)',
                    style: TextStyle(color: Colors.white, fontSize: 13.5, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 10),

                  // Metrics Bar
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1E293B),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFF334155)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildMetric(
                          label: 'Tokens',
                          value: '${widget.result!['usage']?['total_tokens'] ?? 0}',
                        ),
                        _buildMetric(
                          label: 'Cost',
                          value: '\$${(widget.result!['usage']?['cost_usd'] ?? 0.0).toStringAsFixed(4)}',
                          valueColor: const Color(0xFF10B981),
                        ),
                        _buildMetric(
                          label: 'Latency',
                          value: '${widget.result!['latency_ms'] ?? 0} ms',
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 12),

                  // Output Text Console
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: const Color(0xFF020617),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFF1E293B)),
                    ),
                    child: SelectableText(
                      widget.result!['content']?.toString() ?? 'No output returned.',
                      style: const TextStyle(
                        color: Color(0xFFE2E8F0),
                        fontSize: 13,
                        height: 1.5,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetric({required String label, required String value, Color? valueColor}) {
    return Column(
      children: [
        Text(label, style: TextStyle(color: Colors.grey.shade400, fontSize: 11)),
        const SizedBox(height: 3),
        Text(
          value,
          style: TextStyle(
            color: valueColor ?? Colors.white,
            fontSize: 13,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}
