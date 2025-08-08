# 1) Enum für die Stati
from __future__ import annotations

import asyncio
import datetime
from typing import Callable, Any, List, Literal, TYPE_CHECKING

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, ConfigDict
from pydantic.json_schema import SkipJsonSchema

from source.agentic_tasks.agent_pool import AgentPool
from source.agentic_tasks.task_status import TaskStatus
from source.chat.message import Message
from source.dev_logger import debug
from source.markdown_to_braufiful_html import convert_markdown_to_beautiful_html

if TYPE_CHECKING:
	from source.agents.default_search_agent import DefaultAgent

AllowedTypesOfAnswers = Literal["info", "suggestion", "warning", "error", "other"]

class AgentTaskResult(BaseModel):
	more_info_needed:bool = Field(
		default = False,
		description = "If True, the agent needs more information to complete the task")
	group: AllowedTypesOfAnswers = Field(
		description = "Category of the answer; useful for filtering later."
	)
	title: str = Field(
		description = "Short title summarising the information/suggestion."
	)
	very_short_summary_of_content: str = Field(
		description = "Very short summary—just the key point."
	)
	content: str = Field(
		description = "Full content, in Markdown. Can include tables, links, etc."
	)
	color_circle: tuple[int, int, int] = Field(
		default = (0, 128, 255),
		description = "RGB color tuple for the circle in the UI. Green is you are sure, red is you are not sure. blue is neutral. Values are clamped to [0,255]."
	)
	
	def rgb_to_hex(self, r: int, g: int, b: int) -> str:
		"""
		Convert 8‑bit R, G, B values into a hex color string, e.g. '#A1B2C3'.
		Values out of range are clamped to [0,255].
		"""
		
		def clamp(x: int) -> int:
			return max(0, min(255, x))
		
		r, g, b = clamp(r), clamp(g), clamp(b)
		return f"#{r:02X}{g:02X}{b:02X}"
	
	def rgb_to_css(self, r: int, g: int, b: int, a: float | None = None) -> str:
		"""
		If alpha is None, returns a hex string via rgb_to_hex().
		Otherwise returns 'rgba(r,g,b,a)' suitable for CSS (a will be rounded to 2 decimal places).
		"""
		if a is None:
			return self.rgb_to_hex(r, g, b)
		
		# clamp & format alpha
		def clamp_i(x: int) -> int:
			return max(0, min(255, x))
		
		r, g, b = clamp_i(r), clamp_i(g), clamp_i(b)
		a = max(0.0, min(1.0, a))
		return f"rgba({r},{g},{b},{a:.2f})"
	
	def prepare_json_for_gui(self):
		"""
		Prepare the JSON for the GUI.
		This is a workaround to avoid issues with the Pydantic JSON schema.
		"""
		next = '''# 🚀 Project Stardust

Welcome to **Project Stardust** – a quick demo of Markdown features!

## 🌟 Features

- **Bold text** and *italic text*
- [Clickable links](https://example.com)
- Inline code: `const pi = 3.14`
- Code block with syntax highlighting:

```python
def generate_id(prefix: str, length: int = 8) -> str:
    """
    Generate a random identifier string.
    """
    import random, string
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return f"{prefix}_{suffix}"

print(generate_id("user"))
'''
		html = convert_markdown_to_beautiful_html(next)
		# debug(html)
		return {
			"group": self.group,
			"title": self.title,
			"very_short_summary_of_content":convert_markdown_to_beautiful_html(self.very_short_summary_of_content),
			# "very_short_summary_of_content":html,
			"content": convert_markdown_to_beautiful_html(self.content),
			# "content": convert_markdown_to_beautiful_html(),
			"color_circle": self.rgb_to_css(0, 128, 255, 0.5),
		}
	
	
	


