import asyncio
import contextlib
import shutil

from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

from source.agents.default_search_agent import DefaultAgent
from source.dev_logger import debug
from source.live_kit.livekit_room import create_and_run_livekit_room
from source.locations_and_config import path_static_dir, templates_dir, uploads_dir
from source.web_app.core.summary_board_filling_loop import summary_report_filling_loop
from source.web_app.routers.livekit.live_kit_starter import live_kit_app
from source.web_app.routers.summary_board.summary_board import summary_board_router
from typing import AsyncIterator, List



@contextlib.asynccontextmanager
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


app = FastAPI(title="Agent Summary Board", lifespan=lifespan)  # ← register it

# Initialize templates
templates = Jinja2Templates(directory=templates_dir)

# Ensure upload directory exists
uploads_dir.mkdir(parents=True, exist_ok=True)

app.mount(
    "/static", StaticFiles(directory=path_static_dir ), name="static")

# Main entry point route
@app.get("/", response_class=HTMLResponse)
async def main_index(request: Request):
    # Sample prompts for the main page
    sample_prompts = [
        "Analyze the uploaded documents and provide key insights",
        "Summarize the main points and provide actionable recommendations",
        "Extract important data points and create a structured overview",
        "Identify patterns and trends in the provided information"
    ]
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "predefined_prompts": sample_prompts}
    )

# File upload endpoint
@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    uploaded_files = []
    
    for file in files:
        if file.filename:
            safe_filename = file.filename.replace(" ", "_").replace("/", "_")
            file_path = uploads_dir / safe_filename
            
            content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            uploaded_files.append(safe_filename)
            debug(f"Uploaded file: {safe_filename} to {file_path}")
    DefaultAgent.local_files_rag_tool._ensure_vs()  # Ensure the index is built or updated after file upload
    return {"message": f"Successfully uploaded {len(uploaded_files)} files", "files": uploaded_files}

# Prompt processing endpoint
@app.post("/process_prompt")
async def process_prompt(prompt: dict):
    prompt_text = prompt.get("text", "")
    debug(f"Processing prompt: {prompt_text}")
    
    # Here you can add your prompt processing logic
    # For now, just return a simple response
    response = f"Processed prompt: '{prompt_text}' - Add your processing logic here"
    
    return {"response": response, "status": "success"}

app.include_router(summary_board_router, prefix = "/summary_board",tags=["summary_board"])
app.mount("/livekit", live_kit_app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000, reload=False)  # Reload for development purposes