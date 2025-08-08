from __future__ import annotations

from asyncio import Lock
from typing import Annotated

from dataclasses_json import global_config
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from source.dev_logger import debug
from source.global_instances.agents_config import global_agents_config

# In-memory preset store
_PRESET_LIMIT = 20
prompts: list[str] = [
    "Identify key features, benefits, and drawbacks of various solar roof options.",
    "Summarize the main points and provide 3 actionable next steps.",
]
prompts_lock = Lock()

def _update_prompts(new_prompt: str) -> list[str]:
    """Move prompt to front, dedupe, cap length."""
    new = new_prompt.strip()
    debug(new)
    global_agents_config.set_assistant_instructions(new)
    debug(new)
    if not new:
        return prompts
    # move-to-front dedupe
    items = [new] + [p for p in prompts if p != new]
    return items[:_PRESET_LIMIT]


class PromptIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


class PromptList(BaseModel):
    prompts: list[str]









