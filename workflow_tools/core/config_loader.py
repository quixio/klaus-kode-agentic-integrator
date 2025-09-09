"""Configuration loader for YAML-based settings."""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """Loads and manages configuration from YAML files."""
    
    def __init__(self, config_dir: str = "config"):
        """Initialize the configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Any] = {}
        self._main_config: Optional[Dict[str, Any]] = None
        self._models_config: Optional[Dict[str, Any]] = None
        self._workflows_config: Optional[Dict[str, Any]] = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load the main configuration file.
        
        Returns:
            Dictionary containing main configuration
        """
        if self._main_config is None:
            self._main_config = self._load_yaml_file("config.yaml")
            self._substitute_env_vars(self._main_config)
        return self._main_config
    
    def load_models_config(self) -> Dict[str, Any]:
        """Load the models configuration file.
        
        Returns:
            Dictionary containing model configurations
        """
        if self._models_config is None:
            self._models_config = self._load_yaml_file("models.yaml")
        return self._models_config
    
    def load_workflows_config(self) -> Dict[str, Any]:
        """Load the workflows configuration file.
        
        Returns:
            Dictionary containing workflow configurations
        """
        if self._workflows_config is None:
            self._workflows_config = self._load_yaml_file("workflows.yaml")
        return self._workflows_config
    
    def get_model_config(self, task: str, workflow_type: str = None) -> Dict[str, Any]:
        """Get model configuration for a specific task.
        
        Args:
            task: The task type (e.g., 'code_generation', 'schema_analysis')
            workflow_type: Optional workflow type ('sink' or 'source')
        
        Returns:
            Model configuration dictionary
        """
        models = self.load_models_config()
        model_config = models.get("models", {}).get(task, {})
        
        # If workflow_type is specified and task has workflow-specific config
        if workflow_type and isinstance(model_config, dict) and workflow_type in model_config:
            model_config = model_config[workflow_type]
        
        # Add parameters if available
        params = models.get("parameters", {})
        if task in params:
            model_config["parameters"] = params[task]
        elif "default" in params:
            model_config["parameters"] = params["default"]
        
        return model_config
    
    def get_workflow_config(self, workflow_type: str) -> Dict[str, Any]:
        """Get configuration for a specific workflow.
        
        Args:
            workflow_type: The workflow type ('sink' or 'source')
        
        Returns:
            Workflow configuration dictionary
        """
        workflows = self.load_workflows_config()
        return workflows.get("workflows", {}).get(workflow_type, {})
    
    def get_phase_config(self, phase_name: str) -> Dict[str, Any]:
        """Get configuration for a specific phase.
        
        Args:
            phase_name: Name of the phase
        
        Returns:
            Phase configuration dictionary
        """
        workflows = self.load_workflows_config()
        phases = workflows.get("phases", {})
        
        # Combine phase-specific config with defaults
        config = {}
        if "retry_config" in phases:
            config["retry"] = phases["retry_config"]
        if "timeouts" in phases and phase_name in phases["timeouts"]:
            config["timeout"] = phases["timeouts"][phase_name]
        
        return config
    
    def get_package_mapping(self, package_name: str) -> str:
        """Get the actual package name for a given import.
        
        Args:
            package_name: The import name
        
        Returns:
            The actual package name to install
        """
        config = self.load_config()
        mappings = config.get("package_mappings", {})
        return mappings.get(package_name, package_name)
    
    def get_supported_technologies(self, tech_type: str) -> list:
        """Get list of supported technologies.
        
        Args:
            tech_type: Either 'sinks' or 'sources'
        
        Returns:
            List of supported technology names
        """
        config = self.load_config()
        return config.get("technologies", {}).get(tech_type, [])
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled.
        
        Args:
            feature_name: Name of the feature
        
        Returns:
            True if feature is enabled, False otherwise
        """
        config = self.load_config()
        features = config.get("features", {})
        value = features.get(feature_name, False)
        
        # Handle string boolean values
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    def get_path(self, path_key: str) -> Path:
        """Get a configured path.
        
        Args:
            path_key: Key for the path in configuration
        
        Returns:
            Path object for the configured path
        """
        config = self.load_config()
        paths = config.get("paths", {})
        path_str = paths.get(path_key, "")
        return Path(path_str) if path_str else Path(".")
    
    def _load_yaml_file(self, filename: str) -> Dict[str, Any]:
        """Load a YAML file from the config directory.
        
        Args:
            filename: Name of the YAML file
        
        Returns:
            Parsed YAML content as dictionary
        """
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            print(f"Warning: Configuration file {file_path} not found")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file {filename}: {e}")
            return {}
        except Exception as e:
            print(f"Error reading configuration file {filename}: {e}")
            return {}
    
    def _substitute_env_vars(self, config: Dict[str, Any]) -> None:
        """Recursively substitute environment variables in configuration.
        
        Args:
            config: Configuration dictionary to process
        """
        for key, value in config.items():
            if isinstance(value, dict):
                self._substitute_env_vars(value)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Parse environment variable reference
                env_expr = value[2:-1]
                if ":-" in env_expr:
                    # Has default value
                    env_var, default = env_expr.split(":-", 1)
                    config[key] = os.getenv(env_var, default)
                else:
                    # No default value
                    config[key] = os.getenv(env_expr, value)


# Global configuration instance
config = ConfigLoader()