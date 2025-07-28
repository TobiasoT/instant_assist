# message_models.py
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Set, Any

from assemblyai.streaming.v3 import TurnEvent
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from source.dev_logger import debug
from source.global_models import default_thinking_model


class Extraction:
    def __init__(self, id:str, key:str, result:Any, timestamp:datetime =  None) -> None:
        self.id: str = id
        self.key: str = key
        self._result: Any = result
        self.timestamp: datetime = timestamp
        self.lock: asyncio.Lock = asyncio.Lock()
        
    @property
    def result(self) -> Any:
        return self._result
     
    async def set_result(self, result: Any, timestamp: Optional[datetime] = None) -> bool:
        async with self.lock:
            ts = timestamp or datetime.now(timezone.utc)
            if self.timestamp is None or ts >= self.timestamp:
                self._result = result
                self.timestamp = ts
                return True
        return False

class ExtractionState:

    def __init__(self) -> None:
        self.extractions: dict[str, Extraction] = {}
        
        
    async def set_by_key(
        self, key: str, result: Any, timestamp: Optional[datetime] = None
    ) -> bool:
        if key not in self.extractions:
            self.extractions[key] = Extraction(
                id=uuid.uuid4().hex, key=key, result=None)
            
        return await self.extractions[key].set_result(result, timestamp)
    
    def get_by_key(self, key: str) -> Optional[Extraction]:
        return self.extractions.get(key, None)
    
    async def reset_all(self) -> None:
        for key in self.extractions:
            self.extractions[key] = Extraction(
                id=uuid.uuid4().hex, key=key, result=None)
        
        