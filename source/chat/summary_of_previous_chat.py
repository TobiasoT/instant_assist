# message_models.py
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from hashlib import md5
from typing import Optional, List, Set, Any

from assemblyai.streaming.v3 import TurnEvent
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from source.chat.message import Message
from source.dev_logger import debug
from source.global_models import default_thinking_model



class SummaryOfPreviousChatConfig(BaseModel):
	max_length_words: int = Field(
		1000,
		description="Maximum number of words to include in the summary of previous chats."
	)
	user_intent: str = Field(
		"Please summarize the previous chat messages in a concise manner, focusing on key points and important information.",
		description="Prompt to guide the summarization of previous chat messages."
	)
	prompt: str = Field(
		default =  None,
		description="Prompt to guide the summarization of previous chat messages."
	)
	
	def config_id(self) -> str:
		return f"summary_{self.max_length_words}_{md5(self.user_intent.encode()).hexdigest()}"
		# return f"summary_of_previous_chat_{self.max_length_words}_{self.user_intent}"
	
	async def get_summarization_instructions(self)->str:
		if self.prompt is not None:
			return self.prompt
		prompt = ""
		prompt += "a user has instructions for an AI assistant to provide him/her with live assistance during a chat.\n"
		prompt += f"the user has the following instructions for the AI assistant <user_intent>{self.user_intent}</user_intent>\n"
		prompt += (" the AI assistant will get the chat messages to perform it. in order to keep the prompts the AI assistant gets short,"
		           f" the AI assistant gets a summary of the chat which has at maximum {self.max_length_words}. What I like you to to create instructions for me and watch to focus when creating the summary .\n")
		prompt += " put your final instructions into <summarization instructions></summarization instructions> tags.\n"
		result = await default_thinking_model.ainvoke(prompt)
		instructions = result.content.split("<summarization instructions>")[-1].split("</summarization instructions>")[0].strip()
		
		self.prompt = instructions
		return instructions
		


class SummaryOfPreviousChat:
	def __init__(self, summary: str, config: SummaryOfPreviousChatConfig):
		self.summary: str = summary
		self.config: SummaryOfPreviousChatConfig = config
		pass
	
	@classmethod
	async def create(cls, message_to_fill: Message, config: SummaryOfPreviousChatConfig  ) -> SummaryOfPreviousChat |  None:
		if summary:= message_to_fill.get_summary(config = config) is not None:
			return summary
		previous_summary_instance, messages_without_summary = message_to_fill.get_summary_and_chat(config = config)
		
		not_summarized_chat = "\n".join(
			f"{msg.sender}: {msg.content_as_string}" for msg in messages_without_summary
		)
		
		if previous_summary_instance is not None:
			previous_summary = previous_summary_instance.summary
		else:
			previous_summary = " no previous chat and therefore no summary available"
		
		prompt = " i want you to create a summarization of a chat:\n"
		prompt += (f"Previous chat messages:\n"
		           f"<new_chat_messages>{not_summarized_chat}</new_chat_messages>\n\n")
		prompt += f"<summarization of chat prior to new chat messages>{previous_summary}</summarization of chat prior to new chat messages>\n"
		
		prompt += (f" the summarization you create should at maximum the {config.max_length_words} words long."
		           f" keep as much information from the old summary as possible and update it to contain the information from the new chat messages. further more adhere also to the following instructions:\n"
		           f"<further summarization instructions>{await config.get_summarization_instructions()}</further summarization instructions>\n"
		           f" put your final summary into <summary_of_previous_chat></summary_of_previous_chat> tags. in case you do not think there is information worth being summarized in the new chat messages,"
		           f" just return <summary_of_previous_chat>None</summary_of_previous_chat>\n")
			
		llm_result = await default_thinking_model.ainvoke(prompt)
		content = llm_result.content
		summary = content.split("<summary_of_previous_chat>")[-1].split("</summary_of_previous_chat>")[0].strip()
		if summary.lower() != "none" or len(summary.strip()) > 20:
			summary_instance = SummaryOfPreviousChat(summary=summary, config=config)
			await message_to_fill.set_summary(summary=summary_instance, timestamp=datetime.now(timezone.utc))
		else:
			return None






