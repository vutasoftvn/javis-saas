from __future__ import annotations

__all__ = ["DEFAULT_CHUNK_SIZE", "DEFAULT_OVERLAP", "chunk_text"]

DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 100


def chunk_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Phân tách văn bản thành các chunks có độ chồng lấp (overlap) nhất định."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    stripped = text.strip()
    if not stripped:
        return []

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < len(stripped):
        chunk = stripped[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks
