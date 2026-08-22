from workforce.chat.chat_stream_bus import (
    MAX_DELTA_CHARS,
    _asyncpg_dsn,
    _payload_matches_session,
    split_delta,
)


def test_payload_matches_session_when_ids_equal():
    payload = '{"session_id": "abc", "message_id": "xyz"}'
    assert _payload_matches_session(payload, "abc") is True


def test_payload_does_not_match_different_session():
    payload = '{"session_id": "abc", "message_id": "xyz"}'
    assert _payload_matches_session(payload, "other") is False


def test_payload_malformed_json_does_not_match():
    assert _payload_matches_session("not-json", "abc") is False


def test_split_delta_keeps_small_chunk_intact():
    assert split_delta(10, "xin chào") == [(10, "xin chào")]


def test_split_delta_cuts_oversized_chunk_with_absolute_offsets():
    """Chunk to hơn giới hạn payload NOTIFY phải được cắt, và offset của từng mảnh phải
    là vị trí tuyệt đối trong nội dung - SSE dựa vào đó để biết mình có hụt mảnh nào không."""
    chunk = "a" * (MAX_DELTA_CHARS + 5)

    pieces = split_delta(100, chunk)

    assert [offset for offset, _ in pieces] == [100, 100 + MAX_DELTA_CHARS]
    assert "".join(text for _, text in pieces) == chunk


def test_asyncpg_dsn_strips_sqlalchemy_driver_suffix():
    """asyncpg.connect() không hiểu 'postgresql+psycopg2://'."""
    assert (
        _asyncpg_dsn("postgresql+psycopg2://u:p@host:5432/db")
        == "postgresql://u:p@host:5432/db"
    )


def test_asyncpg_dsn_leaves_plain_url_unchanged():
    assert _asyncpg_dsn("postgresql://u:p@host:5432/db") == "postgresql://u:p@host:5432/db"
