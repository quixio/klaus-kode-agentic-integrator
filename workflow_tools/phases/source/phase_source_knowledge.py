# phase_source_knowledge.py - Source Knowledge Gathering Phase

from agents import RunConfig
from workflow_tools.contexts import WorkflowContext
from workflow_tools.services.knowledge_gatherer import KnowledgeGatheringService
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult


class SourceKnowledgePhase(BasePhase):
    """Handles source knowledge gathering and application setup using unified service."""
    
    phase_name = "source_knowledge"
    phase_description = "Gather source knowledge and setup application"
    
    def __init__(self, context: WorkflowContext, run_config=None, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.run_config = run_config or RunConfig(workflow_name="Create Quix Source (V1)")
        self.knowledge_service = KnowledgeGatheringService(context, self.run_config, debug_mode)
    
    async def execute(self) -> PhaseResult:
        """Gather knowledge about source technology and set up application."""
        return await self.knowledge_service.gather_knowledge("source")