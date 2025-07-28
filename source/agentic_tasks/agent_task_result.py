

import asyncio
import datetime
from enum import Enum
from typing import Callable, Coroutine, Any, List

from pydantic import BaseModel, Field, ConfigDict
from pydantic.json_schema import SkipJsonSchema


class AllowedTypesOfAnswers(Enum):
	SUGGESTION_WHAT_TO_DO = "Suggestion for action"
	INFORMATION = "Information"


class AgentTaskQueryResult(BaseModel):
	group: AllowedTypesOfAnswers = Field(description = "Group of the query. This can be used to categorize the query and to filter it later on.")
	title: str = Field(description = "key points from the content (very short, less than 7 Words!) that are a short statement derived from the content and provide the most important facts (no complete sentences)",
	                   )
	very_short_summary_of_content: str = Field(
		description = "Very short summary of the content, only the most important information", )
	content: str = Field(
		description = "Content of the information/suggestion, can be longer than the summary",
	)
	
	model_config = ConfigDict(use_enum_values = True)
