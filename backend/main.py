"""Alias tương thích ngược cho `app.full_main` (refactor app-factory, Quyết
định 3). Tooling/docs/`docker-compose.yml` hiện có đang tham chiếu
`uvicorn app.main:app` - file này giữ nguyên điều đó hoạt động, import lại
đúng 1 FastAPI instance mà `app.full_main` đã build qua
`create_app("full")` thay vì build lại 1 bản trùng."""
from full_main import app

__all__ = ["app"]

if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
