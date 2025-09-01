# phase_sink_knowledge.py - Sink Knowledge Gathering Phase

from agents import RunConfig
from workflow_tools.contexts import WorkflowContext
from workflow_tools.services.knowledge_gatherer import KnowledgeGatheringService
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult


class SinkKnowledgePhase(BasePhase):
    """Handles sink knowledge gathering and application setup using unified service."""
    
    phase_name = "sink_knowledge"
    phase_description = "Gather sink knowledge and setup application"
    
    def __init__(self, context: WorkflowContext, run_config=None, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.run_config = run_config or RunConfig(workflow_name="Create Quix Sink (V2)")
        self.knowledge_service = KnowledgeGatheringService(context, self.run_config, debug_mode)
    
    async def execute(self) -> PhaseResult:
        """Gather knowledge about destination technology and set up application."""
        return await self.knowledge_service.gather_knowledge("sink")