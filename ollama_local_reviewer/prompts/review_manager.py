
import os
from typing import Dict, Optional
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound


class TemplateManager:
   
    def __init__(self, template_dir: str = "templates"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, 'templates')
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
        )
        self._templates: Dict[str, Template] = {}
        self._load_templates()

    def _load_templates(self):
        """Load all available templates."""
        template_files = {
            "base_review": "base_review.jinja",
            "code_smells_and_metrics": "code_smells_and_metrics.jinja",
            "readability_review": "readability_review.jinja",
            "security_review": "security_review.jinja",
            "synthesize": "synthesize.jinja"
        }

        for section_name, filename in template_files.items():
            try:
                template_path = os.path.join(self.template_dir, filename)
                if os.path.exists(template_path):
                    self._templates[section_name] = self.env.get_template(filename)
                else:
                    print(f"Template file not found: {template_path}")
            except Exception as e:
                print(f"Error loading template {filename}: {e}")

    def get_available_sections(self) -> list:
    
        return list(self._templates.keys())

    def render_template(self, section_name: str, **kwargs) -> Optional[str]:
        if section_name not in self._templates:
            print(f" Template not found for section: {section_name}")
            print(f"Available sections: {self.get_available_sections()}")
            return None

        try:
            template = self._templates[section_name]
            return template.render(**kwargs)
        except Exception as e:
            print(f"Error rendering template for {section_name}: {e}")
            return None

    def build_prompt(self, agent_name: str, diff_content: str) -> str:
        """
        Loads the specific agent template and injects the git diff.
        """
        try:
            template = self.env.get_template(f"{agent_name}.jinja")
        except TemplateNotFound:
            raise FileNotFoundError(f"Template {agent_name}.jinja not found in {self.env.loader.searchpath}")
        
        return template.render(
            diff_text=diff_content,
            enforce_json=True
        )