class AgenticTaskWrapper(BaseModel):
	query_or_task: str
	category: str
	relevance_to_instructions: float = Field(default = 0.0, le = 1.0, ge = -1.0,
	                                         description = "Relevance of the task to the instructions. This is a floating value in the range of [1,-1] (1=extremely relevant, -1 not at all relevant). Use whole range, rarely use 1.")
	urgency: float = Field(default = 0.0, le = 1.0, ge = -1.0,
	                       description = "Urgency of the task (== important to do right now). This is a floating value in the range of [1,-1] (1=extremely urgent, -1 not at all urgent). Use whole range, rarely use 1.")
	
	forced_relevance: SkipJsonSchema[float] = Field(default = None, le = 1.0, ge = -1.0,
	                                                description = "Forced relevance of the query to the current context. This is a floating value in the range of [-1,1], where 1 means extremely relevant and urgent, 0 means neutral not urgent, and -1 means not relevant at all. This can be used to override the relevance of the query to the current context.")
	message: SkipJsonSchema[Message] = Field(default = None, exclude = True,
	                                         description = "Message that triggered the task. This is used to store the message that triggered the task, so that it can be used later on to provide context for the task.")
	caption: SkipJsonSchema[str] = Field(default = "", description = "A short caption for the query. This can be used to provide a short description of the query.")
	result: SkipJsonSchema[AgentTaskResult] = Field(default = "", description = "The result of the query, if applicable. This can be used to store the result of the query for later use.")
	intermediate_result: SkipJsonSchema[str] = Field(default = "", description = "The result of the query, if applicable. This can be used to store the result of the query for later use.")
	
	running_tasks: SkipJsonSchema[List[asyncio.Task[Any]]] = Field(default_factory = list, description = "Liste der gerade laufenden asyncio.Tasks")  # right now only 1 task Always.
	
	task_factory: SkipJsonSchema[Callable[[], asyncio.Task[Any]]] = Field(default = None, description = "Fabrik-Funktion zum Erzeugen eines neuen asyncio.Task")
	
	# Callback-Funktion: nimmt das Resultat und liefert eine Coroutine zurück
	callback_result_update: SkipJsonSchema[Callable] = Field(
		default = None, exclude = True, description = ("Callable, das mit dem Task-Result aufgerufen wird und eine Coroutine zurückgibt"), )
	
	time_of_execution: SkipJsonSchema[datetime.datetime] = Field(default = None, description = "Zeitpunkt, zu dem der Task gestartet wurde")
	
	status: SkipJsonSchema[TaskStatus] = Field(default = TaskStatus.PENDING)
	
	agent_pool: SkipJsonSchema[AgentPool] = Field(default = None, exclude = True, description = "AgentTaskPool, in dem der Task gespeichert ist. Wird für die Verwaltung der Tasks verwendet.")
	
	model_config = ConfigDict(use_enum_values = True, arbitrary_types_allowed = True, )
	
	def deactivate (self) -> None:
		self.agent_pool.deactivate_task(self)
	
	async def finalize_task(
			self,
			message: Message,
			agent: DefaultAgent,
			agent_pool: AgentPool,
			callback_result_update: Callable,
			start_running: bool = True
	) -> None:
		# Nun mit Enum-Vergleich
		assert self.status is not TaskStatus.FINISHED, "Task ist bereits finalisiert"
		self.agent_pool = agent_pool
		self.message = message
		self.status = TaskStatus.PENDING
		self.callback_result_update = callback_result_update
		
		self.agent_pool.add_agent_task(self)
		
		def run_task() -> asyncio.Task[Any]:
			# async def run_function(thing):
			# 	debug(f"Running task for {thing.query_or_task}")
			# task = asyncio.create_task(run_function(self))
			task = asyncio.create_task(agent.run(self))
			# Setze den Status direkt auf RUNNING
			self.status = TaskStatus.RUNNING
			
			if self.callback_result_update:
				def _on_done(t: asyncio.Task[Any]):
					try:
						result = t.result()
						asyncio.create_task(self.callback_result_update(result))
					except Exception:
						pass
				
				task.add_done_callback(_on_done)
			
			return task
		
		self.task_factory = run_task
		
		if start_running:
			self.run_task_non_blocking()
	
	def run_task_non_blocking(self) -> None:
		assert self.task_factory is not None, "task_factory muss gesetzt sein"
		self.time_of_execution = datetime.datetime.now()
		task = self.task_factory()
		self.running_tasks.append(task)
	
	@property
	def relevance(self):
		if self.forced_relevance is not None:
			return self.forced_relevance
		return self.relevance_to_instructions
	
	def is_relevant(self) -> bool:
		if self.status == TaskStatus.FAILED:
			return False
		if self.status == TaskStatus.FINISHED or (self.result):
			return self.get_relevance() > self.agent_pool.config.agent_relevance_threshold
		return False

	def get_relevance(self)->float:
		if self.forced_relevance:
			return self.forced_relevance
		return self.relevance_to_instructions*self.urgency
	
	async def set_result(self, result: AgentTaskResult):
		self.result = result
		self.agent_pool.sort_into_relevance(self)
		if self.callback_result_update is not None:
			callback_result = self.callback_result_update()
			if asyncio.iscoroutine(callback_result):
				await callback_result


class ListOfAgenticTaskWrappers(BaseModel):
	list_of_tasks: List[AgenticTaskWrapper]
	
	@classmethod
	def get_pydantic_output_parser(cls):
		return PydanticOutputParser(pydantic_object = cls)
	
	def to_pretty_markdown(self) -> str:
		if not self.list_of_tasks:
			return "No relevant category queries found."
		result = "# Most Relevant Category Queries\n\n"
		for category_query in self.list_of_tasks:
			result += f"## {category_query.category}\n"
			result += f"- **Query/Task:** {category_query.query_or_task}\n"
			result += f"- **Relevance:** {category_query.relevance_to_instructions:.2f}\n"
			result += f"- **Urgency:** {category_query.urgency:.2f}\n"
			if not hasattr(category_query, "result") or category_query.result is None:
				continue
			if category_query.result:
				result += f"- **Result:** {category_query.result}\n"
			else:
				result += "- **Result:** No result yet.\n"
		return result.strip()
