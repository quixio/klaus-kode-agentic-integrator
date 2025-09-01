# phase_source_prerequisites.py - Source Prerequisites Collection Phase

from workflow_tools.common import WorkflowContext
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.services.prerequisites_collector import PrerequisitesCollector


class SourcePrerequisitesCollectionPhase(BasePhase):
    """Handles workspace, topic selection, and source technology selection for source workflows."""
    
    phase_name = "source_prerequisites"
    phase_description = "Collect source prerequisites"
    
    def __init__(self, context: WorkflowContext, run_config=None, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.run_config = run_config
        self.prerequisites_collector = PrerequisitesCollector(context, debug_mode, run_config)
    
    async def execute(self) -> PhaseResult:
        """Execute the source prerequisites collection using centralized service."""
        success = await self.prerequisites_collector.collect_prerequisites("source")
        
        if success:
            return PhaseResult(success=True, message="Source prerequisites collected successfully")
        else:
            return PhaseResult(success=False, message="Failed to collect source prerequisites")