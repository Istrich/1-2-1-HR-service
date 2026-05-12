import os
import mimetypes
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import anyio

from app.core.config import OUTPUTS_DIR
from app.api.endpoints import auth, process, reports, settings
from app.db.database import Base, engine

app = FastAPI(title="HR 1-2-1 Web Refactored")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/dist/index.html")

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(settings.router, prefix="/api", tags=["settings"])
app.include_router(process.router, prefix="/api", tags=["process"])
app.include_router(reports.router, prefix="/api", tags=["reports"])

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Output serving (same logic as before for audio streaming)
def _safe_output_file(relative: str) -> Path:
    base = OUTPUTS_DIR.resolve()
    full = (OUTPUTS_DIR / relative).resolve()
    try:
        full.relative_to(base)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Not found") from e
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return full

@app.api_route("/outputs/{path:path}", methods=["GET", "HEAD"])
async def serve_outputs_file(path: str, request: Request):
    full = _safe_output_file(path)
    stat = full.stat()
    size = stat.st_size
    media_type, _ = mimetypes.guess_type(str(full))
    if not media_type:
        media_type = "application/octet-stream"

    headers = {"accept-ranges": "bytes", "content-length": str(size)}
    if request.method == "HEAD":
        return Response(status_code=200, headers=headers, media_type=media_type)

    async def _stream():
        async with await anyio.open_file(full, "rb") as f:
            while True:
                chunk = await f.read(64*1024)
                if not chunk: break
                yield chunk

    return StreamingResponse(_stream(), status_code=200, media_type=media_type, headers=headers)
