// M5 §5 — RemoteAccessBanner rendering.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/remote_access/models/runtime_status.dart';
import 'package:frontend/modules/remote_access/widgets/remote_access_banner.dart';

Widget _wrap(RuntimeStatus? s) =>
    MaterialApp(home: Scaffold(body: RemoteAccessBanner(status: s)));

void main() {
  testWidgets('ẩn khi status null', (t) async {
    await t.pumpWidget(_wrap(null));
    expect(find.byType(RemoteAccessBanner), findsOneWidget);
    expect(find.byType(Row), findsNothing);
  });

  testWidgets('ẩn khi LOCAL_ONLY online', (t) async {
    await t.pumpWidget(_wrap(
        RuntimeStatus(mode: RuntimeMode.localOnly, presence: NodePresence.online)));
    expect(find.byType(Icon), findsNothing);
  });

  testWidgets('OFFLINE ⇒ hiện "Node offline" + thông điệp chỉ đọc + as_of', (t) async {
    await t.pumpWidget(_wrap(RuntimeStatus(
      mode: RuntimeMode.remoteAccess,
      presence: NodePresence.offline,
      asOf: DateTime.utc(2026, 8, 29, 9, 30),
    )));
    expect(find.text('Node offline'), findsOneWidget);
    expect(find.textContaining('chỉ đọc'), findsOneWidget);
    expect(find.textContaining('Dữ liệu tính đến'), findsOneWidget);
    expect(find.byIcon(Icons.cloud_off_rounded), findsOneWidget);
  });

  testWidgets('DEGRADED ⇒ hiện "Kết nối chập chờn"', (t) async {
    await t.pumpWidget(_wrap(RuntimeStatus(
      mode: RuntimeMode.remoteAccess,
      presence: NodePresence.degraded,
    )));
    expect(find.text('Kết nối chập chờn'), findsOneWidget);
    expect(find.byIcon(Icons.sync_problem_rounded), findsOneWidget);
  });
}
