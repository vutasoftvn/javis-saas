import re
from typing import List

def chunk_markdown(text: str) -> List[str]:
    """
    Chunks a markdown document by headings.
    """
    # Split by markdown headers (# to ######)
    chunks = re.split(r'(?m)^#{1,6}\s+.*$', text)
    headings = re.findall(r'(?m)^#{1,6}\s+.*$', text)
    
    result = []
    if chunks and chunks[0].strip():
        result.append(chunks[0].strip())
    
    for i, heading in enumerate(headings):
        chunk_content = heading + "\n" + (chunks[i+1] if i+1 < len(chunks) else "")
        if chunk_content.strip():
            result.append(chunk_content.strip())
            
    return result if result else [text.strip()]
