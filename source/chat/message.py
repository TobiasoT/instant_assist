# message_models.py
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Callable, TYPE_CHECKING

from assemblyai.streaming.v3 import TurnEvent
from pydantic import BaseModel, Field

from source.chat.extraction_state import ExtractionState
if TYPE_CHECKING:
	from source.chat.summary_of_previous_chat import SummaryOfPreviousChat, SummaryOfPreviousChatConfig
from source.chat.word import Word, AudioStream


async_global_messages_change_lock: asyncio.Lock = asyncio.Lock()

class Message(BaseModel):
	time_start: datetime
	time_end: Optional[datetime] = None
	conversation_id: str
	sender: str
	content_as_string: str
	words: List[Word] = Field(default_factory = list,
	                          description = "Words in the message.")
	
	previous_message: Optional[Message] = None
	next_message: Optional[Message] = None
	
	# created_infos: SingleMessageInfoList | None = None
	extraction: ExtractionState = Field(default_factory = ExtractionState, exclude = True)
	
	class Config:
		arbitrary_types_allowed = True
	
	@property
	def content(self) -> str:
		if self.words:
			self.content_as_string = " ".join(w.text for w in self.words)
		return self.content_as_string
	
	@classmethod
	def from_assembly_ai(
			cls,
			event: TurnEvent,
			speaker: str,
			conversation_id: str,
			audio_stream: Optional[AudioStream] = None,
	) -> Message:
		start_of_stream = (audio_stream.start_time_absolute if audio_stream and audio_stream.start_time_absolute else datetime.now(timezone.utc))
		start_ms = getattr(event, "audio_start_ms", 0)
		end_ms = getattr(event, "audio_end_ms", 0)
		words: List[Word] = []
		for w in getattr(event, "words", []):
			words.append(Word(
				text = w.text,
				audio_stream = audio_stream,
				start_time = start_of_stream + timedelta(milliseconds = w.start),
				end_time = start_of_stream + timedelta(milliseconds = w.end),
				confidence = w.confidence,
				senders_by_probability = None,
			))
		content = event.transcript or " ".join(w.text for w in words)
		time_start = start_of_stream + timedelta(milliseconds = start_ms)
		time_end = start_of_stream + timedelta(milliseconds = end_ms)
		return cls(
			time_start = time_start,
			time_end = time_end,
			conversation_id = conversation_id,
			sender = speaker,
			content_as_string = content,
			words = words,
		)
	
	def reset_extraction(self) -> None:
		"""Reset all extraction flags to False."""
		self.extraction.reset_all()
	
	async def set_infos_extracted(self, value: bool, timestamp: Optional[datetime] = None) -> bool:
		return await self.extraction.set_by_key(key = "infos_extracted", result = value, timestamp = timestamp)
	
	async def set_queries_extracted(self, value: bool, timestamp: Optional[datetime] = None) -> bool:
		return await self.extraction.set_by_key(key = "queries_extracted", result = value, timestamp = timestamp)
	
	async def set_summary(self, summary: SummaryOfPreviousChat, timestamp: Optional[datetime] = None):
		return await self.extraction.set_by_key(key = summary.config.config_id(), result = summary.summary, timestamp = timestamp)
		
	def get_summary(self, config: SummaryOfPreviousChatConfig)  -> Optional[SummaryOfPreviousChat]:
		""""""
		extraction = self.extraction.get_by_key(config.config_id())
		if extraction and extraction.result:
			return SummaryOfPreviousChat(summary = extraction.result, config = config)
		return None
		
	def get_summary_and_chat(self, config: SummaryOfPreviousChatConfig,
	                         minimum_numbers_of_messages: int = 5,
	                         break_condition: Callable[[Message], bool] = lambda m: False)-> tuple[Optional[SummaryOfPreviousChat], list[Message]]:
		minimum_messages = []
		current_number_of_messages = 0
		current = self
		while current:
			if minimum_numbers_of_messages >= current_number_of_messages:
				current_number_of_messages += 1
				break
			minimum_messages.append(current)
		
		first_potential_summary_message = minimum_messages[0].previous_message if minimum_messages else self
		
		chat = first_potential_summary_message.get_messages_until_condition( break_condition = lambda m: m.get_summary(config = config) is not None or break_condition(m), included = True		)
		if chat and (summary := chat[0].get_summary(config = config)) is not None:
			return summary, chat[1:]+minimum_messages
		else:
			return None, chat+minimum_messages
		
	def get_chat_context(self, config: SummaryOfPreviousChatConfig,
	                     minimum_number_of_messages: int = 5,
	                     break_condition: Callable[[Message], bool] = lambda m: False) -> str:
		summary, chat = self.get_summary_and_chat(config = config, minimum_numbers_of_messages = minimum_number_of_messages, break_condition = break_condition)
		prompt = f"<summary_of_previous_chat>{summary.summary if summary else 'No summary available'}</summary_of_previous_chat>\n"
		prompt += "<chat_messages_following_summary>\n"
		prompt += "\n".join([
			f"{msg.sender}: {msg.content_as_string}" for msg in chat
		])
		prompt += "</chat_messages_following_summary>\n"
		return prompt
	
	def get_most_recent_message(self):
		current = self
		while current.next_message:
			current = current.next_message
		return current
		
	async def absorb_other_into_messages_stream(self, other: Message, time_distance_to_never_fusion_messages_sec: float = 5, timestamp_of_change: Optional[datetime] = None) -> None:
		async with async_global_messages_change_lock:
			await self._absorb_other_into_messages_stream(other = other, time_distance_to_never_fusion_messages_sec = time_distance_to_never_fusion_messages_sec, timestamp_of_change = timestamp_of_change)
	
	async def _absorb_other_into_messages_stream(self, other: Message, time_distance_to_never_fusion_messages_sec: float, timestamp_of_change: Optional[datetime]) -> None:
		if self.time_start and other.time_start and self.time_start > other.time_start:
			if self.previous_message:
				await self.previous_message._absorb_other_into_messages_stream(other = other, time_distance_to_never_fusion_messages_sec = time_distance_to_never_fusion_messages_sec, timestamp_of_change = timestamp_of_change)
			await other._absorb_other_into_messages_stream(self, time_distance_to_never_fusion_messages_sec = time_distance_to_never_fusion_messages_sec, timestamp_of_change = timestamp_of_change)
		elif other.sender != self.sender or (self.time_end and other.time_start and (other.time_start - self.time_end).total_seconds() > time_distance_to_never_fusion_messages_sec):
			self.next_message = other
			other.previous_message = self
			await self.extraction.reset_all()
		else:
			self.words.extend(other.words)
			self.time_start = min(self.time_start, other.time_start)
			self.time_end = max(self.time_end, other.time_end) if self.time_end and other.time_end else (self.time_end or other.time_end)
			await self.extraction.reset_all()

	def get_messages_until_condition(self, break_condition: Callable[[Message], bool], included:bool) -> List[Message]:
		"""
		Get all messages until the condition is met.
		The condition should be a callable that takes a Message and returns True if the condition is met.
		"""
		messages = []
		current = self
		while current:
			if break_condition(current):
				if included:
					messages.append(current)
				break
			messages.append(current)
			current = current.previous_message
		return messages[::-1]
	
	
	@classmethod
	def create_messages_list_from_list(self, messages_json : list[dict[str, str]]) -> List[Message]:
		"""
		Create a list of Message objects from a list of dictionaries.
		Each dictionary should have 'time_start', 'time_end', 'conversation_id', 'sender', and 'content_as_string' keys.
		"""
		messages = []
		for item in messages_json:
			message = Message(
				time_start=datetime.now(timezone.utc) if "time_start" not in item else datetime.fromisoformat(item["time_start"]),
				time_end=datetime.now(timezone.utc) if "time_end" not in item else datetime.fromisoformat(item["time_end"]) if item["time_end"] else None,
				conversation_id=item.get("conversation_id", "default_conversation_id"),
				sender=item.get("speaker", "unknown_sender"),
				content_as_string=item.get("message", ""),
			)
			messages.append(message)
		return messages

# Resolve forward references
Message.model_rebuild()
