# phase_diagnose_edit.py - Code Editing Phase for Diagnose Workflow

import asyncio
from typing import Optional
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.services.claude_code_service import ClaudeCodeService
from workflow_tools.core.prompt_manager import prompt_manager
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.phases.shared.app_management import AppManager
from workflow_tools.core.interactive_menu import InteractiveMenu


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
            
            # If user provided requirements, ask if they want to edit code first
            if self.context.diagnose.get('user_requirements'):
                if await self._should_edit_code():
                    # Create session and edit code
                    if not await self._setup_and_edit():
                        return PhaseResult(success=False, message="Failed to edit code")
            
            return PhaseResult(success=True, message="Edit phase complete")
            
        except NavigationBackRequest:
            raise
        except Exception as e:
            printer.print(f"❌ Error during edit phase: {e}")
            return PhaseResult(success=False, message=f"Failed: {e}")
    
    async def _ask_for_optional_context(self) -> bool:
        """Ask if user wants to provide context before running."""
        printer.print("\n" + "="*50)
        printer.print("OPTIONAL CONTEXT")
        printer.print("="*50)
        
        # Clear screen for interactive menu
        InteractiveMenu.clear_terminal()
        
        # Create menu options
        options = [
            {'action': 'context', 'text': '📝 Yes, let me provide context'},
            {'action': 'run', 'text': '🚀 No, just run the application'},
            {'action': 'back', 'text': '⬅️ Go back'}
        ]
        
        # Use interactive menu
        menu = InteractiveMenu(
            title="Before running the application, would you like to provide any context\nabout what you're trying to achieve or issues you're experiencing?"
        )
        
        # Format function for display
        def format_option(opt):
            return opt['text']
        
        # Get user selection with arrow keys
        selected, index = menu.select_option(
            options,
            display_formatter=format_option,
            allow_back=False  # We handle back option manually
        )
        
        if selected is None or selected['action'] == 'back':
            raise NavigationBackRequest()
        elif selected['action'] == 'context':
            # Get context from user
            return await self._get_user_context()
        else:  # run
            return False  # Skip context
    
    async def _get_user_context(self) -> bool:
        """Get context or requirements from the user."""
        try:
            printer.print("\n" + "="*50)
            printer.print("PROVIDE CONTEXT")
            printer.print("="*50)
            
            printer.print("\nPlease describe what you want to do with this application.")
            printer.print("You can mention:")
            printer.print("  • Issues you're experiencing")
            printer.print("  • Features you want to add")
            printer.print("  • Improvements you'd like to make")
            printer.print("  • Questions about how it works")
            printer.print("")
            printer.print("Enter your requirements (press Enter twice when done, or 'b' to go back):")
            printer.print("")
            
            lines = []
            empty_line_count = 0
            
            while True:
                line = input()
                
                if line.lower() == 'b' and not lines:
                    raise NavigationBackRequest()
                
                if line == "":
                    empty_line_count += 1
                    if empty_line_count >= 2:
                        break
                    lines.append("")
                else:
                    empty_line_count = 0
                    lines.append(line)
            
            user_requirements = "\n".join(lines).strip()
            
            if not user_requirements:
                printer.print("⚠️ No requirements provided")
                return False
            
            # Store requirements
            self.context.diagnose['user_requirements'] = user_requirements
            
            printer.print("\n✅ Requirements captured:")
            printer.print("─" * 40)
            printer.print(user_requirements)
            printer.print("─" * 40)
            
            return True
            
        except NavigationBackRequest:
            raise
        except Exception as e:
            printer.print(f"❌ Error getting user context: {e}")
            return False
    
    async def _should_edit_code(self) -> bool:
        """Ask if user wants to edit code before running."""
        printer.print("\n" + "="*50)
        printer.print("CODE MODIFICATION")
        printer.print("="*50)
        
        # Clear screen for interactive menu
        InteractiveMenu.clear_terminal()
        
        # Create menu options
        options = [
            {'action': 'edit', 'text': '✏️ Edit the code first, then run'},
            {'action': 'run', 'text': '🚀 Run as-is and see what happens'},
            {'action': 'back', 'text': '⬅️ Go back'}
        ]
        
        # Use interactive menu
        menu = InteractiveMenu(title="Based on your requirements, would you like to:")
        
        # Format function for display
        def format_option(opt):
            return opt['text']
        
        # Get user selection with arrow keys
        selected, index = menu.select_option(
            options,
            display_formatter=format_option,
            allow_back=False  # We handle back option manually
        )
        
        if selected is None or selected['action'] == 'back':
            raise NavigationBackRequest()
        elif selected['action'] == 'edit':
            return True
        else:  # run
            return False
    
    async def _setup_and_edit(self) -> bool:
        """Setup session and edit code using Claude."""
        try:
            printer.print("\n" + "="*50)
            printer.print("EDITING CODE")
            printer.print("="*50)
            
            # Create IDE session using AppManager
            if not hasattr(self.context.deployment, 'session_id') or not self.context.deployment.session_id:
                printer.print("📋 Creating IDE session for editing...")
                if not await self.app_manager.create_ide_session():
                    printer.print("❌ Failed to create session")
                    return False
            
            printer.print("\n🤖 Using Claude to modify the application based on your requirements...")
            
            # Prepare the edit prompt
            edit_prompt = prompt_manager.load_task_prompt(
                "diagnose/diagnose_edit_code",
                app_name=self.context.workspace.app_name,
                user_requirements=self.context.diagnose.get('user_requirements', ''),
                app_analysis=self.context.diagnose.get('app_analysis', ''),
                log_analysis=self.context.diagnose.get('log_analysis', ''),  # Will be empty initially
                app_directory=self.context.workspace.app_directory
            )
            
            # Use Claude to edit the code
            success = await self.claude_service.generate_code_with_claude(
                user_prompt=edit_prompt,
                template_code=None,  # Not using template, editing existing code
                requirements_content=None,
                docs_content=None,
                is_edit_mode=True  # Important: this tells Claude to edit, not create from scratch
            )
            
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