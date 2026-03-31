"""Sabotage task definitions module."""

from .definitions import (
    SabotageTask,
    Naturalness,
    TASKS,
    get_task,
    get_tasks_by_naturalness,
    get_all_tasks,
)

__all__ = [
    "SabotageTask",
    "Naturalness", 
    "TASKS",
    "get_task",
    "get_tasks_by_naturalness",
    "get_all_tasks",
]
