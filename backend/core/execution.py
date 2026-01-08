from __future__ import annotations

from typing import Any, Dict, TypeVar, Callable
from langgraph.graph import StateGraph

T = TypeVar('T')


class GraphExecutor:
    """Generic graph executor cho mọi domain"""
    
    @staticmethod
    def execute(
        graph: StateGraph,
        init_state: Dict[str, Any],
        to_result: Callable[[Dict[str, Any]], T]
    ) -> T:
        """Execute graph và convert state sang result"""
        final_state = graph.invoke(init_state)
        return to_result(final_state)


