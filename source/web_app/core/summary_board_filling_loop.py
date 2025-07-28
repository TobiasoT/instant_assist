import asyncio
import queue
from datetime import datetime
from typing import TypeVar, List

from source.custom_assembly_ai_multi_client import global_custom_assembly_ai_multi_client_factory
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
		first_message = await first_message.absorb_other_into_messages_stream(
			other = new_message,
			time_distance_to_never_fusion_messages_sec = 5,
			timestamp_of_change = datetime.now()
		)
		agent_tasks_factory.set_latest_unprocessed_message(first_message)
		agent_rater.set_latest_unprocessed_message(first_message)
