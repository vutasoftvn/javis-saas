from fastapi import APIRouter, Depends, HTTPException
from typing import List, Any
from app.workforce.agents.profiles.schemas import AgentProfile
from app.workforce.composition.contracts import ResolvedProfile
from app.workforce.composition.service import ProfileCompositionService

router = APIRouter()

@router.get("/profiles", response_model=List[AgentProfile])
async def list_profiles() -> Any:
    """
    Lấy danh sách các base profiles.
    """
    return []

@router.get("/profiles/{profile_id}/preview", response_model=ResolvedProfile)
async def preview_profile(profile_id: str) -> Any:
    """
    Xem trước ResolvedProfile cho user hiện tại. Đảm bảo API này strip 
    các bí mật (secrets) và logic private khỏi payload trả về client.
    """
    # Placeholder
    raise HTTPException(status_code=404, detail="Profile not found")

@router.post("/profiles/{profile_id}/publish")
async def publish_profile(profile_id: str) -> Any:
    """
    Admin publish một draft profile.
    """
    # Placeholder
    raise HTTPException(status_code=403, detail="Unauthorized")
