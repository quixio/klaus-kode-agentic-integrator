# phase_diagnose_sandbox.py - Sandbox Testing Phase for Diagnose Workflow

import asyncio
import os
from typing import Optional, Tuple
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.services.sandbox_error_handler import SandboxErrorHandler
from workflow_tools.services.debug_analyzer import DebugAnalyzer
from workflow_tools.services.claude_code_service import ClaudeCodeService
from workflow_tools.phases.shared.env_var_management import EnvVarManager
from workflow_tools.phases.shared.app_management import AppManager
from workflow_tools.integrations import quix_tools
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.core.prompt_manager import prompt_manager
from workflow_tools.core.questionary_utils import select, text
from workflow_tools.common import clear_screen, get_user_approval


class DiagnoseSandboxPhase(BasePhase):
    """Runs and tests the application, with debug cycles if needed."""
    
    phase_name = "diagnose_sandbox"
    phase_description = "Test application in sandbox"
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.app_manager = AppManager(context, debug_mode)
        self.debug_analyzer = DebugAnalyzer(context, debug_mode)
        self.error_handler = SandboxErrorHandler(context, debug_mode)
        self.env_var_manager = EnvVarManager(context, debug_mode)
        self.claude_service = ClaudeCodeService(context, debug_mode)
        
        # Track state
        self.first_error_handled = False
    
    async def execute(self) -> PhaseResult:
        """Execute the sandbox testing phase with debug cycles."""
        try:
            printer.print("\n" + "="*50)
            printer.print("SANDBOX TESTING")
            printer.print("="*50)
            
            # Ensure we have a session
            if not await self._ensure_session():
                return PhaseResult(success=False, message="Failed to create/verify session")
            
            # Main test and debug loop
            max_iterations = 20  # Safety limit
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                # Run the application
                success, auto_continue = await self._run_and_debug_cycle()
                
                if success:
                    # Application ran successfully - offer follow-up
                    follow_up_result = await self._handle_follow_up()
                    if follow_up_result:
                        # User made changes, continue testing
                        printer.print("\n🔄 Looping back to test the updated application...")
                        continue
                    else:
                        # User is satisfied
                        return PhaseResult(success=True, message="Application tested successfully")
                else:
                    # Check if we should automatically continue (e.g., after Claude fix)
                    if auto_continue:
                        printer.print("\n🔄 Retrying with the applied fix...")
                        continue
                    
                    # Otherwise ask user if they want to continue debugging
                    if not get_user_approval("Would you like to continue debugging?"):
                        return PhaseResult(success=False, message="Debugging stopped by user")
            
            printer.print(f"\n⚠️ Maximum iterations ({max_iterations}) reached.")
            return PhaseResult(success=False, message="Maximum iterations reached")
            
        except NavigationBackRequest:
            raise
        except Exception as e:
            printer.print(f"❌ Error during sandbox testing: {e}")
            return PhaseResult(success=False, message=f"Failed: {e}")
    
    async def _ensure_session(self) -> bool:
        """Ensure we have an active IDE session."""
        try:
            if hasattr(self.context.deployment, 'session_id') and self.context.deployment.session_id:
                printer.print(f"✅ Using existing session: {self.context.deployment.session_id}")
                return True
            
            printer.print("📋 Creating IDE session for testing...")
            # For diagnose workflow, use the app's existing variables
            return await self.app_manager.create_ide_session(use_app_variables=True)
            
        except Exception as e:
            printer.print(f"❌ Error ensuring session: {e}")
            return False
    
    async def _run_and_debug_cycle(self) -> tuple[bool, bool]:
        """Run the application once and handle any errors.
        
        Returns:
            (success, should_continue_automatically)
            - success: True if app ran successfully  
            - should_continue_automatically: True if we should retry without asking user
        """
        try:
            printer.print("\n🧪 Preparing to test existing application...")
            
            app_dir = self.context.workspace.app_directory
            
            # Ensure code_generation context exists for debug analyzer
            if not hasattr(self.context, 'code_generation'):
                from types import SimpleNamespace
                self.context.code_generation = SimpleNamespace()
            self.context.code_generation.app_extract_dir = app_dir
            
            # Check if this is the first run (files not uploaded yet)
            files_uploaded = self.context.diagnose.get('files_uploaded', False) if hasattr(self.context, 'diagnose') else False
            
            # Check if we have edited code that needs uploading
            code_edited = hasattr(self.context, 'diagnose') and self.context.diagnose.get('code_edited', False)
            
            # Upload files on first run OR if code has been edited
            if not files_uploaded or code_edited:
                if not files_uploaded:
                    printer.print("  - Uploading application files (first run)...")
                else:
                    printer.print("  - Uploading edited code...")
                    
                upload_success = await quix_tools.update_all_session_files_from_local(
                    self.context.workspace.workspace_id,
                    self.context.deployment.session_id,
                    app_dir
                )
                
                if not upload_success:
                    printer.print("❌ Failed to upload code files")
                    return False, False
                
                # Mark files as uploaded
                if not hasattr(self.context, 'diagnose'):
                    self.context.diagnose = {}
                self.context.diagnose['files_uploaded'] = True
                
                # Reset the code_edited flag if it was set
                if code_edited:
                    self.context.diagnose['code_edited'] = False
                
                # Always install dependencies after uploading files
                printer.print("  - Installing dependencies...")
                await quix_tools.setup_session(
                    self.context.workspace.workspace_id,
                    self.context.deployment.session_id,
                    force=True
                )
            else:
                printer.print("  - Application files already uploaded, no changes to sync")
            
            printer.print("✅ Sandbox configured")
            
            # Run the code
            printer.print("\n🚀 Running application...")
            printer.print("   (Collecting logs for 60 seconds...)")
            logs = await quix_tools.run_code_in_session_with_timeout(
                self.context.workspace.workspace_id,
                self.context.deployment.session_id,
                "main.py",
                timeout_seconds=60  # Increased from 30 to give apps more time to initialize
            )
            
            # Analyze logs using centralized error handler
            has_error, is_timeout_error, has_success = self.error_handler.analyze_logs(
                logs, 
                workflow_type="diagnose"
            )
            
            # Display logs
            self.error_handler.display_logs(logs, has_error)
            
            # Determine execution status with AI
            execution_status = await self.error_handler.determine_execution_status_with_ai(
                logs=logs,
                test_objective="Testing the application based on user requirements",
                workflow_type="diagnose",
                code_context=None,
                is_connection_test=False
            )
            
            # Store logs for potential future use
            if not hasattr(self.context, 'diagnose'):
                self.context.diagnose = {}
            self.context.diagnose['last_logs'] = logs
            
            if execution_status in ['success', 'partial_success']:
                printer.print("\n✅ Application test successful!")

                # Pause to let user review the success analysis
                printer.print("")
                printer.print("📋 Log analysis complete. Press Enter to continue...")
                try:
                    input()
                except KeyboardInterrupt:
                    printer.print("\n⚠️ Interrupted. Continuing anyway...")

                return True, False  # Success, no auto-continue needed
            
            # Handle errors
            if execution_status == 'error':
                # For diagnose workflow, on first error automatically try Claude fix
                if not self.first_error_handled:
                    self.first_error_handled = True
                    printer.print("\n🔧 Automatically attempting to fix the error with Claude...")
                    
                    # Use centralized debug analyzer
                    action, fixed_code = await self.debug_analyzer.interactive_debug_workflow(
                        code=self._read_main_py(),
                        error_logs=logs,
                        workflow_type="diagnose",
                        is_timeout_error=is_timeout_error,
                        is_connection_test=False,
                        auto_debug_attempt=1  # Trigger auto-fix on first attempt
                    )
                else:
                    # Show interactive debug menu for subsequent errors
                    action, fixed_code = await self.debug_analyzer.interactive_debug_workflow(
                        code=self._read_main_py(),
                        error_logs=logs,
                        workflow_type="diagnose",
                        is_timeout_error=is_timeout_error,
                        is_connection_test=False,
                        auto_debug_attempt=0  # Manual mode
                    )
                
                # Handle the debug action
                if action == 'abort':
                    return False, False  # Don't continue, ask user
                elif action == 'back':
                    raise NavigationBackRequest()
                elif action == 'fixed_in_ide':
                    # User fixed it themselves, retry automatically
                    return False, True  # Will retry automatically
                elif action == 'retry' and fixed_code:
                    # Apply the fix
                    main_py_path = os.path.join(app_dir, "main.py")
                    with open(main_py_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_code)
                    printer.print("✅ Applied fix to code")
                    # Mark that code has been edited so it gets uploaded on next run
                    if not hasattr(self.context, 'diagnose'):
                        self.context.diagnose = {}
                    self.context.diagnose['code_edited'] = True
                    return False, True  # Will retry automatically (no need to ask)
                
            return False, False  # Default: don't auto-continue
            
        except Exception as e:
            printer.print(f"❌ Error during run cycle: {e}")
            return False, False
    
    
    def _read_main_py(self) -> Optional[str]:
        """Read the main.py file from the app directory."""
        try:
            main_py_path = os.path.join(self.context.workspace.app_directory, "main.py")
            if os.path.exists(main_py_path):
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # Try app.py as alternative
            app_py_path = os.path.join(self.context.workspace.app_directory, "app.py")
            if os.path.exists(app_py_path):
                with open(app_py_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            return None
        except Exception:
            return None
    
    async def _handle_follow_up(self) -> bool:
        """Handle follow-up after successful run. Returns True if user wants to continue."""
        printer.print_section_header("Success - Follow Up", icon="✅", style="green")
        
        printer.print("\n✅ The application is running successfully!")
        
        # Pause to let user review the logs
        printer.print("\nPress any key to continue...")
        import sys
        import termios
        import tty
        if sys.stdin.isatty():
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        # Clear screen for menu
        clear_screen()

        printer.print("✅ The application is running successfully!\n")
        printer.print("Would you like to:")
        printer.print("")

        choices = [
            {'name': '🔧 Make additional improvements or add features', 'value': 'improve'},
            {'name': '✅ Proceed to deployment', 'value': 'deploy'}
        ]

        selected = select("", choices, show_border=False)

        if selected == 'improve':
            # Get additional requirements
            return await self._get_and_apply_follow_up()
        else:  # deploy
            return False  # Done, proceed to deployment
    
    async def _get_and_apply_follow_up(self) -> bool:
        """Get follow-up requirements and apply them."""
        try:
            printer.print_section_header("Additional Improvements", icon="🔧", style="cyan")
            
            printer.print("Describe what you'd like to add or improve:")
            printer.print("(Press Esc then Enter to submit when done)")
            printer.print("")

            # Use questionary text input with multiline
            requirements = text(
                "Enter your requirements:",
                multiline=True
            )

            if requirements is None:  # User cancelled
                return False

            requirements = requirements.strip()
            
            if not requirements:
                printer.print("⚠️ No requirements provided")
                return False
            
            # Apply changes using Claude
            printer.print("\n🤖 Implementing improvements with Claude...")
            
            # Prepare follow-up prompt
            try:
                # Ensure diagnose context exists before accessing it
                if not hasattr(self.context, 'diagnose'):
                    self.context.diagnose = {}
                
                # Load the cached app analysis if available
                app_analysis = self.context.diagnose.get('app_analysis', '')
                if not app_analysis:
                    # Try to load from cache if not in context
                    from workflow_tools.core.working_directory import WorkingDirectory
                    app_name = self.context.workspace.app_name
                    analysis_file_path = WorkingDirectory.get_cached_analysis_path("diagnose", app_name)
                    if os.path.exists(analysis_file_path):
                        with open(analysis_file_path, 'r', encoding='utf-8') as f:
                            app_analysis = f.read()
                            self.context.diagnose['app_analysis'] = app_analysis
                
                if not app_analysis:
                    app_analysis = "No application analysis available. Please analyze the code structure and functionality based on the files in the directory."
                    
                follow_up_prompt = prompt_manager.load_task_prompt(
                    "diagnose_follow_up",  # Fixed path - no subdirectory
                    app_name=self.context.workspace.app_name,
                    previous_changes=self.context.diagnose.get('user_requirements', 'Initial implementation'),
                    user_requirements=requirements,
                    app_directory=self.context.workspace.app_directory,
                    app_analysis=app_analysis
                )
            except Exception as e:
                printer.print(f"❌ Error loading follow-up prompt: {e}")
                return False
            
            # Use Claude to implement changes
            printer.print("\n📝 Calling Claude to implement changes...")
            
            # Call Claude with the correct parameters
            generated_code, env_vars = await self.claude_service.generate_code(
                user_prompt=follow_up_prompt,
                app_dir=self.context.workspace.app_directory,
                workflow_type="diagnose"  # Using diagnose as the workflow type
            )
            
            success = generated_code is not None
            
            if success:
                printer.print("✅ Improvements implemented")
                # Ensure diagnose context exists
                if not hasattr(self.context, 'diagnose'):
                    self.context.diagnose = {}
                # Update requirements for next iteration
                self.context.diagnose['user_requirements'] = requirements
                # Mark that code has been edited so it gets uploaded on next run
                self.context.diagnose['code_edited'] = True
                return True
            else:
                printer.print("❌ Failed to implement improvements")
                return False
                
        except Exception as e:
            printer.print(f"❌ Error implementing follow-up: {e}")
            return False