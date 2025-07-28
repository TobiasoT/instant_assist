import asyncio
import contextlib

from starlette.staticfiles import StaticFiles

from source.agentic_tasks.agent_pool import AgentPool
from source.agentic_tasks.agent_rater import AgentRater
from source.agentic_tasks.agent_task_wrapper import ListOfAgenticTaskWrappers
from source.agentic_tasks.agentic_tasks_factory import AgenticTasksFactory
from source.chat.message import Message
from source.dev_logger import debug
from fastapi import FastAPI

from source.agentic_tasks.agent_task_wrapper import ListOfAgenticTaskWrappers
from source.agentic_tasks.agentic_tasks_factory import AgenticTasksFactory
from source.chat.message import Message
from source.dev_logger import debug
from source.examples.messages_json import messages_json
from source.locations_and_config import resources_dir, path_static_dir
from source.web_app.app import app
from source.web_app.routers.summary_board.summary_board import summary_board_router

agent_pool = AgentPool()
agent_tasks_factory = AgenticTasksFactory()
agent_rater = AgentRater()

async def fake_messages_input_loop(messages_json, sleep_time=1.5):
	messages_list = Message.create_messages_list_from_list(messages_json = messages_json)
	initial_message = messages_list[0]
	for message in messages_list[1: ]:
		await initial_message.absorb_other_into_messages_stream(other = message)
		await agent_tasks_factory.create_new_agents(message = initial_message)
		await agent_rater.rate_agents(message = initial_message)
		currently_existing_agents = agent_tasks_factory.agent_pool.get_already_existing_tasks()
		agent_pool.make_all_but_most_relevant_inactive()
		await asyncio.sleep(sleep_time)
		debug(f"{len(currently_existing_agents)} agents currently in the pool.")
		debug(f"{len(agent_tasks_factory.agent_pool.get_active_agent_tasks())} active agents currently in the pool.")




if __name__ == "__main__":
	@contextlib.asynccontextmanager
	async def lifespan(app: FastAPI):
		# → startup logic_run
		debug("🟢 Starting update loop…")
	
		loop_task = asyncio.create_task(fake_messages_input_loop(messages_json, 1.0))
		try:
			yield
		finally:
			debug("🔴 Stopping update loop…")
			loop_task.cancel()
			with contextlib.suppress(asyncio.CancelledError):
				await loop_task
	
	import uvicorn
	
	app = FastAPI(title = "Agent Summary Board", lifespan = lifespan)  # ← register it
	app.mount("/static", StaticFiles(directory = path_static_dir), name = "static")
	app.include_router(summary_board_router, prefix = "/summary_board", tags = ["summary_board"])
	
	import uvicorn
	
	uvicorn.run(app, host = "localhost", port = 8000, reload = False)




