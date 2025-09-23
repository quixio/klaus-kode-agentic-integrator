# phase_source_sandbox.py - Source Sandbox Testing and Debugging Phase

import os
import random
import string
import re
from typing import List
from workflow_tools.common import WorkflowContext, printer, get_user_approval
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.integrations.credential_mapper import CredentialFieldMapper
from workflow_tools.integrations import quix_tools
from workflow_tools.services import SandboxErrorHandler, DebugAnalyzer
from workflow_tools.core.url_builder import QuixPortalURLBuilder

class SourceSandboxPhase(BasePhase):
    """Handles source sandbox testing and debugging."""
    
    phase_name = "source_sandbox"
    phase_description = "Test in sandbox"
    
    def __init__(self, context: WorkflowContext, generation_phase, debug_mode: bool = False):
        self.context = context
        self.generation_phase = generation_phase  # Reference to GenerationPhase for code regeneration
        self.debug_mode = debug_mode
        self.credential_mapper = CredentialFieldMapper(debug_mode)
        self.debug_analyzer = DebugAnalyzer(context, debug_mode)
    
    def _create_production_code(self, code: str) -> str:
        """Create production-ready code by removing test limits.
        
        For source applications, this typically means:
        - Removing any test iteration limits
        - Ensuring continuous data production
        - Removing debug print statements if needed
        """
        original_code = code
        
        # For source apps, we might have different patterns to clean up
        # Example: while iterations < 100: -> while True:
        test_limit_pattern = r'while\s+iterations?\s*<\s*\d+'
        production_code = re.sub(test_limit_pattern, 'while True', code)
        
        # Remove any count limits in loops
        count_limit_pattern = r'for\s+_\s+in\s+range\s*\(\s*\d+\s*\)'
        production_code = re.sub(count_limit_pattern, 'while True', production_code)
        
        # Log the changes if any modifications were made
        if production_code != original_code:
            printer.print("  - Preparing production-ready code (removing test limits)")
            
            # Show what changed
            if test_limit_pattern in original_code:
                printer.print("    - Removed iteration limits from while loops")
            if count_limit_pattern in original_code:
                printer.print("    - Removed count limits from for loops")
        
        return production_code
    
    async def execute(self) -> PhaseResult:
        """Configures the sandbox, runs the code, and handles success or failure."""
        printer.print("\n--- Phase 2: Sandbox Testing ---")

        # Check if session_id is missing (happens when connection testing is skipped)
        if not self.context.deployment.session_id:
            printer.print("🔄 No IDE session found. Creating a new session...")
            
            # Create a new IDE session
            session_result = await quix_tools.manage_session(
                action=quix_tools.SessionAction.start,
                workspace_id=self.context.workspace.workspace_id,
                application_id=self.context.deployment.application_id,
                branch_name=self.context.workspace.branch_name
            )
            if not session_result or 'sessionId' not in session_result:
                printer.print("❌ Failed to start IDE session.")
                return PhaseResult(success=False, message="Failed to create IDE session")
            
            self.context.deployment.session_id = session_result['sessionId']
            printer.print(f"✅ Created IDE session: {self.context.deployment.session_id}")

        # Check required context fields with specific error messages
        missing_fields = []
        if not self.context.workspace.workspace_id:
            missing_fields.append("workspace_id")
        if not self.context.deployment.application_id:
            missing_fields.append("application_id")
        if not self.context.deployment.session_id:
            missing_fields.append("session_id")
        if not self.context.code_generation.generated_code_draft:
            missing_fields.append("generated_code_draft")
        
        if missing_fields:
            printer.print(f"🛑 Critical context missing for sandbox test: {', '.join(missing_fields)}")
            printer.print("Expected context fields:")
            printer.print(f"  - workspace_id: '{self.context.workspace.workspace_id}'")
            printer.print(f"  - application_id: '{self.context.deployment.application_id}'")
            printer.print(f"  - session_id: '{self.context.deployment.session_id}'")
            printer.print(f"  - generated_code_draft: {'Present' if self.context.code_generation.generated_code_draft else 'Missing'}")
            printer.print(f"  - env_var_values: {len(self.context.credentials.env_var_values) if self.context.credentials.env_var_values else 0} variables")
            return PhaseResult(success=False, message="Phase failed")
        
        printer.print("✅ Verified context requirements")

        # Skip redundant approval - already approved in generation phase
        printer.print("📋 Proceeding to sandbox test (code already approved)...")
        
        # Log the application URL for reference
        url_builder = QuixPortalURLBuilder()
        branch = self.context.workspace.branch_name or "main"
        app_url = url_builder.get_application_url(
            workspace=self.context.workspace.workspace_id,
            application_name=self.context.deployment.application_name,
            branch=branch
        )
        printer.print(f"🔗 Running sandbox test in application: {app_url}")
        
        # Initialize EnvVarManager - will be used throughout retries
        from workflow_tools.phases.shared.env_var_management import EnvVarManager
        env_var_manager = EnvVarManager(self.context, run_config=None, debug_mode=self.debug_mode)
        
        # Only collect environment variables on first run (not during auto-debug retries)
        # Auto-debug should reuse the same variables unless new ones are added
        env_vars_collected_initially = False
        
        retry_count = 0
        # Make max retries configurable via environment variable, default to 10
        max_retries = int(os.getenv('QUIX_SANDBOX_MAX_RETRIES', '10'))
        
        while retry_count < max_retries:
            try:
                if retry_count == 0:
                    printer.print(f"\n🚀 Configuring sandbox...")
                else:
                    printer.print(f"\n🔁 Retrying sandbox configuration (Attempt {retry_count + 1}/{max_retries})")
                
                # 1. Update all application files (main.py, requirements.txt, app.yaml)
                printer.print("  Uploading application files to Quix IDE...")
                
                # First write the generated code to the local main.py file
                main_py_path = os.path.join(self.context.code_generation.app_extract_dir, "main.py")
                with open(main_py_path, 'w', encoding='utf-8') as f:
                    f.write(self.context.code_generation.generated_code_draft)
                
                # Use centralized function to upload all files
                files_updated = await quix_tools.update_all_session_files_from_local(
                    self.context.workspace.workspace_id,
                    self.context.deployment.session_id,
                    self.context.code_generation.app_extract_dir
                )
                if not files_updated:
                    printer.print("  - ⚠️ Some files could not be updated, but continuing...")
                
                # 2. Install dependencies from requirements.txt
                # Note: requirements.txt has already been uploaded by update_all_session_files_from_local
                printer.print("  Installing dependencies...")
                setup_result = await quix_tools.setup_session(self.context.workspace.workspace_id, self.context.deployment.session_id, force=True)
                if self.debug_mode:
                    printer.print_debug(f"  - Setup result (truncated): {repr(setup_result[:200]) if setup_result else 'None'}...")

                # 3. Synchronize variables - Smart sync that preserves manual updates
                # Note: env_var_manager is already created and collection already done before the retry loop
                
                # Detect any additional variables used in the generated code
                detected_env_vars = env_var_manager.detect_environment_variables(self.context.code_generation.generated_code_draft)
                if detected_env_vars and self.debug_mode:
                    printer.print_debug(f"  - Variables detected in code: {detected_env_vars}")
                
                # Use centralized smart sync - preserves existing vars by default
                await env_var_manager.sync_or_update_app_variables(
                    detected_code_vars=detected_env_vars,
                    force_update=False  # Don't overwrite existing variables
                )
                
                # 4. Prepare session variables from the already-collected values in app.yaml
                printer.print_verbose("  Preparing session variables from app.yaml...")
                session_env_vars, session_secrets = env_var_manager.prepare_session_variables()
                
                if self.debug_mode:
                    printer.print_debug(f"  - Available env vars: {list(self.context.credentials.env_var_values.keys())}")
                    printer.print_debug(f"  - Final session_env_vars: {list(session_env_vars.keys())}")
                    printer.print_debug(f"  - Final session_secrets: {list(session_secrets.keys())} (values hidden)")
                
                # Update session with the variables
                update_result = await quix_tools.update_session_environment(
                    self.context.workspace.workspace_id, 
                    self.context.deployment.session_id, 
                    environment_variables=session_env_vars if session_env_vars else None,
                    secrets=session_secrets if session_secrets else None
                )
                if self.debug_mode:
                    printer.print_debug(f"  - Update result:\n{quix_tools.pretty_json(update_result)}")
                printer.print("✅ Sandbox configured")

                # 5. Run the code
                printer.print("\n🧪 Running test...")
                # Use the centralized function with timeout for continuous source apps
                logs = await quix_tools.run_code_in_session_with_timeout(
                    self.context.workspace.workspace_id,
                    self.context.deployment.session_id,
                    "main.py",
                    timeout_seconds=30
                )
                
                # Use centralized error handler with context for AI analysis
                error_handler = SandboxErrorHandler(self.context, self.debug_mode)
                
                # Analyze logs
                has_error, is_timeout_error, has_success = error_handler.analyze_logs(logs, workflow_type="source")
                
                # Display logs
                error_handler.display_logs(logs, has_error)
                
                # Determine overall status using AI analysis when appropriate
                execution_status = await error_handler.determine_execution_status_with_ai(
                    logs=logs,
                    test_objective="Testing the source application to ensure it successfully retrieves and publishes data",
                    workflow_type="source",
                    code_context=self.context.code_generation.generated_code_draft,
                    is_connection_test=False
                )
                
                if execution_status == 'error':
                    # Create a callback to run fixed code and get new logs
                    async def run_fixed_code_callback(fixed_code):
                        """Run the fixed code in the session and return logs."""
                        # Update the session with fixed code
                        await quix_tools.update_session_file(
                            self.context.workspace.workspace_id,
                            self.context.deployment.session_id,
                            "main.py",
                            fixed_code
                        )
                        # Run the code and get logs
                        new_logs = await quix_tools.run_code_in_session_with_timeout(
                            self.context.workspace.workspace_id,
                            self.context.deployment.session_id,
                            "main.py",
                            timeout_seconds=30
                        )
                        return new_logs

                    # Use centralized debug analyzer with callback for auto-testing
                    current_code = self.context.code_generation.generated_code_draft
                    action, fixed_code = await self.debug_analyzer.handle_debug_workflow(
                        code=current_code,
                        error_logs=logs,
                        workflow_type="source",
                        is_timeout_error=is_timeout_error,
                        is_connection_test=False,
                        run_code_callback=run_fixed_code_callback
                    )
                    
                    # Handle the action returned by debug analyzer
                    # Note: 'regenerate_with_fix' action removed - code_generator no longer exists
                    # Note: 'manual_feedback' action no longer used - option 2 now sends feedback directly to Claude Code
                    # and returns 'claude_fixed' action instead
                        
                    if action == 'manual_fix':
                        # User wants to fix code manually in IDE and retry
                        printer.print("🔄 Running your manually fixed code from the IDE...")
                        # Just retry - the code in the IDE has been manually fixed
                        retry_count += 1
                        # Continue to next iteration to retry with manual fix
                        
                    elif action == 'fixed_in_ide':
                            # User has fixed the issue in the IDE themselves
                            printer.print("✅ Continuing with the assumption that you have fixed the issue in the IDE.")
                            
                            # Read the current code from the IDE session (user may have modified it)
                            current_code = await quix_tools.read_session_file(
                                self.context.workspace.workspace_id, 
                                self.context.deployment.session_id, 
                                "main.py"
                            )
                            
                            # Ask if user wants to prepare for production
                            if get_user_approval("Would you like to prepare this code for production deployment?"):
                                # Create production-ready code version
                                printer.print("  - Creating production-ready code version.")
                                production_code = self._create_production_code(current_code)
                                
                                # Update the context with production code and save it back to session
                                self.context.code_generation.generated_code_draft = production_code
                                await quix_tools.update_session_file(
                                    self.context.workspace.workspace_id, 
                                    self.context.deployment.session_id, 
                                    "main.py", 
                                    production_code
                                )
                                printer.print("  - Updated main.py with production-ready code.")
                            else:
                                # Update context with the current IDE code but keep it as-is
                                self.context.code_generation.generated_code_draft = current_code
                                printer.print("  - Keeping current IDE code version.")
                            
                            printer.print("🔄 Proceeding to deployment phase.")
                            return PhaseResult(success=True, message="Phase completed successfully")
                        
                    elif action == 'auto_debug':
                        # User selected auto-debug mode
                        self._auto_debug_mode = True
                        self._auto_debug_attempt = 1
                        printer.print("🚀 Auto-debug mode activated. Will automatically retry debugging.")
                        
                        # Skip sandbox re-run on first auto-debug attempt - use existing logs
                        printer.print("🔄 Using existing error logs for auto-debug...")
                        
                        # Use Claude Code SDK directly with existing logs
                        from workflow_tools.services.claude_code_service import ClaudeCodeService
                        claude_service = ClaudeCodeService(self.context, debug_mode=self.debug_mode)
                        
                        try:
                            # Debug the code with existing logs
                            fixed_code = await claude_service.debug_code(
                                logs, 
                                self.context.code_generation.app_extract_dir,
                                self.context.code_generation.generated_code_draft
                            )
                            
                            if fixed_code:
                                printer.print("✅ Claude Code SDK successfully fixed the code!")
                                # Update the context with fixed code
                                self.context.code_generation.generated_code_draft = fixed_code
                                # Save fixed code to file
                                main_py_path = os.path.join(self.context.code_generation.app_extract_dir, "main.py")
                                with open(main_py_path, 'w', encoding='utf-8') as f:
                                    f.write(fixed_code)
                                printer.print(f"📝 Fixed code saved to {main_py_path}")
                                # Increment attempt counter for next iteration
                                self._auto_debug_attempt = 2
                                retry_count += 1
                                # Continue to next iteration to test the fixed code
                            else:
                                printer.print("❌ Claude Code SDK was unable to fix the error.")
                                self._auto_debug_mode = False
                                return PhaseResult(success=False, message="Auto-debug failed to fix the error")
                                
                        except Exception as e:
                            printer.print(f"❌ Error using Claude Code SDK: {str(e)}")
                            self._auto_debug_mode = False
                            return PhaseResult(success=False, message=f"Auto-debug failed: {str(e)}")
                        
                    elif action == 'auto_debug_failed':
                        # Auto-debug attempt failed, increment counter and retry
                        self._auto_debug_attempt += 1
                        printer.print(f"🔄 Auto-debug attempt {self._auto_debug_attempt - 1} failed. Retrying...")
                        retry_count += 1
                        # Continue to next iteration in auto-debug mode
                        
                    elif action == 'claude_fixed':
                        # Claude Code SDK fixed the code
                        if fixed_code:
                            printer.print("📤 Uploading fixed code to IDE...")
                            try:
                                await quix_tools.update_session_file(
                                    self.context.workspace.workspace_id, 
                                    self.context.deployment.session_id, 
                                    "main.py", 
                                    fixed_code
                                )
                                self.context.code_generation.generated_code_draft = fixed_code
                                printer.print("✅ Fixed code uploaded to IDE. Retrying...")
                                
                                # If in auto-debug mode, increment attempt counter
                                if getattr(self, '_auto_debug_mode', False):
                                    self._auto_debug_attempt += 1
                                    
                                retry_count += 1
                            except Exception as e:
                                printer.print(f"⚠️ Warning: Failed to update IDE session: {e}")
                                if getattr(self, '_auto_debug_mode', False):
                                    # In auto-debug mode, treat upload failure as debug failure
                                    self._auto_debug_attempt += 1
                                    retry_count += 1
                                else:
                                    return PhaseResult(success=False, message="Failed to upload fixed code")
                        else:
                            printer.print("❌ No fixed code provided.")
                            if getattr(self, '_auto_debug_mode', False):
                                self._auto_debug_attempt += 1
                                retry_count += 1
                            else:
                                return PhaseResult(success=False, message="Phase failed")
                    
                    elif action == 'abort':
                        printer.print("🛑 Aborting workflow as per user request.")
                        # Reset auto-debug mode
                        self._auto_debug_mode = False
                        self._auto_debug_attempt = 0
                        return PhaseResult(success=False, message="Phase failed")
                    
                    # After handling the action, continue the retry loop
                    if retry_count >= max_retries:
                        printer.print("❌ Maximum retries reached.")
                        return PhaseResult(success=False, message="Phase failed")
                    # Continue the retry loop
                
                elif execution_status == 'success':
                    printer.print("✅ Source application appears to be running successfully!")
                    printer.print("  - Data is being produced to the output topic")

                    # Pause to let user review the success analysis
                    printer.print("")
                    printer.print("📋 Log analysis complete. Press Enter to continue to the next phase...")
                    try:
                        input()
                    except KeyboardInterrupt:
                        printer.print("\n⚠️ Interrupted. Continuing anyway...")

                    # Create production-ready code
                    production_code = self._create_production_code(self.context.code_generation.generated_code_draft)
                    self.context.code_generation.generated_code_draft = production_code

                    return PhaseResult(success=True, message="Source sandbox testing completed successfully")
                elif execution_status == 'uncertain':
                    printer.print("⚠️ Could not determine if source is running correctly.")
                    printer.print("  - No clear success or error indicators found in logs")
                    
                    if get_user_approval("Continue with deployment?"):
                        # Create production-ready code
                        production_code = self._create_production_code(self.context.code_generation.generated_code_draft)
                        self.context.code_generation.generated_code_draft = production_code
                        return PhaseResult(success=True, message="Source sandbox testing completed (user approved)")
                    else:
                        return PhaseResult(success=False, message="Phase failed")
                        
            except Exception as e:
                printer.print(f"❌ Error during sandbox test: {str(e)}")
                
                if retry_count < max_retries - 1:
                    retry_count += 1
                    printer.print(f"Retrying... (Attempt {retry_count + 1}/{max_retries})")
                    continue
                else:
                    printer.print("Maximum retries reached.")
                    
                    # Save debug information
                    return PhaseResult(success=False, message=f"Sandbox test failed: {str(e)}")
        
        # Should not reach here, but just in case
        return PhaseResult(success=False, message="Phase failed")