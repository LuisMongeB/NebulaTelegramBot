# cost_tracker.py
import time
from typing import Any, Dict, List, Optional

from langchain_core.callbacks import StdOutCallbackHandler


class CostTracker(StdOutCallbackHandler):
    """Cost tracker for LangChain LLMs that tracks costs per node"""

    def __init__(self, model_name="gpt-4o-mini"):
        self.model_name = model_name
        self.start_time = time.time()
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0
        self.calls = 0

        # Track costs per node
        self.node_costs = {}
        self.current_node = None

        # Set pricing based on model
        self.pricing = {
            "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
            "gpt-4o": {"prompt": 0.0005, "completion": 0.0015},
            "gpt-4": {"prompt": 0.00075, "completion": 0.0045},
        }
        self.model_pricing = self.pricing.get(
            model_name, {"prompt": 0.0001, "completion": 0.0002}
        )

    def set_current_node(self, node_name):
        """Set the current node name"""
        self.current_node = node_name
        if node_name not in self.node_costs:
            self.node_costs[node_name] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0,
                "calls": 0,
            }

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Called when LLM starts running."""
        self.calls += 1
        if self.current_node:
            self.node_costs[self.current_node]["calls"] += 1

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when LLM ends running."""
        # Extract token usage from response
        if hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})

            # Get token counts
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            completion_tokens = token_usage.get("completion_tokens", 0)

            # Update global counters
            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.total_tokens += prompt_tokens + completion_tokens

            # Calculate cost
            prompt_cost = prompt_tokens * self.model_pricing["prompt"] / 1000
            completion_cost = (
                completion_tokens * self.model_pricing["completion"] / 1000
            )
            call_cost = prompt_cost + completion_cost
            self.total_cost += call_cost

            # Update node-specific counters if we have a current node
            if self.current_node:
                node_data = self.node_costs[self.current_node]
                node_data["prompt_tokens"] += prompt_tokens
                node_data["completion_tokens"] += completion_tokens
                node_data["total_tokens"] += prompt_tokens + completion_tokens
                node_data["cost"] += call_cost

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary"""
        duration = time.time() - self.start_time

        # Format node costs
        formatted_node_costs = {}
        for node, data in self.node_costs.items():
            formatted_node_costs[node] = {
                "cost": f"${data['cost']:.6f}",
                "prompt_tokens": data["prompt_tokens"],
                "completion_tokens": data["completion_tokens"],
                "total_tokens": data["total_tokens"],
                "calls": data["calls"],
            }

        return {
            "model": self.model_name,
            "total_cost": f"${self.total_cost:.6f}",
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "calls": self.calls,
            "duration_seconds": f"{duration:.2f}",
            "cost_per_node": formatted_node_costs,
        }
