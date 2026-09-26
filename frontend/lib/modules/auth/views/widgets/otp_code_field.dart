import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/theme/app_theme.dart';

/// Ô nhập mã xác thực tách thành từng ô riêng (mặc định 6 số).
///
/// Giá trị vẫn nằm trong [controller] nên controller/luồng gửi mã hiện có không đổi.
/// Một TextField ẩn giữ focus, bàn phím và thao tác dán; các ô chỉ hiển thị lại nội dung.
class OtpCodeField extends StatefulWidget {
  const OtpCodeField({super.key, required this.controller, this.length = 6, this.autofocus = false, this.onSubmitted});

  final TextEditingController controller;
  final int length;
  final bool autofocus;
  final VoidCallback? onSubmitted;

  @override
  State<OtpCodeField> createState() => _OtpCodeFieldState();
}

class _OtpCodeFieldState extends State<OtpCodeField> {
  final _focusNode = FocusNode();

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: _focusNode.requestFocus,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // TextField ẩn: nhận ký tự, giới hạn độ dài và chỉ cho chữ số.
          Positioned.fill(
            child: Opacity(
              opacity: 0,
              child: TextField(
                controller: widget.controller,
                focusNode: _focusNode,
                autofocus: widget.autofocus,
                keyboardType: TextInputType.number,
                showCursor: false,
                enableInteractiveSelection: false,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(widget.length)],
                onSubmitted: (_) => widget.onSubmitted?.call(),
              ),
            ),
          ),
          IgnorePointer(
            child: ListenableBuilder(
              listenable: Listenable.merge([widget.controller, _focusNode]),
              builder: (context, _) {
                final text = widget.controller.text;
                final activeIndex = text.length.clamp(0, widget.length - 1);
                return Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    for (var i = 0; i < widget.length; i++) ...[
                      if (i > 0) const SizedBox(width: 8),
                      _OtpBox(char: i < text.length ? text[i] : '', active: _focusNode.hasFocus && i == activeIndex),
                    ],
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _OtpBox extends StatelessWidget {
  const _OtpBox({required this.char, required this.active});

  final String char;
  final bool active;

  @override
  Widget build(BuildContext context) {
    return Flexible(
      child: AspectRatio(
        aspectRatio: 0.85,
        child: Container(
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppTheme.backgroundDark.withValues(alpha: 0.8),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: active ? AppTheme.primary : AppTheme.borderDark, width: active ? 1.5 : 1),
          ),
          child: Text(
            char,
            style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w600),
          ),
        ),
      ),
    );
  }
}
