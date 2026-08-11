import os
import httpx
from typing import List

async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using OpenAI's API.
    """
    if not texts:
        return []

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Return mock embeddings if no API key is set for local dev
        return [[0.0] * 1536 for _ in texts]
        
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "input": texts,
                "model": "text-embedding-3-small"
            },
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]
