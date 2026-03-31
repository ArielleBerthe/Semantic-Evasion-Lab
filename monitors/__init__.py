"""Monitors module - LLM-based code review monitors."""

from .base import BaseMonitor, MonitorResult
from .claude_monitor import ClaudeMonitor, claude_sonnet_monitor, claude_haiku_monitor
from .openai_monitor import OpenAIMonitor, gpt4o_monitor, gpt4o_mini_monitor
from .prompts import get_monitor_prompt, format_prompt

__all__ = [
    # Base
    "BaseMonitor",
    "MonitorResult",
    
    # Claude
    "ClaudeMonitor",
    "claude_sonnet_monitor",
    "claude_haiku_monitor",
    
    # OpenAI
    "OpenAIMonitor", 
    "gpt4o_monitor",
    "gpt4o_mini_monitor",
    
    # Prompts
    "get_monitor_prompt",
    "format_prompt",
]


def get_monitor(monitor_id: str, **kwargs):
    """
    Factory function to get a monitor by ID.
    
    Args:
        monitor_id: One of "claude-sonnet", "claude-haiku", "gpt-4o", "gpt-4o-mini"
        **kwargs: Additional arguments passed to monitor constructor
        
    Returns:
        Configured monitor instance
    """
    monitors = {
        "claude-sonnet": lambda: ClaudeMonitor(model="claude-sonnet-4-5-20250514", **kwargs),
        "claude-haiku": lambda: ClaudeMonitor(model="claude-haiku-4-5-20251001", **kwargs),
        "gpt-4o": lambda: OpenAIMonitor(model="gpt-4o", **kwargs),
        "gpt-4o-mini": lambda: OpenAIMonitor(model="gpt-4o-mini", **kwargs),
    }
    
    if monitor_id not in monitors:
        raise ValueError(f"Unknown monitor: {monitor_id}. Available: {list(monitors.keys())}")
    
    return monitors[monitor_id]()
