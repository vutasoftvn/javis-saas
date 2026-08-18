import re
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.db.models import VaultDocument, VaultRevision, DocumentChunk

def build_graph(db: Session, brain_id: int) -> Dict[str, Any]:
    """
    Builds a node-edge graph of all documents in a brain based on [[wikilinks]].
    """
    docs = db.query(VaultDocument).filter(
        VaultDocument.brain_id == brain_id,
        VaultDocument.status == 'active'
    ).all()
    
    nodes = []
    edges = []
    doc_paths = {doc.path for doc in docs}
    
    for doc in docs:
        nodes.append({"id": doc.path, "label": doc.path.split('/')[-1]})
        
        if not doc.current_revision_id:
            continue
            
        # Instead of pulling from S3, we use the chunks in the database
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.revision_id == doc.current_revision_id
        ).all()
        
        full_text = "\n".join([chunk.text for chunk in chunks])
        
        links = set(re.findall(r'\[\[(.*?)\]\]', full_text))
        
        for link in links:
            target_path = None
            if link in doc_paths:
                target_path = link
            else:
                for p in doc_paths:
                    if p.endswith(f"/{link}") or p == link or p == f"{link}.md":
                        target_path = p
                        break
                        
            if target_path:
                edges.append({"source": doc.path, "target": target_path})
                
    return {"nodes": nodes, "edges": edges}
