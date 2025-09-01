"""Interface definitions for service layer."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CodeGenerationRequest:
    """Request for code generation."""
    template_code: str
    requirements: str
    schema: Dict[str, Any]
    env_vars: Dict[str, Any]
    technology: str
    workflow_type: str = "sink"


@dataclass
class CodeGenerationResponse:
    """Response from code generation."""
    success: bool
    code: Optional[str] = None
    dependencies: Optional[List[str]] = None
    error_message: Optional[str] = None


@dataclass
class DebugAnalysisRequest:
    """Request for debug analysis."""
    code: str
    error_logs: str
    workflow_type: str = "sink"


@dataclass
class DebugAnalysisResponse:
    """Response from debug analysis."""
    success: bool
    root_cause: Optional[str] = None
    fix_description: Optional[str] = None
    fixed_code: Optional[str] = None
    error_type: Optional[str] = None


class ICodeGenerator(ABC):
    """Interface for code generation services."""
    
    @abstractmethod
    async def generate_code(self, request: CodeGenerationRequest) -> CodeGenerationResponse:
        """Generate code based on request.
        
        Args:
            request: Code generation request
            
        Returns:
            Code generation response
        """
        pass
    
    @abstractmethod
    async def improve_code(self, code: str, feedback: str) -> CodeGenerationResponse:
        """Improve existing code based on feedback.
        
        Args:
            code: Current code
            feedback: Improvement feedback
            
        Returns:
            Improved code response
        """
        pass


class IDebugAnalyzer(ABC):
    """Interface for debug analysis services."""
    
    @abstractmethod
    async def analyze_error(self, request: DebugAnalysisRequest) -> DebugAnalysisResponse:
        """Analyze error and suggest fixes.
        
        Args:
            request: Debug analysis request
            
        Returns:
            Debug analysis response
        """
        pass
    
    @abstractmethod
    def identify_error_pattern(self, error_logs: str) -> str:
        """Identify error pattern from logs.
        
        Args:
            error_logs: Error log text
            
        Returns:
            Identified error pattern
        """
        pass


class IDependencyParser(ABC):
    """Interface for dependency parsing services."""
    
    @abstractmethod
    def extract_dependencies(self, code: str) -> List[str]:
        """Extract dependencies from code.
        
        Args:
            code: Source code
            
        Returns:
            List of dependencies
        """
        pass
    
    @abstractmethod
    def format_requirements(self, dependencies: List[str]) -> str:
        """Format dependencies as requirements.txt.
        
        Args:
            dependencies: List of dependencies
            
        Returns:
            Formatted requirements text
        """
        pass


class IFileManager(ABC):
    """Interface for file management services."""
    
    @abstractmethod
    def save_generated_code(self, code: str, technology: str, 
                           workflow_type: str) -> str:
        """Save generated code to filesystem.
        
        Args:
            code: Code to save
            technology: Technology name
            workflow_type: Workflow type
            
        Returns:
            Path to saved code
        """
        pass
    
    @abstractmethod
    def save_requirements(self, requirements: List[str], code_dir: str) -> str:
        """Save requirements file.
        
        Args:
            requirements: List of requirements
            code_dir: Code directory
            
        Returns:
            Path to requirements file
        """
        pass


class IQuixClient(ABC):
    """Interface for Quix platform interactions."""
    
    @abstractmethod
    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List available workspaces.
        
        Returns:
            List of workspace details
        """
        pass
    
    @abstractmethod
    async def list_topics(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List topics in a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            List of topic details
        """
        pass
    
    @abstractmethod
    async def create_application(self, workspace_id: str, name: str, 
                                library_item_id: Optional[str] = None) -> Dict[str, Any]:
        """Create an application.
        
        Args:
            workspace_id: Workspace ID
            name: Application name
            library_item_id: Optional library item ID
            
        Returns:
            Application details
        """
        pass
    
    @abstractmethod
    async def create_session(self, workspace_id: str, 
                           application_id: str) -> Dict[str, Any]:
        """Create an IDE session.
        
        Args:
            workspace_id: Workspace ID
            application_id: Application ID
            
        Returns:
            Session details
        """
        pass
    
    @abstractmethod
    async def deploy_application(self, workspace_id: str, 
                                application_id: str) -> Dict[str, Any]:
        """Deploy an application.
        
        Args:
            workspace_id: Workspace ID
            application_id: Application ID
            
        Returns:
            Deployment details
        """
        pass
    
    @abstractmethod
    async def get_deployment_status(self, workspace_id: str, 
                                   deployment_id: str) -> str:
        """Get deployment status.
        
        Args:
            workspace_id: Workspace ID
            deployment_id: Deployment ID
            
        Returns:
            Deployment status
        """
        pass


class ISchemaAnalyzer(ABC):
    """Interface for schema analysis services."""
    
    @abstractmethod
    async def analyze_topic_schema(self, workspace_id: str, 
                                  topic_id: str) -> Dict[str, Any]:
        """Analyze schema from topic data.
        
        Args:
            workspace_id: Workspace ID
            topic_id: Topic ID
            
        Returns:
            Schema analysis result
        """
        pass
    
    @abstractmethod
    async def validate_schema(self, schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate a schema definition.
        
        Args:
            schema: Schema to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass


class ITemplateSelector(ABC):
    """Interface for template selection services."""
    
    @abstractmethod
    async def find_matching_template(self, technology: str, 
                                    workflow_type: str) -> Optional[Dict[str, Any]]:
        """Find matching template for technology.
        
        Args:
            technology: Technology name
            workflow_type: Workflow type
            
        Returns:
            Template details or None
        """
        pass
    
    @abstractmethod
    def list_available_templates(self, workflow_type: str) -> List[str]:
        """List available templates.
        
        Args:
            workflow_type: Workflow type
            
        Returns:
            List of template names
        """
        pass


class IEnvironmentVariableManager(ABC):
    """Interface for environment variable management."""
    
    @abstractmethod
    async def extract_variables(self, code: str) -> Dict[str, Any]:
        """Extract environment variables from code.
        
        Args:
            code: Source code
            
        Returns:
            Dictionary of environment variables
        """
        pass
    
    @abstractmethod
    async def translate_variables(self, template_vars: Dict[str, Any], 
                                 technology: str) -> Dict[str, Any]:
        """Translate template variables for technology.
        
        Args:
            template_vars: Template variables
            technology: Target technology
            
        Returns:
            Translated variables
        """
        pass
    
    @abstractmethod
    def apply_smart_defaults(self, variables: Dict[str, Any], 
                           technology: str) -> Dict[str, Any]:
        """Apply smart defaults to variables.
        
        Args:
            variables: Current variables
            technology: Technology type
            
        Returns:
            Variables with defaults applied
        """
        pass