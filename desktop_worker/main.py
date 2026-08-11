import os
import sys
import subprocess
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

app = FastAPI(title="COSA Local Desktop Worker Plane", version="1.0.0")


class LocalExecutionRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    timeout_seconds: Optional[int] = 120


@app.get("/health")
def health_check():
    return {
        "status": "online",
        "plane": "local_worker",
        "platform": sys.platform,
        "pid": os.getpid(),
        "capabilities": ["claude_code", "git", "filesystem", "browser"]
    }


@app.post("/execute-task")
def execute_local_task(req: LocalExecutionRequest):
    """Thực thi an toàn trong phạm vi loopback máy trạm của lập trình viên."""
    try:
        res = subprocess.run(
            req.command,
            shell=True,
            cwd=req.cwd or os.getcwd(),
            capture_output=True,
            text=True,
            timeout=req.timeout_seconds or 120
        )
        return {
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "status": "completed" if res.returncode == 0 else "failed"
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command execution timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Chỉ lắng nghe trên 127.0.0.1 (Loopback only - Tuân thủ nghiêm ngặt Blueprint §113)
    uvicorn.run(app, host="127.0.0.1", port=8765)
