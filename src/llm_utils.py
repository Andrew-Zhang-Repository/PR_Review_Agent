"""
Utility functions for LLM providers.
"""

from typing import Any
from src.model_select import OllamaProvider



def initialize_llm_provider(model_name: str) -> Any:
    """
    Initialize the appropriate LLM provider based on the model name.

    Args:
        model_name: The name of the model to use

    Returns:
        An initialized LLM provider (either OllamaProvider or GeminiProvider(to add in future maybe))
    """
    # Default to Ollama provider
    provider = OllamaProvider()

    return provider
