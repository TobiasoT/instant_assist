from __future__ import annotations

import asyncio
from http.client import HTTPException

from fastapi import APIRouter
from fastapi import Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette.websockets import WebSocket, WebSocketDisconnect

from source.global_instances.testing_insctances import global_fake_messages
from source.locations_and_config import templates_dir
from source.dev_logger import debug
from source.web_app.core.summary_board import summary_board
from source.web_app.core.summary_board_filling_loop import summary_report_filling_loop, fake_summary_report_filling_loop
from source.web_app.core.update_prompts import PromptList, PromptIn, _update_prompts, prompts_lock, prompts

summary_board_router = APIRouter()
templates = Jinja2Templates(directory = templates_dir)


@summary_board_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
	await summary_board.connect(websocket)
	try:
		while True:
			await websocket.receive_text()  # consume pings
	except WebSocketDisconnect:
		summary_board.disconnect(websocket)


@summary_board_router.get("/", response_class = HTMLResponse)
async def index(request: Request) -> HTMLResponse:
	# Render the HTML template and inject the current presets
	global prompts
	return templates.TemplateResponse(
		"summary_board.html",  # the HTML file above, saved under templates/
		{
			"request": request,
			"predefined_prompts": prompts,  # Jinja will inject this
		},
	)


@summary_board_router.get("/api/prompts", response_model = PromptList)
async def get_prompts() -> PromptList:
	return PromptList(prompts = prompts)


@summary_board_router.post("/api/prompt", response_model = PromptList)
async def post_prompt(payload: PromptIn) -> PromptList:
	# Update presets and return the latest list
	async with prompts_lock:
		global prompts
		prompts = _update_prompts(payload.prompt)
		return PromptList(prompts = prompts)


@summary_board_router.delete("/api/prompt", response_model = PromptList)
async def delete_prompt(payload: PromptIn) -> PromptList:
	global prompts
	async with prompts_lock:
		if payload.prompt not in prompts:
			raise HTTPException(status_code = 404, detail = "Prompt not found")
		updated = [p for p in prompts if p != payload.prompt]
		prompts.clear()
		prompts.extend(updated)
	return PromptList(prompts = prompts)


@summary_board_router.post("/api/start")
async def start_summary_board():
	loop_task2 = asyncio.create_task(summary_report_filling_loop())
	loop_task2.add_done_callback(lambda t: t.exception() and debug(f"Summary loop error: {t.exception()}\n{t.get_stack()}"))
	return {"status": "started", "message": "Summary board started successfully"}


@summary_board_router.get("/fill_fake_messages")
async def start_summary_board():
	loop_task2 = asyncio.create_task(fake_summary_report_filling_loop(
		fake_messages = global_fake_messages,
		sleep_between = 1
	))
	loop_task2.add_done_callback(lambda t: t.exception() and debug(f"Summary loop error: {t.exception()}"))
	return {"status": "started", "message": "Summary board started successfully"}