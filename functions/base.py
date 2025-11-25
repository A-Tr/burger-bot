"""Base interface for agent functions."""

from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams


class AgentFunction(ABC):
    """Base interface for agent functions.

    Each agent function consists of:
    - A schema that defines the function signature for the LLM
    - A handler that processes the function call and returns a response
    """

    @abstractmethod
    def get_schema(self) -> FunctionSchema:
        """Get the function schema for LLM registration.

        Returns:
            FunctionSchema defining the function's name, description, and parameters
        """
        pass

    @abstractmethod
    def get_handler(self) -> Callable[[FunctionCallParams], Awaitable[str]]:
        """Get the handler function for processing function calls.

        Returns:
            Async function that takes FunctionCallParams and returns a string response
        """
        pass

    @property
    def name(self) -> str:
        """Get the function name from the schema."""
        return self.get_schema().name
