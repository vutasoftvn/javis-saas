import pytest

from agentos.knowledge.chunking import chunk_text


def test_chunk_text_returns_empty_list_for_blank_input():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_chunk_text_returns_single_chunk_when_shorter_than_chunk_size():
    text = "hello world"
    assert chunk_text(text, chunk_size=100, overlap=10) == ["hello world"]


def test_chunk_text_splits_long_text_into_multiple_overlapping_chunks():
    text = "a" * 200
    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) == 3  # start=0(len100), start=80(len100), start=160(len40)
    assert len(chunks[0]) == 100
    assert len(chunks[1]) == 100
    assert len(chunks[2]) == 40
    # nối lại phải phủ hết text gốc (có overlap nên tổng dài hơn text gốc)
    assert sum(len(c) for c in chunks) >= len(text)


def test_chunk_text_consecutive_chunks_actually_overlap():
    text = "0123456789" * 10  # 100 chars, ký tự có thể phân biệt vị trí
    chunks = chunk_text(text, chunk_size=40, overlap=10)

    # 10 ký tự cuối của chunk trước phải trùng 10 ký tự đầu của chunk sau
    assert chunks[0][-10:] == chunks[1][:10]


def test_chunk_text_rejects_overlap_not_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=50, overlap=50)
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=50, overlap=60)
