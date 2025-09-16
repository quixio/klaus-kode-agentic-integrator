# phase_diagnose_edit.py - Code Editing Phase for Diagnose Workflow

import asyncio
from typing import Optional
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.services.claude_code_service import ClaudeCodeService
from workflow_tools.core.prompt_manager import prompt_manager
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.phases.shared.app_management import AppManager
from workflow_tools.core.questionary_utils import select, text
from workflow_tools.common import clear_screen, get_user_approval
from workflow_tools.core.navigation import NavigationRequest, DiagnoseWorkflowSteps


class DiagnoseEditPhase(BasePhase):
    """Handles user context gathering and optional code editing for the diagnose workflow."""
    
    phase_name = "diagnose_edit"
    phase_description = "Gather context and optionally edit code"
    
    def __init__(self, context: WorkflowContext, run_config=None, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.run_config = run_config
        self.claude_service = ClaudeCodeService(context, debug_mode)
        self.app_manager = AppManager(context, debug_mode)
    
    async def execute(self) -> PhaseResult:
        """Execute the edit phase based on user's initial choice."""
        try:
            # Initialize diagnose context if not exists
            if not hasattr(self.context, 'diagnose'):
                self.context.diagnose = {}
            
            # Check initial choice from download phase
            initial_choice = self.context.diagnose.get('initial_choice', 'context')
            
            if initial_choice == 'run':
                # User chose to run immediately - skip directly to running without asking again
                self.context.diagnose['user_requirements'] = ""
                return PhaseResult(success=True, message="Proceeding to run application directly")
            else:
                # User chose to provide context first (option 2 from download phase)
                if not await self._get_user_context():
                    return PhaseResult(success=False, message="Failed to get user context")
            
            # If user provided requirements, directly apply them with Claude
            if self.context.diagnose.get('user_requirements'):
                printer.print("\n🤖 Applying your requirements using Claude Code...")
                # Create session and edit code
                if not await self._setup_and_edit():
                    return PhaseResult(success=False, message="Failed to edit code")
            
            return PhaseResult(success=True, message="Edit phase complete")
            
        except NavigationBackRequest:
            raise
        except Exception as e:
            printer.print(f"❌ Error during edit phase: {e}")
            return PhaseResult(success=False, message=f"Failed: {e}")
    
    
    async def _get_user_context(self) -> bool:
        """Get context or requirements from the user."""
        try:
            printer.print_section_header("Provide Context", icon="💭", style="cyan")
            
            printer.print("Please describe what you want to do with this application.")
            printer.print("\nYou can mention:")
            printer.print("  • Issues you're experiencing")
            printer.print("  • Features you want to add")
            printer.print("  • Improvements you'd like to make")
            printer.print("  • Questions about how it works")
            printer.print("\n(Press Esc then Enter to submit when done)")
            printer.print("")

            # Use questionary text input with multiline
            user_requirements = text(
                "Enter your requirements:",
                multiline=True
            )

            if user_requirements is None:  # User cancelled
                # Navigate back to previous choice
                self.context.navigation_request = NavigationRequest(
                    target_step=DiagnoseWorkflowSteps.CHOOSE_ACTION,
                    message="User cancelled providing context"
                )
                raise NavigationBackRequest()
            
            if not user_requirements:
                printer.print("⚠️ No requirements provided")
                return False
            
            # Store requirements
            self.context.diagnose['user_requirements'] = user_requirements
            
            printer.print("\n✅ Requirements captured:")
            printer.print_divider()
            printer.print_code(user_requirements, language="text")
            printer.print_divider()
            
            return True
            
        except NavigationBackRequest:
            raise
        except Exception as e:
            printer.print(f"❌ Error getting user context: {e}")
            return False
    
    
    async def _setup_and_edit(self) -> bool:
        """Setup session and edit code using Claude."""
        try:
            printer.print_section_header("Applying Requirements", icon="💻", style="cyan")
            
            # Create IDE session using AppManager
            if not hasattr(self.context.deployment, 'session_id') or not self.context.deployment.session_id:
                printer.print("📋 Creating IDE session for editing...")
                if not await self.app_manager.create_ide_session():
                    printer.print("❌ Failed to create session")
                    return False
            
            printer.print("\n🤖 Using Claude to modify the application based on your requirements...")
            
            # Prepare the edit prompt
            edit_prompt = prompt_manager.load_task_prompt(
                "diagnose_edit_code",
                app_name=self.context.workspace.app_name,
                user_requirements=self.context.diagnose.get('user_requirements', ''),
                app_analysis=self.context.diagnose.get('app_analysis', ''),
                log_analysis=self.context.diagnose.get('log_analysis', ''),  # Will be empty initially
                app_directory=self.context.workspace.app_directory
            )
            
            # Use Claude to edit the code
            code_result, env_vars = await self.claude_service.generate_code(
                user_prompt=edit_prompt,
                app_dir=self.context.workspace.app_directory,
                workflow_type='diagnose'
            )

            success = code_result is not None
            
            if not success:
                printer.print("❌ Failed to edit code with Claude")
                return False
            
            printer.print("✅ Code edited successfully")
            
            # Store that we've made edits
            self.context.diagnose['code_edited'] = True
            
            return True
            
        except Exception as e:
            printer.print(f"❌ Error editing code: {e}")
            return False