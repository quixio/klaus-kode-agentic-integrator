# phase_sink_prerequisites.py - Sink Prerequisites Collection Phase

from workflow_tools.contexts import WorkflowContext
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.services.prerequisites_collector import PrerequisitesCollector


class SinkPrerequisitesCollectionPhase(BasePhase):
    """Handles workspace, source topic selection, and destination technology selection for sink workflows."""
    
    phase_name = "sink_prerequisites"
    phase_description = "Collect workspace, topic, and destination technology for sink workflow"
    
    def __init__(self, context: WorkflowContext, run_config=None, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.run_config = run_config
        self.prerequisites_collector = PrerequisitesCollector(context, debug_mode, run_config)
    
    async def execute(self) -> PhaseResult:
        """Execute the sink prerequisites collection using centralized service."""
        success = await self.prerequisites_collector.collect_prerequisites("sink")
        
        if success:
            return PhaseResult(success=True, message="Sink prerequisites collected successfully")
        else:
            return PhaseResult(success=False, message="Failed to collect sink prerequisites")