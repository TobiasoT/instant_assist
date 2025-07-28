# 1) Enum für die Stati
from __future__ import annotations

import asyncio

from langchain_core.exceptions import OutputParserException
from langchain_openai import ChatOpenAI

from source.agentic_tasks.agent_pool import AgentPool, global_agent_pool_instance
from source.agentic_tasks.agent_task_wrapper import ListOfAgenticTaskWrappers, AgenticTaskWrapper
from source.agentic_tasks.agents_config import AgentsConfig
from source.agents.default_search_agent import DefaultAgent
from source.chat.message import Message
from source.dev_logger import debug
from source.global_models import default_thinking_model
from source.web_app.core.summary_board import summary_board


class AgenticTasksFactory:
	def __init__(self,agent_pool: AgentPool =  None,  config: AgentsConfig = AgentsConfig()):
		self.agent_pool: AgentPool = agent_pool or  global_agent_pool_instance
		self.config: AgentsConfig = config
		self.latest_unprocessed_message: Message | None = None
		self.latest_unprocessed_message_event: asyncio.Event = asyncio.Event()
		
	def set_latest_unprocessed_message(self, message: Message):
		self.latest_unprocessed_message = message
		self.latest_unprocessed_message_event.set()
		
	async def run_in_loop(self):
		while True:
			await self.latest_unprocessed_message_event.wait()
			self.latest_unprocessed_message_event.clear()
			debug(f"Creating new agents for message: {self.latest_unprocessed_message.content}")
			await self.create_new_agents(self.latest_unprocessed_message)

	
	async def create_new_agents(self, message: Message, llm: ChatOpenAI = None):
		llm = llm or self.config.get_agent_creation_llm()
		already_existing_tasks = self.agent_pool.get_already_existing_tasks()
		
		prompt = ""
		prompt += (f"you create agent tasks according to the assistance_instructions taking_into_account_the_context_and_the_chat.\n")
		prompt += (f"<assistance_instructions>{self.config.assistant_instructions}</assistance_instructions>\n")
		prompt += (f"<chat>{message.get_chat_context( config = self.config.summarization_config, minimum_number_of_messages = self.config.minimum_number_of_unchanged_messages)}</chat>\n")
		prompt += (f"previously you already have created such tasks. you shall not create duplicates or near duplicates of those tasks. the ones you already have created are:\n")
		prompt += (f"<tasks_not_to_create>{[task.query_or_task for task in already_existing_tasks] if already_existing_tasks else []}</tasks_not_to_create>\n")
		prompt += (f"if you deem it appropriate. you now can create a new task in case you think thumbsting similar does not already exist.\n")
		prompt += (f"your output shall be put into <json> tags in the following form:\n")
		prompt += (f"<json>ResultHere</json>\n")
		prompt += f"ResultHere shall suffice {ListOfAgenticTaskWrappers.get_pydantic_output_parser().get_format_instructions()}\n"
		prompt += (f"")
		
		result = await llm.ainvoke(prompt)
		json_string = result.content.split("<json>")[-1].split("</json>")[0].strip()
		if not json_string:
			return []
		try:
			agent_tasks = ListOfAgenticTaskWrappers.get_pydantic_output_parser().parse(json_string).list_of_tasks
			final_tasks = []
			for task in agent_tasks:
				final_tasks.append(self.finalize_task_non_blocking(task, message = message))
			return final_tasks
		except OutputParserException as e:
			debug(f"Error while parsing agent tasks: {json_string}")
			debug(f"Prompt: {prompt}")
			debug(f"Error: {e}")
			if llm is not default_thinking_model:
				return await self.create_new_agents(message = message, llm = default_thinking_model)
			else:
				raise e
			 
	def finalize_task_non_blocking(self, task: AgenticTaskWrapper, message: Message) -> AgenticTaskWrapper:
		already_in_pool = self.agent_pool.check_for_duplicate(task)
		if already_in_pool:
			return task
		asyncio.create_task( task.finalize_task(agent_pool = self.agent_pool,
		                                       message = message,
		                         callback_result_update = lambda : summary_board.inform_change(agent_pool = self.agent_pool, task = task),
		                         start_running = True,
		                         agent = DefaultAgent()) )
		
		
		
		
		
		
		
		
		