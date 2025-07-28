from source.agentic_tasks.agent_pool import AgentPool
from source.agentic_tasks.agent_rater import AgentRater
from source.agentic_tasks.agent_task_wrapper import ListOfAgenticTaskWrappers
from source.agentic_tasks.agentic_tasks_factory import AgenticTasksFactory
from source.chat.message import Message
from source.dev_logger import debug

agent_pool = AgentPool()
agent_tasks_factory = AgenticTasksFactory()
agent_rater = AgentRater()


async def test_new_agent_creation( messages_json : list[dict[str, str]]):
	messages_list = Message.create_messages_list_from_list(messages_json = messages_json)
	initial_message = messages_list[0]
	for message in messages_list[1:]:
		await initial_message.absorb_other_into_messages_stream(other = message)
		await agent_tasks_factory.create_new_agents(message = initial_message)
		await agent_rater.rate_agents(message = initial_message)
		currently_existing_agents = agent_tasks_factory.agent_pool.get_already_existing_tasks()
		# debug(ListOfAgenticTaskWrappers(list_of_tasks = currently_existing_agents).to_pretty_markdown())
		await asyncio.sleep(1)
		debug(f"{len(currently_existing_agents)} agents currently in the pool.")
		debug(f"{len(agent_tasks_factory.agent_pool.get_active_agent_tasks())} active agents currently in the pool.")






if __name__ == "__main__":
	import asyncio
	import json
	
	assistant_instructions = "I am tom. I am salesperson that wants to sell solar roofs to customers jerry. Please provide me with information that helps me to sell solar roofs to jerry. You may also provide tips what to ask next."
	
	messages_json = [
		{
			"speaker": "Jerry",
			"message": "Hi Tom, thanks for taking the time to meet with me today. I’ve been looking into solar solutions, and I’m particularly interested in a solar roof for my home. By the way, I love Beethoven."
		},
		{
			"speaker": "Tom",
			"message": "Absolutely, Jerry. I’m glad you reached out. Let’s start with what’s driving your interest in a solar roof—are you primarily focused on lowering your energy bills, reducing your carbon footprint, or both?"
		},
		{
			"speaker": "Jerry",
			"message": "A bit of both, actually. I’ve read that solar roofs can generate enough electricity to cover most of a household’s needs, and I want to take advantage of that. Plus, I don’t want to worry about noisy panels sticking up on my shingles—I like the sleek look of an integrated solar roof."
		},
		{
			"speaker": "Tom",
			"message": "That makes sense. Our solar roofs use high-efficiency photovoltaic tiles that look just like traditional roofing materials, so there’s no bulky rack-mounted system. They blend in seamlessly, and they’re backed by a 25-year warranty for both power output and weatherproofing."
		},
		{
			"speaker": "Jerry",
			"message": "That warranty sounds reassuring. Can you tell me more about the tile efficiency and overall expected output?"
		},
		{
			"speaker": "Tom",
			"message": "Of course. Each solar tile has an efficiency of about 22–23%, which is on par with top-tier solar panels. For an average 2,000 ft² roof in Berlin receiving roughly 1,000 kWh/m²/year of solar irradiance, you can expect around 5,000 kWh of annual generation. That typically covers 80–90% of a household’s consumption, depending on your usage patterns."
		},
	]
	asyncio.run(test_new_agent_creation(messages_json = messages_json))









