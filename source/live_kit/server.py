# server.py
# from __future__ import annotations
#
# import os
# from datetime import timedelta
#
#
# from fastapi import FastAPI, Request
# from fastapi.templating import Jinja2Templates
# from fastapi.responses import HTMLResponse
# from pydantic import BaseModel
# from pydantic_settings import BaseSettings, SettingsConfigDict
# from livekit.api.access_token import AccessToken, VideoGrants
#
# from fastapi import FastAPI
# from pydantic import BaseModel
# from pydantic_settings import BaseSettings, SettingsConfigDict
# from livekit.api.access_token import AccessToken, VideoGrants
# from fastapi.responses import FileResponse
# from starlette.responses import HTMLResponse
# from starlette.templating import Jinja2Templates
#
# from source.locations_and_config import path_live_kit_index_html, content_path_live_kit_url
#
#
# class Settings(BaseSettings):
#     LIVEKIT_API_KEY:    str
#     LIVEKIT_API_SECRET: str
#
#     model_config = SettingsConfigDict(
#         env_file=".env",
#         env_file_encoding="utf-8",
#     )
#
# cfg = Settings(LIVEKIT_API_KEY=os.environ.get("LIVEKIT_API_KEY"),
#                LIVEKIT_API_SECRET=os.environ.get("LIVEKIT_API_SECRET"))
# app = FastAPI()
#
# class TokenRequest(BaseModel):
#     identity: str = "anonymous"
#     room:     str = "default-room"
#
# class TokenResponse(BaseModel):
#     token: str
#
# @app.post("/token", response_model=TokenResponse)
# async def mint_token(req: TokenRequest) -> TokenResponse:
#     token = (
#         AccessToken(cfg.LIVEKIT_API_KEY, cfg.LIVEKIT_API_SECRET)
#         .with_identity(req.identity)
#         .with_grants(VideoGrants(room_join=True, room=req.room))
#         .with_ttl(timedelta(hours=222))
#         .to_jwt()
#     )
#     return TokenResponse(token=token)
#
#
# templates = Jinja2Templates(directory=path_live_kit_index_html.parent)
# @app.get("/", response_class=HTMLResponse)
# async def get_index(request: Request) -> HTMLResponse:
#     return templates.TemplateResponse(
#         path_live_kit_index_html.name,
#         {
#             "request": request,
#             "livekit_ws_url": content_path_live_kit_url.split("=")[1],
#         },
#     )
#
#
#
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "server:app",
#         host="0.0.0.0",
#         port=8080,
#         reload=True,         # pick up code changes automatically
#     )
#
#
#












# server.py
from __future__ import annotations

import os
from datetime import timedelta
from starlette.staticfiles import StaticFiles

from source.live_kit.generate_livekit_token import make_token
from source.locations_and_config import path_static_dir, config

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
from livekit.api import AccessToken, VideoGrants  # note: livekit.api not livekit.api.access_token

from source.dev_logger import debug
from source.locations_and_config import  templates_dir, path_live_kit_index_html


class Settings(BaseSettings):
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_WS_URL: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

cfg = Settings(
LIVEKIT_API_KEY = config.livekit_api_key,
LIVEKIT_API_SECRET = config.livekit_api_secret,
LIVEKIT_WS_URL = config.livekit_ws_url,
)

app = FastAPI()

app.mount(
    "/static", StaticFiles(directory=path_static_dir ), name="static")
templates = Jinja2Templates(directory=templates_dir)

class TokenRequest(BaseModel):
    identity: str = "anonymous"
    room: str = "default-room"

class TokenResponse(BaseModel):
    token: str

@app.post("/token", response_model=TokenResponse)
async def mint_token(req: TokenRequest) -> TokenResponse:
    debug(f"Generating token for identity: {req.identity}, room: {req.room}")
    token = make_token(identity=req.identity, room=req.room, hours=6)
    return TokenResponse(token=token)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    debug(f"Serving index page with LiveKit WS URL: {cfg.LIVEKIT_WS_URL}")
    return templates.TemplateResponse(
        path_live_kit_index_html.name,
        {"request": request, "LIVEKIT_WS_URL": cfg.LIVEKIT_WS_URL},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="localhost", port=8080, reload=True)
    # uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)

