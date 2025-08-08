# message_models.py
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Set

from assemblyai.streaming.v3 import TurnEvent
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from source.dev_logger import debug
from source.global_models import default_thinking_model


class AudioStream(BaseModel):
	"""
	Represents an audio stream in a message.
	"""
	# audio_data: bytes = Field(..., description = "The audio data of the stream.") # for later
	start_time_absolute: Optional[datetime] = Field(None, description = "The start time of the audio stream in seconds.")
	
	def __str__(self):
		return f"AudioStream(start_time={self.start_time_absolute})"

class Word(BaseModel):
	"""
	Represents a word in a message.
	"""
	text: str = Field(..., description = "The text of the word.")
	audio_stream: Optional[AudioStream] = Field(None, description = "The audio stream associated with this word. This is used to store the audio data of the word for further processing.")
	start_time: Optional[datetime] = Field(None, description = "The start time of the word ") # ? relative to the audio stream in seconds. ? -> check
	end_time: Optional[datetime] = Field(None, description = "The start time of the word ") # ? relative to the audio stream in seconds. ? -> check
	
	confidence: Optional[float] = Field(None, description = "The confidence score of the word recognition.")
	senders_by_probability: Optional[dict[str, float]] = Field(
		None, description = "A dictionary mapping sender IDs to their probability of being the sender of this word."
	)
	
	def __str__(self):
		return self.text





