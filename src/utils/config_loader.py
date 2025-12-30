"""Configuration loader for prompts and settings."""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and manage configuration from YAML files."""

    def __init__(self, config_dir: str = None):
        """
        Initialize config loader.

        Args:
            config_dir: Directory containing config files (defaults to project config/)
        """
        if config_dir is None:
            # Default to project config directory
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "config"

        self.config_dir = Path(config_dir)
        self._prompts_config = None
        self._global_config = None

    def load_prompts(self, config_file: str = "prompts.yaml") -> Dict[str, Any]:
        """
        Load prompts configuration.

        Args:
            config_file: Name of the prompts config file

        Returns:
            Prompts configuration dict

        Raises:
            ConfigurationError: If config file not found or invalid
        """
        if self._prompts_config is not None:
            return self._prompts_config

        config_path = self.config_dir / config_file

        if not config_path.exists():
            raise ConfigurationError(f"Prompts config file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._prompts_config = yaml.safe_load(f)

            logger.info(f"Loaded prompts config from: {config_path}")
            return self._prompts_config

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML config: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load config: {e}")

    def get_prompt(self, agent_name: str, prompt_key: str, **kwargs) -> str:
        """
        Get a prompt template and format it with provided kwargs.

        Args:
            agent_name: Name of the agent (e.g., 'requirement_parser')
            prompt_key: Key of the prompt (e.g., 'system_prompt')
            **kwargs: Variables to format the template

        Returns:
            Formatted prompt string

        Raises:
            ConfigurationError: If prompt not found
        """
        prompts = self.load_prompts()

        if agent_name not in prompts:
            raise ConfigurationError(f"Agent '{agent_name}' not found in prompts config")

        agent_prompts = prompts[agent_name]

        if prompt_key not in agent_prompts:
            raise ConfigurationError(
                f"Prompt '{prompt_key}' not found for agent '{agent_name}'"
            )

        template = agent_prompts[prompt_key]

        # Format template with kwargs
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ConfigurationError(
                f"Missing variable {e} for prompt template '{prompt_key}'"
            )

    def get_global_config(self, key: str, default: Any = None) -> Any:
        """
        Get global configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        prompts = self.load_prompts()
        global_config = prompts.get("global", {})

        return global_config.get(key, default)

    def reload(self):
        """Reload configuration from files."""
        self._prompts_config = None
        self._global_config = None
        logger.info("Configuration reloaded")


# Global config loader instance
_config_loader = None


def get_config_loader(config_dir: str = None) -> ConfigLoader:
    """
    Get global config loader instance.

    Args:
        config_dir: Optional config directory

    Returns:
        ConfigLoader instance
    """
    global _config_loader

    if _config_loader is None:
        _config_loader = ConfigLoader(config_dir)

    return _config_loader


def get_prompt(agent_name: str, prompt_key: str, **kwargs) -> str:
    """
    Convenience function to get a formatted prompt.

    Args:
        agent_name: Name of the agent
        prompt_key: Key of the prompt
        **kwargs: Template variables

    Returns:
        Formatted prompt string
    """
    loader = get_config_loader()
    return loader.get_prompt(agent_name, prompt_key, **kwargs)


def get_config(key: str, default: Any = None) -> Any:
    """
    Convenience function to get global config value.

    Args:
        key: Configuration key
        default: Default value

    Returns:
        Configuration value
    """
    loader = get_config_loader()
    return loader.get_global_config(key, default)
