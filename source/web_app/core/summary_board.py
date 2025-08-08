
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from source.agentic_tasks.agent_pool import AgentPool
from source.agentic_tasks.agent_task_wrapper import AgentTaskResult, AgenticTaskWrapper


class SummaryBoard:
	def __init__(self) -> None:
		self._clients: set[WebSocket] = set()
		self._last_results: list[dict] = []
	
	async def connect(self, ws: WebSocket) -> None:
		await ws.accept()
		self._clients.add(ws)
		if self._last_results:
			await ws.send_json(self._last_results)
	
	def disconnect(self, ws: WebSocket) -> None:
		self._clients.discard(ws)

	async def _broadcast(self, results: list[AgentTaskResult]) -> None:
		payload = [r.prepare_json_for_gui() for r in results]
		self._last_results = payload
		stale: set[WebSocket] = set()
		for ws in self._clients:
			try:
				await ws.send_json(payload)
			except WebSocketDisconnect:
				stale.add(ws)
		self._clients -= stale
	 

	def inform_change(self, agent_pool: AgentPool, task: AgenticTaskWrapper = None) -> None:
		top_active_queries = agent_pool.get_active_agent_tasks(maximum_number = 6)
		stuff_to_add = []
		for agent_query in top_active_queries:
			if agent_query.result:
				stuff_to_add.append(agent_query.result)
		stuff_to_add.sort(key = lambda x: ord(x.group[0]))
		asyncio.create_task(self._broadcast(stuff_to_add))
		
		
		
		
summary_board = SummaryBoard()
#





