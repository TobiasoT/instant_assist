from source.agentic_tasks.agent_pool import AgentPool
from source.agentic_tasks.agent_rater import AgentRater
from source.agentic_tasks.agentic_tasks_factory import AgenticTasksFactory
from source.global_instances.agents_config import agents_config

agent_pool = AgentPool(config=agents_config)
agent_tasks_factory = AgenticTasksFactory(agent_pool=agent_pool, config=agents_config)
agent_rater = AgentRater(agent_pool=agent_pool, config=agents_config)
