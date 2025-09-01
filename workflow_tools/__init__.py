# workflow_tools/__init__.py - Package initialization with organized structure

# Core components (keep at root level)
from .contexts import WorkflowContext
from .common import printer, workflow_logger
from .workflow_types import WorkflowType, WorkflowInfo
from .service_container import ServiceContainer, get_global_container
from .workflow_factory import WorkflowFactory

# Import from organized subfolders
from .core.triage_agent import TriageAgent
from .core.placeholder_workflows import PlaceholderWorkflowFactory
from .core.prompt_manager import load_agent_instructions, load_task_prompt
from .integrations.credentials_parser import CredentialsParser

# Import all phases from the phases module
from .phases import (
    SinkPrerequisitesCollectionPhase,
    SourcePrerequisitesCollectionPhase,
    SinkSchemaPhase,
    SinkKnowledgePhase,
    SinkGenerationPhase,
    SinkSandboxPhase,
    SourceKnowledgePhase,
    SourceConnectionTestingPhase,
    SourceSchemaPhase,
    SourceGenerationPhase,
    SourceSandboxPhase,
    DeploymentPhase,
    MonitoringPhase,
)

__all__ = [
    'WorkflowContext',
    'printer',
    'workflow_logger',
    'WorkflowType',
    'WorkflowInfo',
    'ServiceContainer',
    'get_global_container',
    'WorkflowFactory',
    'TriageAgent',
    'PlaceholderWorkflowFactory',
    'CredentialsParser',
    'load_agent_instructions',
    'load_task_prompt',
    'SinkPrerequisitesCollectionPhase',
    'SourcePrerequisitesCollectionPhase',
    'SinkSchemaPhase',
    'SinkKnowledgePhase',
    'SinkGenerationPhase',
    'SinkSandboxPhase',
    'SourceKnowledgePhase',
    'SourceConnectionTestingPhase',
    'SourceSchemaPhase',
    'SourceGenerationPhase',
    'SourceSandboxPhase',
    'DeploymentPhase',
    'MonitoringPhase',
]