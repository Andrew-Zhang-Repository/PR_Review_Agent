from abc import ABC, abstractmethod
from enum import Enum
import yaml
from typing import List, Optional, Dict, Tuple, Any, Protocol, runtime_checkable

with open("providers.yml", "r") as file:
    config = yaml.safe_load(file)


class ModelProvider(Enum):
    OLLAMA = "ollama"
    DEFAULT_MODEL = config["default_model"]


class LLMBackend(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass
    
   
class gemma312b(LLMBackend):
    def generate(self, prompt: str) -> str:
        return "Gemma3 12b model"
        

class gemma34b(LLMBackend):
    def generate(self, prompt: str) -> str:
        return "Gemma3 4b model"


class qwen34b(LLMBackend):
    def generate(self, prompt: str) -> str:
        return "Qwen3 4b model"
        
class OllamaProvider:
    """Ollama LLM provider implementation."""

    def __init__(self):
        import ollama

        self.client = ollama

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to Ollama."""

        ollama_options = options.copy() if options else {}

        # remove steam from ollama options
        ollama_options.pop("stream", None)

        # Add num_ctx 32K context window to options
        ollama_options["num_ctx"] = 32768

        # convert to chat params
        chat_params = {
            "model": model,
            "messages": messages,
            "options": ollama_options,
        }

        # add it to top level
        if "stream" in kwargs:
            chat_params["stream"] = kwargs["stream"]

        if "format" in kwargs:
            chat_params["format"] = kwargs["format"]

        return self.client.chat(**chat_params)