"""
Working directory structure management for the Quix Coding Agent.

This module provides centralized path management for all working files,
ensuring a clean and organized directory structure.
"""

import os
from pathlib import Path
from typing import Optional, Literal
from datetime import datetime

WorkflowType = Literal["sink", "source"]
CacheType = Literal["main", "connection_test"]


class WorkingDirectory:
    """Manages the working directory structure for the Quix Coding Agent."""
    
    BASE_DIR = "working_files"
    
    # Main directories
    CURRENT_DIR = "current"
    CACHE_DIR = "cache"
    TEMP_DIR = "temp"
    
    # Cache subdirectories
    CACHE_APPS = "apps"
    CACHE_TEMPLATES = "templates"
    CACHE_SCHEMAS = "schemas"
    CACHE_ANALYSIS = "analysis"
    CACHE_PREREQUISITES = "prerequisites"
    CACHE_PROMPTS = "prompts"
    CACHE_CONNECTION_TESTS = "connection_tests"
    CACHE_ENV_VARS = "env_vars"
    CACHE_CODE = "code"
    
    # Temp subdirectories
    TEMP_SAMPLES = "samples"
    TEMP_DEBUG = "debug"
    
    @classmethod
    def ensure_structure(cls):
        """Ensure the complete directory structure exists."""
        # Create base directories
        base_path = Path(cls.BASE_DIR)
        base_path.mkdir(exist_ok=True)
        
        # Create main subdirectories
        (base_path / cls.CURRENT_DIR).mkdir(exist_ok=True)
        (base_path / cls.CACHE_DIR).mkdir(exist_ok=True)
        (base_path / cls.TEMP_DIR).mkdir(exist_ok=True)
        
        # Create cache structure for all workflows
        for workflow in ["sink", "source", "diagnose"]:
            workflow_cache = base_path / cls.CACHE_DIR / workflow
            workflow_cache.mkdir(exist_ok=True)
            
            # Create cache subdirectories
            (workflow_cache / cls.CACHE_APPS).mkdir(exist_ok=True)
            (workflow_cache / cls.CACHE_TEMPLATES).mkdir(exist_ok=True)
            (workflow_cache / cls.CACHE_SCHEMAS).mkdir(exist_ok=True)
            (workflow_cache / cls.CACHE_ANALYSIS).mkdir(exist_ok=True)
            (workflow_cache / cls.CACHE_PREREQUISITES).mkdir(exist_ok=True)
            (workflow_cache / cls.CACHE_PROMPTS).mkdir(exist_ok=True)
            (workflow_cache / cls.CACHE_ENV_VARS).mkdir(exist_ok=True)
            (workflow_cache / cls.CACHE_CODE).mkdir(exist_ok=True)
            
            # Source-specific directories
            if workflow == "source":
                (workflow_cache / cls.CACHE_CONNECTION_TESTS).mkdir(exist_ok=True)
        
        # Create temp subdirectories
        (base_path / cls.TEMP_DIR / cls.TEMP_SAMPLES).mkdir(exist_ok=True)
        (base_path / cls.TEMP_DIR / cls.TEMP_DEBUG).mkdir(exist_ok=True)
    
    @classmethod
    def get_current_app_dir(cls) -> str:
        """Get the path to the current app directory."""
        cls.ensure_structure()
        return os.path.join(cls.BASE_DIR, cls.CURRENT_DIR)
    
    @classmethod
    def get_cached_app_dir(cls, workflow: WorkflowType, app_name: str, cache_type: CacheType = "main") -> str:
        """Get the path to a cached app directory."""
        cls.ensure_structure()
        sanitized_name = cls._sanitize_name(app_name)
        return os.path.join(cls.BASE_DIR, cls.CACHE_DIR, workflow, cls.CACHE_APPS, f"{sanitized_name}_{cache_type}")
    
    @classmethod
    def get_cached_template_path(cls, workflow: WorkflowType, tech_name: str) -> str:
        """Get the path to a cached template file."""
        cls.ensure_structure()
        sanitized_name = cls._sanitize_name(tech_name)
        return os.path.join(cls.BASE_DIR, cls.CACHE_DIR, workflow, cls.CACHE_TEMPLATES, f"{sanitized_name}.json")
    
    @classmethod
    def get_cached_schema_path(cls, workflow: WorkflowType, identifier: str) -> str:
        """Get the path to a cached schema analysis file."""
        cls.ensure_structure()
        sanitized_name = cls._sanitize_name(identifier)
        return os.path.join(cls.BASE_DIR, cls.CACHE_DIR, workflow, cls.CACHE_SCHEMAS, f"{sanitized_name}_schema.md")
    
    @classmethod
    def get_cached_analysis_path(cls, workflow: str, identifier: str) -> str:
        """Get the path to a cached app analysis file (for diagnose workflow)."""
        cls.ensure_structure()
        sanitized_name = cls._sanitize_name(identifier)
        return os.path.join(cls.BASE_DIR, cls.CACHE_DIR, workflow, cls.CACHE_ANALYSIS, f"{sanitized_name}_analysis.md")
    
    @classmethod
    def get_cached_prerequisites_path(cls, workflow: WorkflowType, timestamp: Optional[str] = None) -> str:
        """Get the path to a cached prerequisites file."""
        cls.ensure_structure()
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(cls.BASE_DIR, cls.CACHE_DIR, workflow, cls.CACHE_PREREQUISITES, f"{timestamp}.json")
    
    @classmethod
    def get_cached_prompt_path(cls, workflow: WorkflowType, app_name: str) -> str:
        """Get the path to a cached user prompt file."""
        cls.ensure_structure()
        sanitized_name = cls._sanitize_name(app_name)
        return os.path.join(cls.BASE_DIR, cls.CACHE_DIR, workflow, cls.CACHE_PROMPTS, f"{sanitized_name}.txt")
    
    @classmethod
    def get_cached_env_vars_path(cls, workflow: WorkflowType, tech_name: str) -> str:
        """Get the path to cached environment variables."""
        cls.ensure_structure()
        sanitized_name = cls._sanitize_name(tech_name)
        return os.path.join(cls.BASE_DIR, cls.CACHE_DIR, workflow, cls.CACHE_ENV_VARS, f"{sanitized_name}.json")
    
    @classmethod
    def get_cached_code_path(cls, workflow: WorkflowType, code_type: str, tech_name: str) -> str:
        """Get the path to cached code file."""
        cls.ensure_structure()
        sanitized_name = cls._sanitize_name(tech_name)
        return os.path.join(cls.BASE_DIR, cls.CACHE_DIR, workflow, cls.CACHE_CODE, f"{code_type}_{sanitized_name}.py")
    
    @classmethod
    def get_cached_connection_test_path(cls, tech_name: str) -> str:
        """Get the path to a cached connection test file (source only)."""
        cls.ensure_structure()
        sanitized_name = cls._sanitize_name(tech_name)
        return os.path.join(cls.BASE_DIR, cls.CACHE_DIR, "source", cls.CACHE_CONNECTION_TESTS, f"{sanitized_name}.py")
    
    @classmethod
    def get_temp_sample_path(cls, timestamp: Optional[str] = None) -> str:
        """Get the path to a temporary sample data file."""
        cls.ensure_structure()
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(cls.BASE_DIR, cls.TEMP_DIR, cls.TEMP_SAMPLES, f"{timestamp}.txt")
    
    @classmethod
    def get_temp_debug_path(cls, filename: str) -> str:
        """Get the path to a temporary debug file."""
        cls.ensure_structure()
        return os.path.join(cls.BASE_DIR, cls.TEMP_DIR, cls.TEMP_DEBUG, filename)
    
    @classmethod
    def clear_current_app(cls):
        """Clear the current app directory."""
        import shutil
        current_dir = cls.get_current_app_dir()
        if os.path.exists(current_dir):
            # Remove all contents but keep the directory
            for item in os.listdir(current_dir):
                item_path = os.path.join(current_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
    
    @classmethod
    def clear_temp_files(cls):
        """Clear all temporary files."""
        import shutil
        temp_dir = os.path.join(cls.BASE_DIR, cls.TEMP_DIR)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        cls.ensure_structure()  # Recreate empty structure
    
    @classmethod
    def _sanitize_name(cls, name: str) -> str:
        """Sanitize a name for use in file paths."""
        if not name:
            return "unknown"
        # Replace problematic characters
        sanitized = name.lower()
        for char in [' ', '/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            sanitized = sanitized.replace(char, '_')
        # Remove multiple underscores
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        # Trim underscores from ends
        sanitized = sanitized.strip('_')
        return sanitized or "unknown"
    
    @classmethod
    def migrate_existing_files(cls):
        """One-time migration of existing files to new structure."""
        import shutil
        base_path = Path(cls.BASE_DIR)
        
        if not base_path.exists():
            return
        
        cls.ensure_structure()
        
        # Migrate files based on patterns
        for item in os.listdir(base_path):
            item_path = base_path / item
            
            # Skip if it's one of our new directories
            if item in [cls.CURRENT_DIR, cls.CACHE_DIR, cls.TEMP_DIR]:
                continue
            
            # Skip empty.txt
            if item == "empty.txt":
                continue
            
            # Migrate based on patterns
            if item.startswith("sink_"):
                cls._migrate_sink_file(item, item_path)
            elif item.startswith("source_"):
                cls._migrate_source_file(item, item_path)
            elif item.startswith("cached_app_"):
                cls._migrate_cached_app(item, item_path)
            elif "_schema_analysis" in item or "schema_analysis.md" == item:
                cls._migrate_schema_file(item, item_path)
            elif item.endswith("_source_code") or item.endswith("_sink_code"):
                # These are extracted app directories - can be deleted or moved to current
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            # Leave other files as-is for manual review
    
    @classmethod
    def _migrate_sink_file(cls, filename: str, filepath: Path):
        """Migrate a sink-related file to new structure."""
        import shutil
        
        if "prerequisites" in filename:
            new_path = Path(cls.BASE_DIR) / cls.CACHE_DIR / "sink" / cls.CACHE_PREREQUISITES / filename.replace("sink_prerequisites_", "")
            shutil.move(str(filepath), str(new_path))
        elif "template" in filename:
            new_path = Path(cls.BASE_DIR) / cls.CACHE_DIR / "sink" / cls.CACHE_TEMPLATES / filename.replace("sink_template_", "")
            shutil.move(str(filepath), str(new_path))
        elif "claude_code" in filename or "sandbox_code" in filename:
            new_path = Path(cls.BASE_DIR) / cls.CACHE_DIR / "sink" / cls.CACHE_CODE / filename.replace("sink_", "")
            shutil.move(str(filepath), str(new_path))
        elif "user_prompt" in filename:
            new_path = Path(cls.BASE_DIR) / cls.CACHE_DIR / "sink" / cls.CACHE_PROMPTS / filename.replace("sink_user_prompt_", "")
            shutil.move(str(filepath), str(new_path))
        elif "app_name" in filename:
            new_path = Path(cls.BASE_DIR) / cls.CACHE_DIR / "sink" / cls.CACHE_PROMPTS / filename.replace("sink_app_name_", "app_name_")
            shutil.move(str(filepath), str(new_path))
    
    @classmethod
    def _migrate_source_file(cls, filename: str, filepath: Path):
        """Migrate a source-related file to new structure."""
        import shutil
        
        if "prerequisites" in filename:
            new_path = Path(cls.BASE_DIR) / cls.CACHE_DIR / "source" / cls.CACHE_PREREQUISITES / filename.replace("source_prerequisites_", "")
            shutil.move(str(filepath), str(new_path))
        elif "connection_test" in filename:
            new_path = Path(cls.BASE_DIR) / cls.CACHE_DIR / "source" / cls.CACHE_CONNECTION_TESTS / filename.replace("source_connection_test_code_", "")
            shutil.move(str(filepath), str(new_path))
        elif "samples" in filename:
            new_path = Path(cls.BASE_DIR) / cls.TEMP_DIR / cls.TEMP_SAMPLES / filename.replace("source_samples_", "")
            shutil.move(str(filepath), str(new_path))
        elif "app_name" in filename:
            new_path = Path(cls.BASE_DIR) / cls.CACHE_DIR / "source" / cls.CACHE_PROMPTS / filename.replace("source_app_name_", "app_name_")
            shutil.move(str(filepath), str(new_path))
    
    @classmethod
    def _migrate_cached_app(cls, dirname: str, dirpath: Path):
        """Migrate a cached app directory to new structure."""
        import shutil
        
        if os.path.isdir(dirpath):
            if "source" in dirname:
                new_path = Path(cls.BASE_DIR) / cls.CACHE_DIR / "source" / cls.CACHE_APPS / dirname.replace("cached_app_source_", "")
                shutil.move(str(dirpath), str(new_path))
            elif "sink" in dirname:
                new_path = Path(cls.BASE_DIR) / cls.CACHE_DIR / "sink" / cls.CACHE_APPS / dirname.replace("cached_app_sink_", "")
                shutil.move(str(dirpath), str(new_path))
    
    @classmethod
    def _migrate_schema_file(cls, filename: str, filepath: Path):
        """Migrate a schema analysis file to new structure."""
        import shutil
        
        # Try to determine if it's sink or source based on content or name
        # For now, default to source as most schemas seem to be for source
        if os.path.isfile(filepath):
            new_path = Path(cls.BASE_DIR) / cls.CACHE_DIR / "source" / cls.CACHE_SCHEMAS / filename
            shutil.move(str(filepath), str(new_path))