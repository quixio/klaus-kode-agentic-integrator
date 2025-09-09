"""Service for managing file operations."""

import os
import json
import random
import string
from pathlib import Path
from typing import Dict, Any, Optional, List

from workflow_tools.core.config_loader import ConfigLoader
config = ConfigLoader()


class FileManager:
    """Manages file operations for workflow artifacts."""
    
    def __init__(self, debug_mode: bool = False):
        """Initialize the file manager.
        
        Args:
            debug_mode: Whether to enable debug mode
        """
        self.debug_mode = debug_mode
        self.working_dir = self._get_working_directory()
        self.resources_dir = self._get_resources_directory()
        self._ensure_directories()
    
    def save_generated_code(self, code: str, technology: str, 
                           workflow_type: str = "sink") -> str:
        """Save generated code to a file.
        
        Args:
            code: The code to save
            technology: Technology name (e.g., "questdb", "timescaledb")
            workflow_type: Type of workflow (sink or source)
        
        Returns:
            Path to the saved file
        """
        # Generate unique identifier
        unique_id = self._generate_unique_id()
        
        # Create directory name
        dir_name = f"{technology.lower()}-{workflow_type}-{unique_id}_source_code"
        dir_path = self.working_dir / dir_name
        
        # Create directory
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Save main.py
        main_file = dir_path / "main.py"
        main_file.write_text(code)
        
        if self.debug_mode:
            print(f"Saved generated code to: {main_file}")
        
        return str(dir_path)
    
    def save_requirements(self, requirements: List[str], code_dir: str) -> str:
        """Save requirements.txt file.
        
        Args:
            requirements: List of package requirements
            code_dir: Directory containing the code
        
        Returns:
            Path to the saved requirements file
        """
        req_file = Path(code_dir) / "requirements.txt"
        req_content = "\n".join(requirements)
        req_file.write_text(req_content)
        
        if self.debug_mode:
            print(f"Saved requirements to: {req_file}")
        
        return str(req_file)
    
    def save_dockerfile(self, code_dir: str, base_image: str = "python:3.11-slim") -> str:
        """Save Dockerfile for the application.
        
        Args:
            code_dir: Directory containing the code
            base_image: Base Docker image to use
        
        Returns:
            Path to the saved Dockerfile
        """
        dockerfile_content = f"""FROM {base_image}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
"""
        
        dockerfile = Path(code_dir) / "dockerfile"
        dockerfile.write_text(dockerfile_content)
        
        if self.debug_mode:
            print(f"Saved Dockerfile to: {dockerfile}")
        
        return str(dockerfile)
    
    def save_app_yaml(self, code_dir: str, env_vars: Dict[str, Any]) -> str:
        """Save app.yaml configuration file.
        
        Args:
            code_dir: Directory containing the code
            env_vars: Environment variables configuration
        
        Returns:
            Path to the saved app.yaml file
        """
        # Create app.yaml content
        app_yaml = {
            "name": Path(code_dir).name.replace("_source_code", ""),
            "language": "python",
            "variables": env_vars
        }
        
        app_yaml_file = Path(code_dir) / "app.yaml"
        
        # Save as YAML (simplified format)
        with open(app_yaml_file, 'w', encoding='utf-8') as f:
            f.write("name: " + app_yaml["name"] + "\n")
            f.write("language: python\n")
            f.write("variables:\n")
            for key, value in env_vars.items():
                f.write(f"  {key}: {json.dumps(value)}\n")
        
        if self.debug_mode:
            print(f"Saved app.yaml to: {app_yaml_file}")
        
        return str(app_yaml_file)
    
    def read_template(self, template_name: str, tech_type: str = "sink") -> Optional[str]:
        """Read a template file from resources.
        
        Args:
            template_name: Name of the template
            tech_type: Type of template (sink or source)
        
        Returns:
            Template content or None if not found
        """
        template_path = self.resources_dir / tech_type / f"{template_name}.md"
        
        if not template_path.exists():
            # Try without .md extension
            template_path = self.resources_dir / tech_type / template_name
        
        if template_path.exists():
            return template_path.read_text()
        
        return None
    
    def list_files_in_directory(self, directory: str) -> List[str]:
        """List all files in a directory.
        
        Args:
            directory: Path to the directory
        
        Returns:
            List of file paths
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            return []
        
        files = []
        for item in dir_path.rglob("*"):
            if item.is_file():
                files.append(str(item))
        
        return files
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """Clean up old temporary files.
        
        Args:
            max_age_hours: Maximum age of files to keep in hours
        
        Returns:
            Number of files deleted
        """
        import time
        from datetime import datetime, timedelta
        
        deleted_count = 0
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        # Clean up working directory
        for item in self.working_dir.iterdir():
            if item.is_dir() and "_source_code" in item.name:
                # Check modification time
                if item.stat().st_mtime < cutoff_time:
                    try:
                        import shutil
                        shutil.rmtree(item)
                        deleted_count += 1
                        if self.debug_mode:
                            print(f"Deleted old directory: {item}")
                    except Exception as e:
                        if self.debug_mode:
                            print(f"Error deleting {item}: {e}")
        
        return deleted_count
    
    def _get_working_directory(self) -> Path:
        """Get the working directory path from configuration.
        
        Returns:
            Path to working directory
        """
        cfg = config.load_config()
        working_dir = cfg.get("paths", {}).get("working_directory", "working_files")
        return Path(working_dir)
    
    def _get_resources_directory(self) -> Path:
        """Get the resources directory path from configuration.
        
        Returns:
            Path to resources directory
        """
        cfg = config.load_config()
        resources_dir = cfg.get("paths", {}).get("resources_directory", "resources")
        return Path(resources_dir)
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.working_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure empty.txt exists in working directory
        empty_file = self.working_dir / "empty.txt"
        if not empty_file.exists():
            empty_file.touch()
    
    def _generate_unique_id(self, length: int = 4) -> str:
        """Generate a unique identifier.
        
        Args:
            length: Length of the identifier
        
        Returns:
            Random alphanumeric string
        """
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))