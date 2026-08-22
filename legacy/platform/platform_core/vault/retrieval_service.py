from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from platform_core.vault.embedding_service import generate_embeddings

# Ngưỡng "stale" cho tài liệu regulatory_sensitivity chưa re-verify (Supplement §20.2: nội
# dung pháp lý/policy không được coi là current legal truth nếu chưa verify gần đây). 180
# ngày là default policy — chưa có yêu cầu per-workspace configurable nên không thêm bảng
# config cho một con số duy nhất.
REGULATORY_STALE_THRESHOLD_DAYS = 180


def _is_stale(regulatory_sensitivity: bool, last_verified: Optional[date]) -> bool:
    if not regulatory_sensitivity:
        return False
    if last_verified is None:
        return True
    return (date.today() - last_verified).days > REGULATORY_STALE_THRESHOLD_DAYS


async def search_chunks(
    db: Session,
    brain_id: int,
    query: str,
    k: int = 5,
    stage: Optional[str] = None,
    dimension: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search chunks using Hybrid Search (pgvector + TSVECTOR) and Reciprocal Rank Fusion.

    ``stage``/``dimension`` lọc theo metadata just-in-time coaching (Supplement §20) khi
    caller biết bối cảnh hiện tại (vd. Question Graph node đang hỏi). Mặc định None — không
    lọc gì cả — nên caller hiện tại (chat_execution_service._retrieve_context) không đổi
    hành vi nếu không truyền thêm 2 tham số này.
    """
    embeddings = await generate_embeddings([query])
    query_embedding = embeddings[0]

    stage_filter_sql = "AND (:stage IS NULL OR vd.stage = :stage)"
    dimension_filter_sql = "AND (:dimension IS NULL OR vd.dimension = :dimension)"

    # We use pgvector <=> (cosine distance) and websearch_to_tsquery
    sql = text(f"""
        WITH vector_search AS (
            SELECT dc.id,
                   dc.revision_id,
                   dc.text,
                   vd.path,
                   vd.regulatory_sensitivity,
                   vd.last_verified,
                   1 - (dc.embedding <=> :query_embedding ::vector) AS vector_score,
                   RANK() OVER (ORDER BY dc.embedding <=> :query_embedding ::vector) AS vector_rank
            FROM document_chunks dc
            JOIN vault_revisions vr ON dc.revision_id = vr.id
            JOIN vault_documents vd ON vr.document_id = vd.id
            WHERE vd.brain_id = :brain_id AND vd.status = 'active'
              AND vd.current_revision_id = vr.id
              {stage_filter_sql}
              {dimension_filter_sql}
            ORDER BY dc.embedding <=> :query_embedding ::vector
            LIMIT 50
        ),
        fts_search AS (
            SELECT dc.id,
                   vd.regulatory_sensitivity,
                   vd.last_verified,
                   ts_rank(dc.fts, websearch_to_tsquery('english', :query)) AS fts_score,
                   RANK() OVER (ORDER BY ts_rank(dc.fts, websearch_to_tsquery('english', :query)) DESC) AS fts_rank
            FROM document_chunks dc
            JOIN vault_revisions vr ON dc.revision_id = vr.id
            JOIN vault_documents vd ON vr.document_id = vd.id
            WHERE vd.brain_id = :brain_id AND vd.status = 'active'
              AND vd.current_revision_id = vr.id
              AND dc.fts @@ websearch_to_tsquery('english', :query)
              {stage_filter_sql}
              {dimension_filter_sql}
            ORDER BY fts_score DESC
            LIMIT 50
        )
        SELECT
            COALESCE(vs.id, fs.id) as chunk_id,
            COALESCE(vs.text, (SELECT text FROM document_chunks WHERE id = fs.id)) as text,
            COALESCE(vs.path, (SELECT vd.path FROM vault_documents vd JOIN vault_revisions vr ON vr.document_id = vd.id JOIN document_chunks dc ON dc.revision_id = vr.id WHERE dc.id = fs.id)) as path,
            COALESCE(vs.regulatory_sensitivity, fs.regulatory_sensitivity) as regulatory_sensitivity,
            COALESCE(vs.last_verified, fs.last_verified) as last_verified,
            COALESCE(1.0 / (60 + vs.vector_rank), 0.0) + COALESCE(1.0 / (60 + fs.fts_rank), 0.0) AS rrf_score
        FROM vector_search vs
        FULL OUTER JOIN fts_search fs ON vs.id = fs.id
        ORDER BY rrf_score DESC
        LIMIT :k
    """)

    result = db.execute(sql, {
        "query_embedding": str(query_embedding),
        "brain_id": str(brain_id),
        "query": query,
        "k": k,
        "stage": stage,
        "dimension": dimension,
    })

    chunks = []
    for row in result:
        regulatory_sensitivity = bool(row.regulatory_sensitivity) if row.regulatory_sensitivity is not None else False
        last_verified = row.last_verified
        chunks.append({
            "chunk_id": str(row.chunk_id),
            "text": row.text,
            "path": row.path,
            "score": float(row.rrf_score),
            "regulatory_sensitivity": regulatory_sensitivity,
            "last_verified": last_verified.isoformat() if last_verified else None,
            "stale": _is_stale(regulatory_sensitivity, last_verified),
        })

    return chunks
