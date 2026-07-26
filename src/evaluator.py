
import yaml
import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
from prompts.review_manager import TemplateManager
CONFIG_PATH = os.path.join(BASE_DIR, "providers.yml")
with open(CONFIG_PATH, "r") as file:
    config = yaml.safe_load(file)

print(BASE_DIR,CONFIG_PATH)
DEFAULT_MODEL = config["default_model"]
DEFAULT_PROVIDER = "ollama"
DEFAULT_MODEL_PARAMETERS = config["providers"][DEFAULT_PROVIDER]["models"][DEFAULT_MODEL]
from src.llm_utils import initialize_llm_provider

class Evaluator:
    def __init__(self, model_name: str = DEFAULT_MODEL, model_params: dict = None):
        if not model_name:
            raise ValueError("Model name cannot be empty")

        if model_name not in config["providers"][DEFAULT_PROVIDER]["models"]:
            raise ValueError("Input model not in yml")

        self.model_name = model_name
        if model_name == DEFAULT_MODEL:
            self.model_params = DEFAULT_MODEL_PARAMETERS
        else:
            self.model_params = config["providers"][DEFAULT_PROVIDER]["models"][model_name]
        
        self.template_manager = TemplateManager()
        self.template_manager.__init__
        self._initialize_llm_provider()

    def _initialize_llm_provider(self):
        """Initialize the appropriate LLM provider based on the model."""
        self.provider = initialize_llm_provider(self.model_name)

    def run_review(self, agent_name: str, diff_content: str) -> str:
        """
        Builds the prompt using the Jinja template and sends it to the LLM.
        """
        prompt = self.template_manager.build_prompt(agent_name, diff_content)
      
        print(f"[{agent_name.capitalize()} Agent] Sending request to {self.model_name} (Temp: {self.model_params.get('temperature')})...")
        chat_params = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content":prompt},
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.model_params.get("temperature"),
                "top_p": self.model_params.get("top_p"),
            },
        }
        response = self.provider.chat(**chat_params)
        
        return response