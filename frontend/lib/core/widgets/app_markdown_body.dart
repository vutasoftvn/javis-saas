import 'package:flutter/widgets.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';

// Task 10 (truthful-mvp-hardening) — mọi nơi render Markdown trong app phải
// đi qua widget này thay vì import trực tiếp package render markdown.
// flutter_markdown gốc đã ngừng bảo trì (discontinued trên pub.dev); repo
// chuyển sang flutter_markdown_plus (fork API tương thích) — nhờ bọc qua đây
// từ trước nên lần đổi package sau (nếu có) chỉ cần sửa 1 file.
export 'package:flutter_markdown_plus/flutter_markdown_plus.dart' show MarkdownStyleSheet;

/// Widget render nội dung Markdown dùng chung toàn app (chat bubble, hub
/// chat...). Forward thẳng tham số cần dùng tới `MarkdownBody` thật của
/// flutter_markdown_plus — không thêm hành vi khác ở đây để giữ đúng hành vi
/// render đã được test từ trước.
class AppMarkdownBody extends StatelessWidget {
  final String data;
  final bool selectable;
  final MarkdownStyleSheet? styleSheet;
  final void Function(String text, String? href, String title)? onTapLink;

  const AppMarkdownBody({
    super.key,
    required this.data,
    this.selectable = false,
    this.styleSheet,
    this.onTapLink,
  });

  @override
  Widget build(BuildContext context) {
    return MarkdownBody(
      data: data,
      selectable: selectable,
      styleSheet: styleSheet,
      onTapLink: onTapLink,
    );
  }
}
