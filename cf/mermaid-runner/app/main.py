from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class IngestPayload(BaseModel):
    source: str
    meta: Optional[Dict[str, Any]] = None


@app.get("/api/health")
async def health() -> Dict[str, bool]:
    return {"ok": True}


@app.post("/api/mermaid/ingest")
async def ingest(payload: IngestPayload) -> Dict[str, Any]:
    source = payload.source
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return {
        "ok": True,
        "receivedChars": len(source),
        "sha256": digest,
    }
