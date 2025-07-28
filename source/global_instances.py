
import queue
from datetime import datetime
from typing import TypeVar, List
import asyncio
import contextlib
from source.agentic_tasks.agent_pool import AgentPool
from source.agentic_tasks.agent_rater import AgentRater
from source.agentic_tasks.agents_config import AgentsConfig
from source.custom_assembly_ai_multi_client import global_custom_assembly_ai_multi_client_factory
from source.agentic_tasks.agentic_tasks_factory import AgenticTasksFactory



# This file contains global instances that are used throughout the application.
# TODO: this is a temporary solution, we should refactor a more structured approach.


agents_config: AgentsConfig = AgentsConfig()
agent_pool = AgentPool(config=agents_config)
agent_tasks_factory = AgenticTasksFactory(agent_pool=agent_pool, config=agents_config)
agent_rater = AgentRater(agent_pool=agent_pool, config=agents_config)







