from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
	PENDING = "pending"
	RUNNING = "running"
	FINISHED = "finished"
	FAILED = "failed"
	DEACTIVATED = "deactivated"
