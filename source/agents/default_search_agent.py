# Python 3.12
from __future__ import annotations

import traceback
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langgraph.prebuilt import create_react_agent

from source.agentic_tasks.agent_task_wrapper import AgenticTaskWrapper, AgentTaskResult
from source.agentic_tasks.task_status import TaskStatus
from source.agents.tools.local_files_rag_tool import LocalFilesRAGTool
from source.chat.message import Message
from source.dev_logger import debug
from source.global_instances import agents_config
from source.global_models import cached_embeddings, default_cheapest_model
from source.locations_and_config import uploads_dir, quick_access_info


class DefaultAgent:
	# Reuse a single tool instance (it lazy-loads or builds its index as needed)
	local_files_rag_tool = LocalFilesRAGTool(
		data_dir = uploads_dir,
		index_dir = uploads_dir / ".rag_index/faiss",
		embeddings = cached_embeddings,
		allow_unsafe_deser = True,
	)
	
	def __init__(self) -> None:
		self.category_query_llm = default_cheapest_model
	
	# -----------------------------
	# Helpers
	# -----------------------------
	@staticmethod
	def _last_message(messages: Message) -> Message:
		"""Walk to the tail of the linked list of messages."""
		while messages.next_message is not None:
			messages = messages.next_message
		return messages
	
	@staticmethod
	def _needs_agent(result: AgentTaskResult | None) -> bool:
		"""Heuristics to decide if the ReAct agent should run."""
		if result is None:
			return True
		# If your schema uses different attribute names, tweak below:
		# 1) explicit status asking for lookup
		if hasattr(result, "status") and getattr(result, "status") in {
			getattr(TaskStatus, "NEEDS_INFO", None),
			getattr(TaskStatus, "REQUIRES_LOOKUP", None),
		}:
			return True
		# 2) empty/placeholder content
		if hasattr(result, "content"):
			content = getattr(result, "content")
			if content is None:
				return True
			if isinstance(content, str) and not content.strip():
				return True
		# 3) any explicit flag the model may set
		if hasattr(result, "needs_lookup") and bool(getattr(result, "needs_lookup")):
			return True
		return False
	
	def _build_context_prompt(
			self, agentic_task_wrapper: AgenticTaskWrapper, messages: Message
	) -> str:
		"""Compose a compact prompt with prior chat + quick access + task."""
		messages = self._last_message(messages)
		
		parser = PydanticOutputParser(pydantic_object = AgentTaskResult)
		prompt = "You are a careful, precise assistant.\n"
		prompt += "When you cite local files, use bracketed numeric citations like [1], [2].\n"
		prompt += "If you use tools, incorporate their outputs faithfully.\n\n"
		
		# Prior chat context
		prompt += "Context from previous chat:\n"
		prompt += "<chat>\n"
		prompt += messages.get_chat_context(
			minimum_number_of_messages = 50,
			config = agents_config.summarization_config,
		)
		prompt += "\n</chat>\n\n"
		
		# Quick access info (if present)
		if quick_access_info.exists():
			prompt += "Context from quick access info:\n"
			prompt += "<quick_access_info>\n"
			prompt += quick_access_info.read_text()
			prompt += "\n</quick_access_info>\n\n"
		
		# Current task
		prompt += "Current task:\n"
		prompt += f"<query_or_task>{agentic_task_wrapper}</query_or_task>\n\n"
		
		# Output contract
		prompt += "Put your final answer inside <json>...</json> tags.\n"
		prompt += "Your answer must satisfy the following Pydantic schema:\n"
		prompt += parser.get_format_instructions() + "\n"
		return prompt
	
	# -----------------------------
	# Fast path (your original)
	# -----------------------------
	async def quick_result(
			self, agentic_task_wrapper: AgenticTaskWrapper, messages: Message
	) -> AgentTaskResult:
		messages = self._last_message(messages)
		parser = PydanticOutputParser(pydantic_object = AgentTaskResult)
		
		prompt = "You are a concise assistant.\n"
		prompt += "If you can answer without external lookup, do so.\n"
		prompt += "If you need to look up info, return an empty JSON object.\n\n"
		
		prompt += "Context from previous chat:\n"
		prompt += "<chat>"
		prompt += messages.get_chat_context(
			minimum_number_of_messages = 50,
			config = agents_config.summarization_config,
		)
		prompt += "</chat>\n"
		
		if quick_access_info.exists():
			prompt += "Context from quick access info:\n"
			prompt += "<quick_access_info>"
			prompt += quick_access_info.read_text()
			prompt += "</quick_access_info>\n"
		
		prompt += "Context from current task:\n"
		prompt += f"You're given the following query or task: <query_or_task>{agentic_task_wrapper}</query_or_task>.\n"
		prompt += "Put your answer in <json>...</json> tags.\n"
		prompt += "If you think you need to look something up, answer with empty <json></json>.\n"
		prompt += "Your answer must match this schema:\n"
		prompt += parser.get_format_instructions() + "\n"
		
		result = await self.category_query_llm.ainvoke(prompt)
		content: str = result.content.strip()
		json_str = content.split("<json>")[-1].split("</json>")[0].strip()
		parsed = parser.parse(json_str)
		await agentic_task_wrapper.set_result(parsed)
		return parsed
	
	# -----------------------------
	# Agentic path (more precise, allowed to use tools)
	# -----------------------------
	async def agentic_result(
			self, agentic_task_wrapper: AgenticTaskWrapper, messages: Message
	) -> AgentTaskResult:
		parser = PydanticOutputParser(pydantic_object = AgentTaskResult)
		
		# Bind the local-files RAG as a tool
		rag_tool = self.local_files_rag_tool.as_tool()
		
		# Build a ReAct agent over your cheapest model
		agent = create_react_agent(
			model = self.category_query_llm,
			tools = [rag_tool],
			prompt = (
				"You are a precise ReAct agent.\n"
				"Use tools when they can materially improve accuracy.\n"
				"Prefer the LocalFilesRAG tool for any query that might be answered from local documents.\n"
				"When you produce the final answer, it MUST be enclosed in <json>...</json> and conform to the provided schema.\n"
				"Include bracketed citations like [1], [2] when drawing on local files."
			),
		)
		
		# Compose the user-facing prompt that includes schema instructions
		user_prompt = self._build_context_prompt(agentic_task_wrapper, messages)
		
		# Run the agent (it will think/act/call tools as needed)
		agent_result: dict[str, Any] = await agent.ainvoke(
			{"messages": [{"role": "user", "content": user_prompt}]}
		)
		
		# Extract the final assistant message text
		final_text: str = agent_result["messages"][-1].content if isinstance(
			agent_result, dict
		) else str(agent_result)
		
		# Parse to your schema
		try:
			json_str = final_text.split("<json>")[-1].split("</json>")[0].strip()
			parsed = parser.parse(json_str)
			await agentic_task_wrapper.set_result(parsed)
			return parsed

		except Exception as e:
			# Fall back to a minimal error result if parsing fails
			debug("Agent parsing failed: %s", e)
			agentic_task_wrapper.status = TaskStatus.FAILED
	
	
	# -----------------------------
	# Entry point
	# -----------------------------
	async def run(self, agentic_task_wrapper: AgenticTaskWrapper) -> AgentTaskResult:
		try:
			quick = await self.quick_result(
				agentic_task_wrapper, agentic_task_wrapper.message
			)
			if self._needs_agent(quick):
				debug("Escalating to agentic path (needs lookup or empty result).")
				return await self.agentic_result(
					agentic_task_wrapper, agentic_task_wrapper.message
				)
			return quick
		except Exception as e:
			debug(
				"Quick path failed for task %s: %s; falling back to agent.",
				agentic_task_wrapper.query_or_task,
				e,
			)
			traceback.print_exc()
			return await self.agentic_result(
				agentic_task_wrapper, agentic_task_wrapper.message
			)
