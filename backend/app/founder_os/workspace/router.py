"""Company Workspace API Router.

Provides endpoints for Flutter Frontend to explore, read, update, and reset files in ~/.cosa/companies/<company_id>/
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel

from app.founder_os.workspace.manager import workspace_manager

router = APIRouter()


class WorkspaceFileItem(BaseModel):
    relative_path: str
    category: str
    is_protected: bool = False


class WorkspaceContentRequest(BaseModel):
    relative_path: str
    content: str
    company_id: Optional[str] = "1"


class ResetDefaultRequest(BaseModel):
    relative_path: str
    company_id: Optional[str] = "1"


@router.get("/files")
def list_workspace_files(company_id: str = Query("1")) -> Dict[str, Any]:
    """List available markdown workspace files for the company."""
    company_dir = workspace_manager.init_company_workspace(company_id)
    files = []

    for path in company_dir.rglob("*.md"):
        rel = str(path.relative_to(company_dir))
        is_protected = any(rel.startswith(p) for p in ["company/", "founder/", "policies/"])
        category = rel.split("/")[0] if "/" in rel else "root"
        files.append({
            "relative_path": rel,
            "category": category,
            "is_protected": is_protected,
            "size_bytes": path.stat().st_size,
        })

    return {
        "company_id": str(company_id),
        "workspace_path": str(company_dir),
        "files": sorted(files, key=lambda x: x["relative_path"]),
    }


@router.get("/file")
def read_workspace_file(
    relative_path: str = Query(...),
    company_id: str = Query("1"),
) -> Dict[str, Any]:
    """Read contents of a workspace file."""
    content = workspace_manager.read_file(company_id, relative_path)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace file '{relative_path}' not found.",
        )
    return {
        "company_id": str(company_id),
        "relative_path": relative_path,
        "content": content,
    }


@router.post("/file")
def write_workspace_file(req: WorkspaceContentRequest) -> Dict[str, Any]:
    """Save content to a workspace file."""
    target = workspace_manager.write_file(
        company_id=req.company_id or "1",
        relative_path=req.relative_path,
        content=req.content,
    )
    return {
        "ok": True,
        "company_id": req.company_id or "1",
        "relative_path": req.relative_path,
        "saved_path": str(target),
    }


@router.post("/reset-default")
def reset_workspace_file(req: ResetDefaultRequest) -> Dict[str, Any]:
    """Reset a customized workspace file back to system default."""
    success = workspace_manager.reset_file_to_default(
        company_id=req.company_id or "1",
        relative_path=req.relative_path,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No system default available for '{req.relative_path}'.",
        )
    content = workspace_manager.read_file(req.company_id or "1", req.relative_path)
    return {
        "ok": True,
        "relative_path": req.relative_path,
        "content": content,
    }
