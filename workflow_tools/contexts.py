"""Refactored context classes following Single Responsibility Principle."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import json


@dataclass
class WorkspaceContext:
    """Context for workspace-related information."""
    workspace_id: Optional[str] = None
    repository_id: Optional[str] = None  # Repository ID for secret management
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None
    branch_name: Optional[str] = None  # Git branch for this workspace


@dataclass
class TechnologyContext:
    """Context for technology and template selection."""
    destination_technology: Optional[str] = None
    source_technology: Optional[str] = None
    library_item_id: Optional[str] = None
    has_exact_template_match: bool = False
    selected_library_item: Optional[Dict[str, Any]] = None
    technology_preparation_advice: Optional[str] = None
    # Data specification fields for issue #36
    source_data_specification: Optional[str] = None
    sink_data_specification: Optional[str] = None


@dataclass
class SchemaContext:
    """Context for data schema information."""
    data_schema: Optional[Dict[str, Any]] = None
    table_name: Optional[str] = None


@dataclass
class CodeGenerationContext:
    """Context for code generation and templates."""
    template_code: Optional[str] = None
    template_requirements: Optional[str] = None
    generated_code_draft: Optional[str] = None
    docs_content: str = ""
    app_extract_dir: Optional[str] = None
    
    # Additional attributes for comprehensive workflow support
    code_feedback: Optional[str] = None
    connection_test_code: Optional[str] = None
    connection_test_file: Optional[str] = None
    source_schema_doc_path: Optional[str] = None
    dependencies: Optional[List[str]] = None
    generated_code_path: Optional[str] = None
    
    # Store generation prompts for log analysis (issue #2)
    last_generation_prompt: Optional[str] = None
    last_connection_test_prompt: Optional[str] = None


@dataclass
class DeploymentContext:
    """Context for application deployment."""
    application_name: Optional[str] = None
    application_id: Optional[str] = None
    application_path: Optional[str] = None
    session_id: Optional[str] = None
    deployment_id: Optional[str] = None
    deployment_name: Optional[str] = None


@dataclass
class CredentialsContext:
    """Context for credentials and environment variables."""
    connection_credentials: Dict[str, str] = field(default_factory=dict)
    env_var_names: List[str] = field(default_factory=list)
    env_var_values: Dict[str, str] = field(default_factory=dict)
    translated_env_content: Optional[str] = None
    secret_variables: List[str] = field(default_factory=list)


@dataclass
class WorkflowContext:
    """Main workflow context composed of focused sub-contexts."""
    workspace: WorkspaceContext = field(default_factory=WorkspaceContext)
    technology: TechnologyContext = field(default_factory=TechnologyContext)
    schema: SchemaContext = field(default_factory=SchemaContext)
    code_generation: CodeGenerationContext = field(default_factory=CodeGenerationContext)
    deployment: DeploymentContext = field(default_factory=DeploymentContext)
    credentials: CredentialsContext = field(default_factory=CredentialsContext)
    
    # Workflow metadata
    selected_workflow: Optional[Any] = None  # Will store WorkflowType enum
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            'workspace': {
                'workspace_id': self.workspace.workspace_id,
                'repository_id': self.workspace.repository_id,
                'topic_id': self.workspace.topic_id,
                'topic_name': self.workspace.topic_name,
                'branch_name': self.workspace.branch_name,
            },
            'technology': {
                'destination_technology': self.technology.destination_technology,
                'source_technology': self.technology.source_technology,
                'library_item_id': self.technology.library_item_id,
                'has_exact_template_match': self.technology.has_exact_template_match,
                'selected_library_item': self.technology.selected_library_item,
            },
            'schema': {
                'data_schema': self.schema.data_schema,
                'table_name': self.schema.table_name,
            },
            'code_generation': {
                'template_code': self.code_generation.template_code,
                'template_requirements': self.code_generation.template_requirements,
                'generated_code_draft': self.code_generation.generated_code_draft,
                'docs_content': self.code_generation.docs_content,
                'app_extract_dir': self.code_generation.app_extract_dir,
            },
            'deployment': {
                'application_name': self.deployment.application_name,
                'application_id': self.deployment.application_id,
                'application_path': self.deployment.application_path,
                'session_id': self.deployment.session_id,
                'deployment_id': self.deployment.deployment_id,
                'deployment_name': self.deployment.deployment_name,
            },
            'credentials': {
                'connection_credentials': self.credentials.connection_credentials,
                'env_var_names': self.credentials.env_var_names,
                'env_var_values': self.credentials.env_var_values,
                'translated_env_content': self.credentials.translated_env_content,
                'secret_variables': self.credentials.secret_variables,
            },
            'selected_workflow': self.selected_workflow.value if self.selected_workflow else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowContext':
        """Create context from dictionary."""
        context = cls()
        
        if 'workspace' in data:
            context.workspace = WorkspaceContext(**data['workspace'])
        if 'technology' in data:
            context.technology = TechnologyContext(**data['technology'])
        if 'schema' in data:
            context.schema = SchemaContext(**data['schema'])
        if 'code_generation' in data:
            context.code_generation = CodeGenerationContext(**data['code_generation'])
        if 'deployment' in data:
            context.deployment = DeploymentContext(**data['deployment'])
        if 'credentials' in data:
            context.credentials = CredentialsContext(**data['credentials'])
        
        # Handle selected_workflow enum conversion
        selected_workflow = data.get('selected_workflow')
        if selected_workflow and isinstance(selected_workflow, str):
            from .workflow_types import WorkflowType
            try:
                context.selected_workflow = WorkflowType(selected_workflow)
            except ValueError:
                context.selected_workflow = None
        
        return context
    
    def save_to_file(self, filename: str = "workflow_context.json") -> None:
        """Save context to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filename: str = "workflow_context.json") -> 'WorkflowContext':
        """Load context from JSON file."""
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)