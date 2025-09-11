# phase_sink_generation.py - Sink Code Generation and Review Phase

import os
import yaml
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.services.claude_code_service import ClaudeCodeService


class SinkGenerationPhase(BasePhase):
    """Handles code generation and review processes using Claude Code SDK."""
    
    phase_name = "sink_generation"
    phase_description = "Generate sink code"
    
    def __init__(self, context: WorkflowContext, run_config=None, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.run_config = run_config
        self.claude_code_service = ClaudeCodeService(context, debug_mode)
    
    async def execute(self) -> PhaseResult:
        """Generates code using Claude Code SDK with centralized caching."""
        # Phase header is already shown by base_phase
        # No need for additional header here
        
        # Initialize cache utils
        from workflow_tools.phases.shared.cache_utils import CacheUtils
        cache_utils = CacheUtils(self.context, self.debug_mode)
        
        # Try to use centralized cached app generation
        cached_code = cache_utils.handle_cached_app_generation(workflow_type="sink")
        if cached_code:
            # Store the cached code in context
            self.context.code_generation.generated_code_draft = cached_code
            printer.print("✅ Sink code generation completed successfully (from cache)!")
            return PhaseResult(success=True, message="Phase completed successfully")
        
        # Get the app directory where Claude Code will work
        app_dir = self.context.code_generation.app_extract_dir
        if not app_dir or not os.path.exists(app_dir):
            printer.print("❌ Error: Application directory not found. Ensure knowledge gathering phase completed.")
            return PhaseResult(success=False, message="App directory not found")
        
        # Use Claude Code to generate the sink application
        code, env_vars = await self.claude_code_service.generate_with_feedback_loop(
            workflow_type="sink",
            app_dir=app_dir
        )
        
        if code:
            # Store the generated code in context
            self.context.code_generation.generated_code_draft = code
            
            # Note: Environment variable collection is now handled in the sandbox phase
            # using the app.yaml as the source of truth with field type display and modification
            
            printer.print("✅ Sink code generation completed successfully!")
            return PhaseResult(success=True, message="Phase completed successfully")
        else:
            printer.print("❌ Code generation failed or was aborted.")
            return PhaseResult(success=False, message="Phase failed")
    
    async def debug_and_fix(self, current_code: str, error_logs: str) -> str:
        """Debug and fix code using Claude Code SDK.
        
        This method is called by the sandbox phase when errors are detected.
        
        Args:
            current_code: The code that produced errors
            error_logs: The error logs from running the code
            
        Returns:
            Fixed code or None if fix failed
        """
        app_dir = self.context.code_generation.app_extract_dir
        if not app_dir:
            printer.print("❌ Error: Application directory not found for debugging.")
            return None
        
        return await self.claude_code_service.debug_code(
            error_logs=error_logs,
            app_dir=app_dir,
            current_code=current_code
        )