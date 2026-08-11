import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.modules.vault.embedding_service import generate_embeddings

async def search_chunks(db: Session, brain_id: uuid.UUID, query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Search chunks using Hybrid Search (pgvector + TSVECTOR) and Reciprocal Rank Fusion.
    """
    embeddings = await generate_embeddings([query])
    query_embedding = embeddings[0]
    
    # We use pgvector <=> (cosine distance) and websearch_to_tsquery
    sql = text("""
        WITH vector_search AS (
            SELECT dc.id,
                   dc.revision_id,
                   dc.text,
                   vd.path,
                   1 - (dc.embedding <=> :query_embedding::vector) AS vector_score,
                   RANK() OVER (ORDER BY dc.embedding <=> :query_embedding::vector) AS vector_rank
            FROM document_chunks dc
            JOIN vault_revisions vr ON dc.revision_id = vr.id
            JOIN vault_documents vd ON vr.document_id = vd.id
            WHERE vd.brain_id = :brain_id AND vd.status = 'active'
              AND vd.current_revision_id = vr.id
            ORDER BY dc.embedding <=> :query_embedding::vector
            LIMIT 50
        ),
        fts_search AS (
            SELECT dc.id,
                   ts_rank(dc.fts, websearch_to_tsquery('english', :query)) AS fts_score,
                   RANK() OVER (ORDER BY ts_rank(dc.fts, websearch_to_tsquery('english', :query)) DESC) AS fts_rank
            FROM document_chunks dc
            JOIN vault_revisions vr ON dc.revision_id = vr.id
            JOIN vault_documents vd ON vr.document_id = vd.id
            WHERE vd.brain_id = :brain_id AND vd.status = 'active'
              AND vd.current_revision_id = vr.id
              AND dc.fts @@ websearch_to_tsquery('english', :query)
            ORDER BY fts_score DESC
            LIMIT 50
        )
        SELECT 
            COALESCE(vs.id, fs.id) as chunk_id,
            COALESCE(vs.text, (SELECT text FROM document_chunks WHERE id = fs.id)) as text,
            COALESCE(vs.path, (SELECT vd.path FROM vault_documents vd JOIN vault_revisions vr ON vr.document_id = vd.id JOIN document_chunks dc ON dc.revision_id = vr.id WHERE dc.id = fs.id)) as path,
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
        "k": k
    })
    
    chunks = []
    for row in result:
        chunks.append({
            "chunk_id": str(row.chunk_id),
            "text": row.text,
            "path": row.path,
            "score": float(row.rrf_score)
        })
        
    return chunks
