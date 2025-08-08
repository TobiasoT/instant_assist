from __future__ import annotations

from enum import Enum

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel
from pydantic.json_schema import SkipJsonSchema

from source.chat.summary_of_previous_chat import SummaryOfPreviousChatConfig
from source.global_models import default_cheapest_model

class PossibleAiModels(str, Enum):
	default_cheapest_model = "default_cheapest_model"
	default_thinking_model = "default_thinking_model"


class AgentsConfig(BaseModel):
	summarization_config: SkipJsonSchema[SummaryOfPreviousChatConfig] = SummaryOfPreviousChatConfig()
	minimum_number_of_unchanged_messages: int = 5
	agent_creation_llm: PossibleAiModels = PossibleAiModels.default_cheapest_model
	agent_rating_llm: PossibleAiModels = PossibleAiModels.default_cheapest_model
	assistant_instructions: str = None
	agent_relevance_threshold: float = 0.2
	agent_destruction_threshold: float = 0.2  # Minimum relevance to consider a task active
	agents_number_shown_to_rater: int= 30
	agents_number_shown_to_creater:int= 30
	agent_pool_maximum_messages_to_keep_active: int = 50  # Maximum number of messages to keep in the pool
	
	class Config:
		arbitrary_types_allowed = True
	
	
	def _get_llm_by_string(self, llm:str) -> BaseChatModel:
		if llm == PossibleAiModels.default_cheapest_model:
			return default_cheapest_model
		elif llm == PossibleAiModels.default_thinking_model:
			return default_cheapest_model
		else:
			raise ValueError(f"Unknown LLM type: {self.agent_creation_llm}. Please use one of the defined PossibleAiModels.")
	
	def get_agent_creation_llm(self) -> BaseChatModel:
		return self._get_llm_by_string(self.agent_creation_llm)
	
	def get_agent_rating_llm(self) -> BaseChatModel:
		return self._get_llm_by_string(self.agent_rating_llm)
	
	def set_assistant_instructions(self, instructions: str):
		self.assistant_instructions = instructions
		self.summarization_config.prompt = instructions

