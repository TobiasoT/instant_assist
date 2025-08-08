import asyncio
from typing import Type

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from source.agentic_tasks.agent_pool import AgentPool, global_agent_pool_instance
from source.agentic_tasks.agent_task_wrapper import AgenticTaskWrapper
from source.chat.message import Message

from source.agentic_tasks.agent_pool import AgentPool, global_agent_pool_instance
from source.agentic_tasks.agents_config import AgentsConfig
from source.dev_logger import debug


class AgentRater:
	def __init__(self, agent_pool: AgentPool =  None, config: AgentsConfig = AgentsConfig()):
		self.agent_pool: AgentPool = agent_pool or global_agent_pool_instance
		self.config: AgentsConfig = config
		self.latest_unprocessed_message: Message | None = None
		self.latest_unprocessed_message_event: asyncio.Event = asyncio.Event()
		self.latest_unprocessed_message_event.clear()
		
	def set_latest_unprocessed_message(self, message: Message):
		"""
		Set the latest unprocessed message and notify the loop to process it.
		"""
		self.latest_unprocessed_message = message
		self.latest_unprocessed_message_event.set()
		debug(message.content_as_string)
		
	async def run_in_loop(self):
		while True:
			await self.latest_unprocessed_message_event.wait()
			self.latest_unprocessed_message_event.clear()

			debug(f"Creating new agents for message: {self.latest_unprocessed_message.content}")
			await self.rate_agents(self.latest_unprocessed_message)
		

	@classmethod
	def get_output_schema(cls)-> Type[BaseModel]:
		"""
		Returns the output schema for the rerating function.
		"""
		field_info_relevance = AgenticTaskWrapper.model_fields.get("relevance_to_instructions")
		field_info_urgency = AgenticTaskWrapper.model_fields.get("urgency")
		assert not (field_info_relevance is None or field_info_urgency is None), "Relevance and urgency fields must be defined in AgentTaskQuery model."
		class OutputSchemaSingle(BaseModel):
			task_index: int
			relevance_to_instructions: float =  Field(default = 0.0,description = getattr(field_info_relevance, "description", "Relevance of the task to the current context."))
			urgency: float = Field(default = 0.0, description = getattr(field_info_urgency, "description", "Urgency of the task in the current context."))
		class ListOfAgentTaskQuery(BaseModel):
			agent_queries: list[OutputSchemaSingle] = Field(
				default_factory = list,
				description = "List of agent tasks with their relevance and urgency scores."
			)
		return ListOfAgentTaskQuery
	
	
	async def rate_agents(self, message: Message,  llm=None) -> list:
		"""
		Rerate agents based on their relevance and return a list of active agents.
		"""
		
		# create the schema for the lmm parsing
		field_info_relevance = AgenticTaskWrapper.model_fields.get("relevance_to_instructions")
		field_info_urgency = AgenticTaskWrapper.model_fields.get("urgency")
		assert not (field_info_relevance is None or field_info_urgency is None), "Relevance and urgency fields must be defined in AgentTaskQuery model."
		class OutputSchemaSingle(BaseModel):
			task_index: int
			relevance_to_instructions: float =  Field(default = 0.0,description = getattr(field_info_relevance, "description", "Relevance of the task to the current context."))
			urgency: float = Field(default = 0.0, description = getattr(field_info_urgency, "description", "Urgency of the task in the current context."))
		class ListOfAgentTasks(BaseModel):
			agent_queries: list[OutputSchemaSingle] = Field(
				default_factory = list,
				description = "List of agent tasks with their relevance and urgency scores."
			)
		parser = PydanticOutputParser(pydantic_object = ListOfAgentTasks)
		
		#--------
		llm = llm or self.config.get_agent_rating_llm()
		active_agents = self.agent_pool.get_active_agent_tasks(
			maximum_number=self.config.agents_number_shown_to_rater,
			cancel_failed=True
		)
		prompt = ""
		prompt += (f"you now are supposed to rate how relevant the following tasks are to the current conext instructions:\n")
		prompt += (f"<tasks>\n")
		prompt += (f"{[(str(index)+ ": " + task.query_or_task) for index, task in enumerate(active_agents)] if active_agents else []}\n")
		prompt += (f"</tasks>\n")
		
		prompt += (f"<assistance_instructions>{self.config.assistant_instructions}</assistance_instructions> (be aware that,"
		           f" when the instructions tell you, e.g. provide 3 actionable steps, that means all steps more than 3 will have 0 urgency.\n")
		prompt += (f"Here is the chat you need for rating:\n<chat>{message.get_chat_context( config = self.config.summarization_config, minimum_number_of_messages = self.config.minimum_number_of_unchanged_messages)}</chat>\n")

		
		prompt += (f" you now are supposed to give me a list of of python object representing relevance and urgency.\n")
		prompt += (f"the output should be in the following form:\n")
		prompt += (f"<json>\n")
		prompt += (f"RESULT\n")
		prompt += (f"</json>\n"
		           f"RESULT shale have the following structure:\n"
		           f"{parser.get_format_instructions()}\n")
		prompt += (f"you may think first (only very shortly because of latency). Put your thinking into <thinking>...</thinking> tag. the result in <json>...</json> tag.\n")
		
		result = await llm.ainvoke(prompt)
		if isinstance(result.content, list):
			parsing_content = result.content[ - 1].split("<json>")[-1].split("</json>")[0].strip()
		else:
			parsing_content = result.content.split("<json>")[-1].split("</json>")[0].strip()
		try:
			parsed_results = parser.parse(parsing_content).agent_queries
			for task in parsed_results:
				agent = active_agents[task.task_index]
				agent.relevance_to_instructions = task.relevance_to_instructions
				agent.urgency = task.urgency
				if agent.relevance < self.config.agent_destruction_threshold:
					agent.deactivate()
				
		except OutputParserException as e:
			debug(f"Error while parsing agent tasks: {parsing_content}")
			debug(f"Prompt: {prompt}")
			debug(f"Error: {e}")
			if llm is not self.config.get_agent_rating_llm():
				return await self.rate_agents(message=message,  llm=self.config.get_agent_rating_llm())
			else:
				raise e
			
		
		
		









