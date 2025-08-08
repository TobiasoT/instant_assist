import asyncio
import queue
import traceback
from datetime import datetime
from typing import TypeVar, List, Callable

from source.chat.message import Message
from source.dev_logger import debug
from source.global_instances.custom_assembly_ai_multi_client_factory import global_custom_assembly_ai_multi_client_factory
from source.global_instances.agent_instances import agent_tasks_factory, agent_rater

T = TypeVar("T")


async def drain_queue(q: queue.Queue[T]) -> List[T]:
	"""Remove and return all items currently in the queue."""
	items: List[T] = []
	while True:
		try:
			# Immediately raise queue.Empty if empty
			item = q.get_nowait()
		except queue.Empty:
			break
		else:
			items.append(item)
	return items


async def aget(q: queue.Queue[T]) -> T:
	"""Run q.get() in a thread so the event loop isn’t blocked."""
	return await asyncio.to_thread(q.get)


async def summary_report_filling_loop(drain_queue_before: bool = True) -> None:
	try:
		if drain_queue_before:
			await drain_queue(
				global_custom_assembly_ai_multi_client_factory.messages_queue
			)
		agent_tasks_factory.run_in_loop_task = asyncio.create_task(
			agent_tasks_factory.run_in_loop()
		)
		agent_rater.run_in_loop_task = asyncio.create_task(
	        agent_rater.run_in_loop()
		)
		
		first_message = await aget(global_custom_assembly_ai_multi_client_factory.messages_queue)
		while True:
			new_message = await aget(global_custom_assembly_ai_multi_client_factory.messages_queue)
			debug(f"New message received: {new_message.content_as_string}")
			await first_message.absorb_other_into_messages_stream(
				other = new_message,
				time_distance_to_never_fusion_messages_sec = 5,
				timestamp_of_change = datetime.now()
			)
			first_message = first_message.get_most_recent_message()
			agent_tasks_factory.set_latest_unprocessed_message(first_message)
			agent_rater.set_latest_unprocessed_message(first_message)
	except Exception as e:
		traceback.print_exc()
		raise e


async def fake_summary_report_filling_loop(fake_messages:list[Message], sleep_between:float|None = 1) -> None:
	for index, message in enumerate(fake_messages):
		if not isinstance(message, Message):
			raise TypeError(f"Expected Message instance, got {type(message)} at index {index}")
		assert message is not None
		global_custom_assembly_ai_multi_client_factory.messages_queue.put_nowait(message)
		if sleep_between:
			await asyncio.sleep(sleep_between)
		