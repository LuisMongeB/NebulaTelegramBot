import logging
from typing import Any, Dict

import yaml


def load_yaml(file_path):
    """
    Load a YAML file and return its content.

    :param file_path: Path to the YAML file.
    :return: Content of the YAML file as a dictionary.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return {}
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file {file_path}: {e}")
        return {}


def build_prompt(prompt_name: str) -> Dict[str, Any]:
    """
    Build a prompt from a YAML file based on the provided prompt name.

    :param prompt_name: Name of the prompt to build.
    :return: The constructed prompt string.
    """
    yaml_file_path = "src/agents/prompts.yaml"
    prompts = load_yaml(yaml_file_path)

    if not prompts:
        return {"error": "Failed to load prompts from YAML file."}

    if prompt_name not in prompts:
        logging.error(f"Prompt '{prompt_name}' not found in YAML file.")
        return {"error": f"Prompt '{prompt_name}' not found."}

    prompt_content = prompts[prompt_name]

    if isinstance(prompt_content, dict):
        return "\n".join(
            f"{key.capitalize()}: {value}" for key, value in prompt_content.items()
        )

    return str(prompt_content)
