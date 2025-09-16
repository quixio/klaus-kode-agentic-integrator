"""Factory for creating workflows with dependency injection."""

from typing import List, Optional
from agents import RunConfig

from .phases.base.base_phase import BasePhase
from .service_container import ServiceContainer
from .contexts import WorkflowContext
from .workflow_types import WorkflowType

# Import all phase classes from organized structure
from .phases.sink.phase_sink_prerequisites import SinkPrerequisitesCollectionPhase
from .phases.source.phase_source_prerequisites import SourcePrerequisitesCollectionPhase
from .phases.sink.phase_sink_schema import SinkSchemaPhase
from .phases.sink.phase_sink_knowledge import SinkKnowledgePhase
from .phases.sink.phase_sink_generation import SinkGenerationPhase
from .phases.sink.phase_sink_sandbox import SinkSandboxPhase
from .phases.source.phase_source_knowledge import SourceKnowledgePhase
from .phases.source.phase_source_connection_testing import SourceConnectionTestingPhase
from .phases.source.phase_source_schema import SourceSchemaPhase
from .phases.source.phase_source_generation import SourceGenerationPhase
from .phases.source.phase_source_sandbox import SourceSandboxPhase
from .phases.shared.phase_deployment import DeploymentPhase
from .phases.shared.phase_monitoring import MonitoringPhase
from .phases.diagnose import (
    DiagnoseAppSelectionPhase,
    DiagnoseAppDownloadPhase,
    DiagnoseEditPhase,
    DiagnoseSandboxPhase,
    DiagnoseDeploymentSyncPhase
)


