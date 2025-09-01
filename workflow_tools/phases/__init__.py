# phases/__init__.py
"""Workflow phases organized by type."""

# Import all phases for easy access
from .base.base_phase import BasePhase, PhaseResult

from .sink.phase_sink_prerequisites import SinkPrerequisitesCollectionPhase
from .sink.phase_sink_schema import SinkSchemaPhase
from .sink.phase_sink_knowledge import SinkKnowledgePhase
from .sink.phase_sink_generation import SinkGenerationPhase
from .sink.phase_sink_sandbox import SinkSandboxPhase

from .source.phase_source_prerequisites import SourcePrerequisitesCollectionPhase
from .source.phase_source_schema import SourceSchemaPhase
from .source.phase_source_knowledge import SourceKnowledgePhase
from .source.phase_source_generation import SourceGenerationPhase
from .source.phase_source_connection_testing import SourceConnectionTestingPhase
from .source.phase_source_sandbox import SourceSandboxPhase

from .shared.phase_deployment import DeploymentPhase
from .shared.phase_monitoring import MonitoringPhase

__all__ = [
    # Base classes
    'BasePhase', 'PhaseResult',
    
    # Sink phases
    'SinkPrerequisitesCollectionPhase',
    'SinkSchemaPhase',
    'SinkKnowledgePhase', 
    'SinkGenerationPhase',
    'SinkSandboxPhase',
    
    # Source phases
    'SourcePrerequisitesCollectionPhase',
    'SourceSchemaPhase',
    'SourceKnowledgePhase',
    'SourceGenerationPhase',
    'SourceConnectionTestingPhase',
    'SourceSandboxPhase',
    
    # Shared phases
    'DeploymentPhase',
    'MonitoringPhase',
]