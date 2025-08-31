import time
from crewai_tools import BraveSearchTool
from pydantic import BaseModel, Field
from typing import Type

# Explicit args schema defining the required `query` parameter.

class BraveSearchInput(BaseModel):
    query: str = Field(..., description="Search query for Brave search")

class ThrottledBraveSearchTool(BraveSearchTool):
    """BraveSearchTool wrapper that sleeps between calls to avoid hitting rate limits."""

    # seconds to wait between consecutive API calls
    _sleep_seconds: float = 1.5

    # Provide the correct args_schema expected by BaseTool / Pydantic
    args_schema: Type[BaseModel] = BraveSearchInput

    def _run(self, **kwargs):
        """Sleep then delegate to parent. Accepts only keyword args as parent expects."""
        time.sleep(self._sleep_seconds)
        return super()._run(**kwargs)
