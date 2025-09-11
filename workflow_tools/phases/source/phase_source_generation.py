# phase_source_generation.py - Source Code Generation Phase

import os
import yaml
from typing import Optional
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.services.claude_code_service import ClaudeCodeService
from workflow_tools.integrations import quix_tools


class SourceGenerationPhase(BasePhase):
    """Handles source code generation and review processes using Claude Code SDK."""
    
    phase_name = "source_generation"
    phase_description = "Generate source code"
    
    def __init__(self, context: WorkflowContext, run_config=None, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.run_config = run_config
        self.claude_code_service = ClaudeCodeService(context, debug_mode)
    
    async def execute(self) -> PhaseResult:
        """Execute the source code generation using Claude Code SDK with centralized caching."""
        # Phase header is already shown by base_phase
        # No need for additional header here
        
        try:
            # Initialize cache utils
            from workflow_tools.phases.shared.cache_utils import CacheUtils
            cache_utils = CacheUtils(self.context, self.debug_mode)
            
            # Get the app directory
            app_dir = self.context.code_generation.app_extract_dir
            if not app_dir or not os.path.exists(app_dir):
                printer.print("❌ Error: Application directory not found. Ensure knowledge gathering phase completed.")
                return PhaseResult(success=False, message="App directory not found")
            
            # Try to use centralized cached app generation
            cached_code = cache_utils.handle_cached_app_generation(workflow_type="source")
            if cached_code:
                # Store the cached code in context
                self.context.code_generation.generated_code_draft = cached_code
                printer.print("✅ Source code generation completed successfully (from cache)!")
                return PhaseResult(success=True, message="Phase completed successfully")
            
            # Check for backup from connection testing phase
            restored_code = cache_utils.restore_final_code_from_backup(app_dir)
            if restored_code:
                # User chose to use existing final code
                self.context.code_generation.generated_code_draft = restored_code
                
                # Cache the app directory for future use
                cache_utils.save_app_directory_to_cache(app_dir)
                
                return PhaseResult(success=True, message="Phase completed successfully")
            
            # Generate fresh code using Claude Code
            code, env_vars = await self.claude_code_service.generate_with_feedback_loop(
                workflow_type="source",
                app_dir=app_dir
            )
            
            if code:
                # Store the generated code in context
                self.context.code_generation.generated_code_draft = code
                
                # Clean up connection test backup if exists (we have new final code)
                cache_utils.cleanup_connection_test_backup(app_dir)
                
                # Cache the entire app directory for future use
                cache_utils.save_app_directory_to_cache(app_dir)
                printer.print("💾 Cached application directory for future use")
                
                printer.print("✅ Source code generation completed successfully!")
                return PhaseResult(success=True, message="Phase completed successfully")
            else:
                printer.print("❌ Code generation failed or was aborted.")
                return PhaseResult(success=False, message="Phase failed")
                
        except NavigationBackRequest:
            # Re-raise navigation requests to be handled by phase orchestrator
            raise
        except Exception as e:
            printer.print(f"❌ Error in source code generation: {str(e)}")
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
    
