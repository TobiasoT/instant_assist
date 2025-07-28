from __future__ import annotations

import asyncio
import contextlib
from http.client import HTTPException





import os
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
from livekit.api import AccessToken, VideoGrants  # note: livekit.api not livekit.api.access_token
from typing import AsyncIterator

import asyncio
import contextlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from source.dev_logger import debug
from source.live_kit.generate_livekit_token import make_token
from source.live_kit.livekit_room import create_and_run_livekit_room
from source.locations_and_config import config, templates_dir, path_live_kit_index_html

from source.dev_logger import debug
from source.live_kit.generate_livekit_token import make_token
from source.live_kit.livekit_room import create_and_run_livekit_room
from source.locations_and_config import  templates_dir, path_live_kit_index_html, config

from fastapi import APIRouter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    debug("🔵 Starting LiveKit room update loop…")
    loop_task = asyncio.create_task(create_and_run_livekit_room())
    try:
        yield
    finally:
        debug("🔴 Stopping update loop…")
        loop_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await loop_task


live_kit_app = FastAPI(lifespan=lifespan)  # ← register it

templates = Jinja2Templates(directory=templates_dir)

class TokenRequest(BaseModel):
    identity: str = "anonymous"
    room: str = "default-room"

class TokenResponse(BaseModel):
    token: str

@live_kit_app.post("/token", response_model=TokenResponse)
async def mint_token(req: TokenRequest) -> TokenResponse:
    debug(f"Minting token for identity: {req.identity}, room: {config.livekit_room_name}")
    token = make_token(identity=req.identity, room=config.livekit_room_name, hours=6)
    return TokenResponse(token=token)

@live_kit_app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    debug(f"Serving index with LiveKit WS URL: {config.livekit_ws_url}")
    return templates.TemplateResponse(
        path_live_kit_index_html.name,
        {"request": request, "LIVEKIT_WS_URL": config.livekit_ws_url},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(live_kit_app, host= "localhost", port=8080)
    # uvicorn.run("server:app", host="0