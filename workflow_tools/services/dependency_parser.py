"""Service for parsing Python dependencies and environment variables from code."""

import ast
import re
from typing import List, Set
from workflow_tools.core.config_loader import ConfigLoader

config = ConfigLoader()


class DependencyParser:
    """Parses and extracts Python package dependencies from code."""
    
    def __init__(self):
        """Initialize the dependency parser."""
        self.package_mappings = self._load_package_mappings()
    
    def extract_dependencies(self, code: str) -> List[str]:
        """Extract package dependencies from Python code.
        
        Args:
            code: Python source code
        
        Returns:
            List of required package names
        """
        dependencies = set()
        
        # Try AST parsing first
        try:
            dependencies = self._extract_with_ast(code)
        except SyntaxError:
            # Fallback to regex if AST parsing fails
            dependencies = self._extract_with_regex(code)
        
        # Map import names to actual package names
        mapped_deps = self._map_dependencies(dependencies)
        
        # Filter and clean dependencies
        cleaned_deps = self._clean_dependencies(mapped_deps)
        
        return sorted(cleaned_deps)
    
    def _extract_with_ast(self, code: str) -> Set[str]:
        """Extract imports using AST parsing.
        
        Args:
            code: Python source code
        
        Returns:
            Set of import names
        """
        tree = ast.parse(code)
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        
        return imports
    
    def _extract_with_regex(self, code: str) -> Set[str]:
        """Extract imports using regex patterns.
        
        Args:
            code: Python source code
        
        Returns:
            Set of import names
        """
        imports = set()
        
        # Pattern for 'import module' statements
        import_pattern = r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'
        for match in re.finditer(import_pattern, code, re.MULTILINE):
            module = match.group(1).split('.')[0]
            imports.add(module)
        
        # Pattern for 'from module import' statements
        from_pattern = r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import'
        for match in re.finditer(from_pattern, code, re.MULTILINE):
            module = match.group(1).split('.')[0]
            imports.add(module)
        
        return imports
    
    def _map_dependencies(self, imports: Set[str]) -> Set[str]:
        """Map import names to actual package names.
        
        Args:
            imports: Set of import names
        
        Returns:
            Set of actual package names
        """
        mapped = set()
        
        for imp in imports:
            # Check if there's a mapping for this import
            if imp in self.package_mappings:
                mapped.add(self.package_mappings[imp])
            else:
                mapped.add(imp)
        
        return mapped
    
    def _clean_dependencies(self, dependencies: Set[str]) -> Set[str]:
        """Clean and filter dependencies.
        
        Args:
            dependencies: Set of package names
        
        Returns:
            Cleaned set of package names
        """
        # Standard library modules to exclude
        stdlib_modules = {
            'os', 'sys', 'time', 'datetime', 'json', 'random', 'string',
            're', 'math', 'collections', 'itertools', 'functools',
            'typing', 'enum', 'dataclasses', 'pathlib', 'urllib',
            'asyncio', 'threading', 'multiprocessing', 'subprocess',
            'logging', 'warnings', 'traceback', 'inspect', 'ast',
            'copy', 'pickle', 'base64', 'hashlib', 'uuid', 'secrets',
            'contextlib', 'io', 'csv', 'configparser', 'argparse',
            'unittest', 'abc', 'queue', 'signal', 'atexit'
        }
        
        # Quix-specific packages to always include
        required_packages = {'quixstreams'}
        
        # Filter out standard library and add required packages
        cleaned = set()
        for dep in dependencies:
            if dep not in stdlib_modules:
                cleaned.add(dep)
        
        # Always include required packages
        cleaned.update(required_packages)
        
        return cleaned
    
    def _load_package_mappings(self) -> dict:
        """Load package mappings from configuration.
        
        Returns:
            Dictionary of import name to package name mappings
        """
        # Extended package mappings including common packages
        default_mappings = {
            'dotenv': 'python-dotenv',
            'psycopg2': 'psycopg2-binary',
            'oracledb': 'oracledb',
            'sqlalchemy': 'sqlalchemy',
            'mysql': 'mysql-connector-python',
            'pymongo': 'pymongo',
            'redis': 'redis',
            'boto3': 'boto3',
            'requests': 'requests',
            'pandas': 'pandas',
            'numpy': 'numpy',
            'google': 'google-cloud-storage',
            'azure': 'azure-storage-blob',
        }
        
        # Try to load from config and merge with defaults
        try:
            cfg = config.load_config()
            config_mappings = cfg.get("package_mappings", {})
            default_mappings.update(config_mappings)
        except:
            pass  # Use defaults if config loading fails
            
        return default_mappings
    
    def parse_dependency_comments(self, code: str) -> List[str]:
        """Parse AI-generated dependency comments to extract pip package names.
        
        Looks for dependency blocks in comments like:
        # DEPENDENCIES:
        # pip install package-name
        # END_DEPENDENCIES
        
        Args:
            code: Python source code with dependency comments
        
        Returns:
            List of package specifications (e.g., ['requests>=2.28.0', 'pandas'])
        """
        dependencies = []
        lines = code.split('\n')
        in_dependencies_block = False
        
        for line in lines:
            line = line.strip()
            
            if line == "# DEPENDENCIES:":
                in_dependencies_block = True
                continue
            elif line == "# END_DEPENDENCIES":
                break
            elif in_dependencies_block and line.startswith("# pip install "):
                # Extract package spec from "# pip install package-name"
                package_spec = line[14:].strip()  # Remove "# pip install "
                if package_spec:
                    dependencies.append(package_spec)  # Keep full spec for requirements.txt
        
        return dependencies
    
    def detect_required_packages(self, code: str) -> List[str]:
        """Detect required packages from import statements in code.
        
        This method extracts dependencies from imports and returns them
        as a list suitable for requirements.txt.
        
        Args:
            code: Python source code
        
        Returns:
            List of required package names
        """
        # First check for AI-generated dependency comments
        ai_dependencies = self.parse_dependency_comments(code)
        if ai_dependencies:
            return ai_dependencies
            
        # Otherwise extract from imports
        return self.extract_dependencies(code)
    
    def format_requirements(self, dependencies: List[str]) -> str:
        """Format dependencies as requirements.txt content.
        
        Args:
            dependencies: List of package names
        
        Returns:
            Formatted requirements.txt content
        """
        lines = []
        for dep in sorted(dependencies):
            # Don't add version constraints for now
            lines.append(dep)
        
        return '\n'.join(lines)