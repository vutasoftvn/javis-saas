from agentos.core.audit_sink import SqliteAuditSink


def test_sqlite_audit_sink_persists_and_exports_by_run_id(tmp_path):
    db_path = tmp_path / "audit_log.sqlite3"
    sink = SqliteAuditSink(db_path=db_path)

    sink.record(event_type="policy.evaluated", run_id="run-1", subject="FINANCIAL_ACTION", decision="REQUIRE_APPROVAL")
    sink.record(event_type="approval.requested", run_id="run-1", subject="pay_invoice", actor="agent", decision="PENDING")
    sink.record(event_type="approval.decided", run_id="run-1", subject="pay_invoice", actor="founder", decision="APPROVED")
    # sự kiện của run khác không được lẫn vào kết quả export_run("run-1")
    sink.record(event_type="policy.evaluated", run_id="run-2", subject="READ_LOCAL", decision="ALLOW")

    events = sink.export_run("run-1")

    assert [e["event_type"] for e in events] == ["policy.evaluated", "approval.requested", "approval.decided"]
    assert events[2]["decision"] == "APPROVED"
    assert events[2]["actor"] == "founder"

    sink.close()

    # Đóng rồi mở lại file phải vẫn thấy dữ liệu đã ghi (bền vững qua restart
    # process, không chỉ tồn tại trong connection đang mở).
    reopened = SqliteAuditSink(db_path=db_path)
    assert len(reopened.export_run("run-1")) == 3
    reopened.close()