class WorkflowFactory:
    """Factory for creating workflow phases with proper dependency injection."""
    
    @staticmethod
    def register_services(container: ServiceContainer, context: WorkflowContext, 
                         run_config: RunConfig, debug_mode: bool = False) -> None:
        """Register all services in the container.
        
        Args:
            container: Service container to populate
            context: Workflow context
            run_config: Run configuration
            debug_mode: Whether debug mode is enabled
        """
        # Register core services
        container.register_instance('context', context)
        container.register_instance('run_config', run_config)
        container.register_instance('debug_mode', debug_mode)
        
        # Register sink workflow phases as factories (non-singletons for proper navigation)
        container.register('sink_prerequisites_phase', 
            lambda c: SinkPrerequisitesCollectionPhase(
                c.get('context'), c.get('run_config'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('sink_schema_phase',
            lambda c: SinkSchemaPhase(
                c.get('context'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('sink_knowledge_phase',
            lambda c: SinkKnowledgePhase(
                c.get('context'), c.get('run_config'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('sink_generation_phase',
            lambda c: SinkGenerationPhase(
                c.get('context'), c.get('run_config'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('sink_sandbox_phase',
            lambda c: SinkSandboxPhase(
                c.get('context'), c.get('sink_generation_phase'), c.get('debug_mode')
            ), singleton=False)
        
        # Register source workflow phases (non-singletons for proper navigation)
        container.register('source_prerequisites_phase',
            lambda c: SourcePrerequisitesCollectionPhase(
                c.get('context'), c.get('run_config'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('source_knowledge_phase',
            lambda c: SourceKnowledgePhase(
                c.get('context'), c.get('run_config'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('source_connection_testing_phase',
            lambda c: SourceConnectionTestingPhase(
                c.get('context'), c.get('run_config'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('source_schema_phase',
            lambda c: SourceSchemaPhase(
                c.get('context'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('source_generation_phase',
            lambda c: SourceGenerationPhase(
                c.get('context'), c.get('run_config'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('source_sandbox_phase',
            lambda c: SourceSandboxPhase(
                c.get('context'), c.get('source_generation_phase'), c.get('debug_mode')
            ), singleton=False)
        
        # Register shared phases (non-singletons for proper navigation)
        container.register('deployment_phase',
            lambda c: DeploymentPhase(
                c.get('context'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('monitoring_phase',
            lambda c: MonitoringPhase(
                c.get('context'), c.get('run_config'), c.get('debug_mode')
            ), singleton=False)
        
        # Register diagnose workflow phases (non-singletons for proper navigation)
        container.register('diagnose_app_selection_phase',
            lambda c: DiagnoseAppSelectionPhase(
                c.get('context'), c.get('run_config'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('diagnose_app_download_phase',
            lambda c: DiagnoseAppDownloadPhase(
                c.get('context'), c.get('run_config'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('diagnose_edit_phase',
            lambda c: DiagnoseEditPhase(
                c.get('context'), c.get('run_config'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('diagnose_sandbox_phase',
            lambda c: DiagnoseSandboxPhase(
                c.get('context'), c.get('debug_mode')
            ), singleton=False)
        
        container.register('diagnose_deployment_sync_phase',
            lambda c: DiagnoseDeploymentSyncPhase(
                c.get('context'), c.get('debug_mode')
            ), singleton=False)
    
    @staticmethod
    def create_sink_workflow(container: ServiceContainer) -> List[BasePhase]:
        """Create sink workflow phases.
        
        Args:
            container: Service container with registered services
            
        Returns:
            List of phases for sink workflow
        """
        return [
            container.get('sink_prerequisites_phase'),
            container.get('sink_schema_phase'),
            container.get('sink_knowledge_phase'),
            container.get('sink_generation_phase'),
            container.get('sink_sandbox_phase'),
            container.get('deployment_phase'),
            container.get('monitoring_phase')
        ]
    
    @staticmethod
    def create_source_workflow(container: ServiceContainer) -> List[BasePhase]:
        """Create source workflow phases.
        
        Args:
            container: Service container with registered services
            
        Returns:
            List of phases for source workflow
        """
        return [
            container.get('source_prerequisites_phase'),
            container.get('source_knowledge_phase'),
            container.get('source_connection_testing_phase'),
            container.get('source_schema_phase'),
            container.get('source_generation_phase'),
            container.get('source_sandbox_phase'),
            container.get('deployment_phase'),
            container.get('monitoring_phase')
        ]
    
    @staticmethod
    def create_diagnose_workflow(container: ServiceContainer) -> List[BasePhase]:
        """Create diagnose workflow phases.
        
        Args:
            container: Service container with registered services
            
        Returns:
            List of phases for diagnose workflow
        """
        return [
            container.get('diagnose_app_selection_phase'),
            container.get('diagnose_app_download_phase'),
            container.get('diagnose_edit_phase'),
            container.get('diagnose_sandbox_phase'),
            container.get('diagnose_deployment_sync_phase'),
            container.get('monitoring_phase')
        ]
    
    @staticmethod
    def create_workflow(workflow_type: WorkflowType, container: ServiceContainer) -> List[BasePhase]:
        """Create workflow phases based on type.
        
        Args:
            workflow_type: Type of workflow to create
            container: Service container with registered services
            
        Returns:
            List of phases for the specified workflow
            
        Raises:
            ValueError: If workflow type is not supported
        """
        if workflow_type == WorkflowType.SINK:
            return WorkflowFactory.create_sink_workflow(container)
        elif workflow_type == WorkflowType.SOURCE:
            return WorkflowFactory.create_source_workflow(container)
        elif workflow_type == WorkflowType.DIAGNOSE:
            return WorkflowFactory.create_diagnose_workflow(container)
        else:
            raise ValueError(f"Unsupported workflow type: {workflow_type}")
    
    @staticmethod
    def create_phase(phase_name: str, container: ServiceContainer) -> BasePhase:
        """Create a specific phase by name.
        
        Args:
            phase_name: Name of the phase to create
            container: Service container with registered services
            
        Returns:
            Phase instance
            
        Raises:
            KeyError: If phase is not registered
        """
        return container.get(phase_name)