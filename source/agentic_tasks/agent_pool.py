# 1) Enum für die Stati
from __future__ import annotations

from typing import TYPE_CHECKING

from source.agentic_tasks.agents_config import AgentsConfig
from source.agentic_tasks.task_status import TaskStatus
if TYPE_CHECKING:
	from source.agentic_tasks.agent_task_wrapper import AgenticTaskWrapper
from source.dev_logger import debug






class AgentPool:
	def __init__(self,  config: AgentsConfig = AgentsConfig()):
		self.config: AgentsConfig = config
		self.agent_tasks: dict[str, AgenticTaskWrapper] = {}
		self.relevant_agent_tasks: set[str] = set()
		self.active_threshold: float = 0.2  # Minimum relevance to consider a task active
		self.maximum_messages_to_keep: int = 1000  # Maximum number of messages to keep in the pool
		
	def make_all_but_most_relevant_inactive(self):
		"""
		Deactivate all but the n most relevant tasks.
		This is useful to keep the pool manageable and focused on the most relevant tasks.
		"""
		active_tasks = self.get_active_agent_tasks(maximum_number = self.config.agent_pool_maximum_messages_to_keep_active,
		                                           cancel_failed = True)
		self.relevant_agent_tasks.clear()
		for task in active_tasks:
			self.relevant_agent_tasks.add(task.query_or_task)
		
	def add_agent_task(self, task: AgenticTaskWrapper):
		"""
		Add a new agent task to the pool.
		If the task already exists, it will be updated.
		"""
		# debug(f"Adding task {task.query_or_task} to the agent pool.")
		self.agent_tasks[task.query_or_task] = task
		
	def sort_into_relevance(self, task: AgenticTaskWrapper):
		if task.is_relevant():
			self.relevant_agent_tasks.add(task.query_or_task)
		else:
			self.relevant_agent_tasks.discard(task.query_or_task)
		
	def get_already_existing_tasks(self):
		debug("Getting already existing tasks from the agent pool.")
		return list(self.agent_tasks.values())
	
	def check_for_duplicate(self, task: AgenticTaskWrapper) -> bool:
		"""
		TODO: use vector store
		:return already_in_pool: bool | AgenticTaskWrapper
		"""
		already_in_pool =  self.agent_tasks.get(task.query_or_task, False)
		if already_in_pool:
			return not (already_in_pool is task)
		return False
	
	def deactivate_failed_tasks(self):
		for relevant_task in self.relevant_agent_tasks:
			task = self.agent_tasks[relevant_task]
			if task.status is TaskStatus.FAILED:
				self.relevant_agent_tasks.discard(relevant_task)
				continue
				
	def deactivate_task(self, task: AgenticTaskWrapper):
		"""
		Deactivate a task and remove it from the relevant tasks.
		"""
		if task.query_or_task in self.relevant_agent_tasks:
			self.relevant_agent_tasks.discard(task.query_or_task)
			task.status = TaskStatus.DEACTIVATED
			debug(f"Task {task.query_or_task} has been deactivated.")
		else:
			debug(f"Task {task.query_or_task} was not found in relevant tasks.")
	
	def get_active_agent_tasks(self, maximum_number: int = int(10e10), cancel_failed: bool = True) -> list[AgenticTaskWrapper]:
		if cancel_failed:
			self.deactivate_failed_tasks()
		remaining_tasks = []
		for task_id in self.relevant_agent_tasks:
			task = self.agent_tasks[task_id]
			if task.is_relevant():
				remaining_tasks.append(task)
		sorted_tasks = sorted(remaining_tasks, key = lambda x: x.relevance, reverse = True)
		return sorted_tasks[:maximum_number]
	
	 


global_agent_pool_instance = AgentPool()

