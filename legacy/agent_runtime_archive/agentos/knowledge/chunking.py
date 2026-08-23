from __future__ import annotations

DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 100


def chunk_text(text: str, *, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP) -> list[str]:
    """Chia `text` thành các chunk theo ký tự, có overlap giữa các chunk
    liền kề để không cắt đứt ngữ cảnh ngay tại ranh giới chunk (blueprint
    §66 giai đoạn "chunk"). Chunk theo ký tự đơn giản, KHÔNG theo token hay
    ranh giới câu/đoạn — không cần thêm dependency tokenizer cho MVP; nếu
    sau này cần chunk theo câu/token thật, đây là chỗ cần thay thế.

    Text rỗng/toàn khoảng trắng trả về danh sách rỗng (không tạo chunk rác).
    """
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
