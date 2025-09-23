# phase_sink_sandbox.py - Sink Sandbox Testing and Debugging Phase

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

class SinkSandboxPhase(BasePhase):
    """Handles sandbox testing and debugging."""
    
    phase_name = "sink_sandbox"
    phase_description = "Test in sandbox"
    
    def __init__(self, context: WorkflowContext, generation_phase, debug_mode: bool = False):
        self.context = context
        self.generation_phase = generation_phase  # Reference to GenerationPhase for code regeneration
        self.debug_mode = debug_mode
        self.credential_mapper = CredentialFieldMapper(debug_mode)
        self.debug_analyzer = DebugAnalyzer(context, debug_mode)
    
    
    def _create_production_code(self, code: str) -> str:
        """Create production-ready code by removing app.run() limits and adding proper infinite loop."""
        original_code = code
        
        # Find app.run() calls using a more specific pattern
        # This matches: app.run(anything) including multiline calls
        app_run_pattern = r'(app\.run\s*\([^)]*\))'
        
        def replace_app_run(match):
            app_run_call = match.group(1)
            
            # Remove count= and timeout= parameters only within this specific app.run() call
            # First, remove count=<anything> parameter
            count_pattern = r'count\s*=\s*[^,)]+\s*,?\s*'
            cleaned_call = re.sub(count_pattern, '', app_run_call)
            
            # Second, remove timeout=<anything> parameter  
            timeout_pattern = r'timeout\s*=\s*[^,)]+\s*,?\s*'
            cleaned_call = re.sub(timeout_pattern, '', cleaned_call)
            
            # Clean up any remaining double commas or trailing commas before closing parenthesis
            cleaned_call = re.sub(r',\s*,', ',', cleaned_call)  # Remove double commas
            cleaned_call = re.sub(r',\s*\)', ')', cleaned_call)  # Remove trailing comma before closing paren
            
            return cleaned_call
        
        # Apply the replacement only to app.run() calls
        production_code = re.sub(app_run_pattern, replace_app_run, code)
        
        # Log the changes if any modifications were made
        if production_code != original_code:
            printer.print("  - Preparing production-ready code (removing app.run() limits)")
            
            # Extract and show the changes
            original_app_run = re.search(r'app\.run\s*\([^)]*\)', original_code)
            production_app_run = re.search(r'app\.run\s*\([^)]*\)', production_code)
            
            if original_app_run and production_app_run:
                printer.print(f"    Original: {original_app_run.group(0)}")
                printer.print(f"    Production: {production_app_run.group(0)}")
        
        return production_code
    
    async def execute(self) -> PhaseResult:
        """Configures the sandbox, runs the code, and handles success or failure."""
        printer.print("\n--- Phase 2: Sandbox Testing ---")

        # Check required context fields with specific error messages
        missing_fields = []
        if not self.context.workspace.workspace_id:
            missing_fields.append("workspace_id")
        if not self.context.deployment.application_id:
            missing_fields.append("application_id")
        # Note: session_id is no longer required here - we'll create it if needed
        if not self.context.code_generation.generated_code_draft:
            missing_fields.append("generated_code_draft")
        # Note: connection_credentials can be empty dict, so we don't check it as required
        
        if missing_fields:
            printer.print(f"🛑 Critical context missing for sandbox test: {', '.join(missing_fields)}")
            printer.print("Expected context fields:")
            printer.print(f"  - workspace_id: '{self.context.workspace.workspace_id}'")
            printer.print(f"  - application_id: '{self.context.deployment.application_id}'")
            printer.print(f"  - generated_code_draft: {'Present' if self.context.code_generation.generated_code_draft else 'Missing'}")
            printer.print(f"  - env_var_values: {len(self.context.credentials.env_var_values) if self.context.credentials.env_var_values else 0} variables")
            return PhaseResult(success=False, message="Phase failed")
        
        # Create IDE session if it doesn't exist (consistent with source workflow)
        if not hasattr(self.context.deployment, 'session_id') or not self.context.deployment.session_id:
            printer.print("🔄 Creating IDE session for sandbox testing.")
            
            # Log the application URL for reference
            url_builder = QuixPortalURLBuilder()
            branch = self.context.workspace.branch_name or "main"
            app_url = url_builder.get_application_url(
                workspace=self.context.workspace.workspace_id,
                application_name=self.context.deployment.application_name,
                branch=branch
            )
            printer.print_verbose(f"🔗 Running session in application: {app_url}")
            
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
        
        # ALWAYS collect environment variable values from user BEFORE configuring sandbox
        # This happens regardless of whether we're using cached code or fresh generation
        # This ensures users can provide values that will be used in the sandbox test
        from workflow_tools.phases.shared.env_var_management import EnvVarManager
        env_var_manager = EnvVarManager(self.context, run_config=None, debug_mode=self.debug_mode)
        
        printer.print("\n📋 Collecting environment variable values before sandbox configuration...")
        await env_var_manager.collect_env_vars_from_app_yaml(self.context.code_generation.app_extract_dir)
        
        # Save the updated app directory back to cache after user provides env var values
        # This ensures the cache contains the user's values for next time
        from workflow_tools.phases.shared.cache_utils import CacheUtils
        cache_utils = CacheUtils(self.context, self.debug_mode)
        if self.context.code_generation.app_extract_dir:
            cache_utils.save_app_directory_to_cache(self.context.code_generation.app_extract_dir)
            printer.print("✅ Saved updated environment variables to cache for future use")

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
                printer.print("  - Uploading application files to Quix IDE...")
                
                # First write the generated code to the local main.py file
                main_py_path = os.path.join(self.context.code_generation.app_extract_dir, "main.py")
                with open(main_py_path, 'w', encoding='utf-8') as f:
                    f.write(self.context.code_generation.generated_code_draft)
                
                # Use centralized function to upload all files
                try:
                    files_updated = await quix_tools.update_all_session_files_from_local(
                        self.context.workspace.workspace_id,
                        self.context.deployment.session_id,
                        self.context.code_generation.app_extract_dir
                    )
                    if not files_updated:
                        printer.print("  - ⚠️ Some files could not be updated, but continuing...")
                except Exception as e:
                    error_msg = str(e)
                    # Check for session-related 404 errors (corrupted session or session not found)
                    if "404" in error_msg and ("app.yaml" in error_msg or "Session was not found" in error_msg):
                        printer.print("  - ⚠️ Session appears to be corrupted or not found. Recreating session.")
                        
                        # Stop the existing session
                        await quix_tools.manage_session(
                            action=quix_tools.SessionAction.stop,
                            workspace_id=self.context.workspace.workspace_id,
                            session_id=self.context.deployment.session_id
                        )
                        printer.print("  - Stopped corrupted session.")
                        
                        # Create a new session for the same application
                        new_session = await quix_tools.manage_session(
                            action=quix_tools.SessionAction.start,
                            workspace_id=self.context.workspace.workspace_id,
                            application_id=self.context.deployment.application_id,
                            branch_name=self.context.workspace.branch_name
                        )
                        if new_session and 'sessionId' in new_session:
                            self.context.deployment.session_id = new_session['sessionId']
                            printer.print(f"  - Created new session: {self.context.deployment.session_id}")
                            
                            # Retry the main.py upload with the new session
                            await quix_tools.update_session_file(self.context.workspace.workspace_id, self.context.deployment.session_id, "main.py", self.context.code_generation.generated_code_draft)
                            printer.print("  - Updated main.py with generated code (after session recreation).")
                        else:
                            printer.print("  - ❌ Failed to create new session. Please try again.")
                            return PhaseResult(success=False, message="Phase failed")
                    else:
                        # Re-raise if it's a different error
                        raise e

                # 2. Install dependencies from requirements.txt
                # Note: requirements.txt has already been uploaded by update_all_session_files_from_local
                printer.print("  - Installing dependencies...")
                setup_result = await quix_tools.setup_session(self.context.workspace.workspace_id, self.context.deployment.session_id, force=True)
                printer.print_debug(f"  - Setup result (full): {repr(setup_result)}")

                # 3. Synchronize variables - Use ALL user-provided variables plus any additional from code
                # Note: env_var_manager is already created and collection already done before the retry loop
                
                # Print what variables we have from the user
                user_provided_vars = list(self.context.credentials.env_var_values.keys()) if self.context.credentials.env_var_values else []
                printer.print_verbose(f"  - User-provided environment variables: {user_provided_vars}")
                
                # Also detect any additional variables used in the generated code
                detected_env_vars = env_var_manager.detect_environment_variables(self.context.code_generation.generated_code_draft)
                printer.print_verbose(f"  - Additional variables detected in code: {detected_env_vars}")
                
                # Use centralized smart sync - preserves existing vars by default
                await env_var_manager.sync_or_update_app_variables(
                    detected_code_vars=detected_env_vars,
                    force_update=False  # Don't overwrite existing variables
                )
                
                # 4. Prepare session variables from the already-collected values in app.yaml
                printer.print_verbose("  Preparing session variables from app.yaml...")
                session_env_vars, session_secrets = env_var_manager.prepare_session_variables()
                
                printer.print_verbose(f"  - Final session_env_vars: {list(session_env_vars.keys())}")
                printer.print_verbose(f"  - Final session_secrets: {list(session_secrets.keys())} (values hidden)")
                
                # Update session with the variables
                update_result = await quix_tools.update_session_environment(
                    self.context.workspace.workspace_id, 
                    self.context.deployment.session_id, 
                    environment_variables=session_env_vars if session_env_vars else None,
                    secrets=session_secrets if session_secrets else None
                )
                printer.print_verbose("  - Session environment updated.")
                printer.print_debug(f"  - Update result:\n{quix_tools.pretty_json(update_result)}")
                printer.print("✅ Sandbox configured")

                # 5. Run the code
                printer.print("\n🧪 Running test...")
                # Use the centralized function with timeout to prevent infinite running
                logs = await quix_tools.run_code_in_session_with_timeout(
                    self.context.workspace.workspace_id, 
                    self.context.deployment.session_id, 
                    "main.py",
                    timeout_seconds=30
                )

                # Use centralized error handler with context for AI analysis
                error_handler = SandboxErrorHandler(self.context, self.debug_mode)
                
                # Analyze logs
                has_error, is_timeout_error, has_success = error_handler.analyze_logs(logs, workflow_type="sink")
                
                # Display logs
                error_handler.display_logs(logs, has_error)
                
                # Determine overall status using AI analysis when appropriate
                execution_status = await error_handler.determine_execution_status_with_ai(
                    logs=logs,
                    test_objective="Testing the sink application to ensure it successfully consumes data from Kafka and writes to the destination",
                    workflow_type="sink",
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
                        workflow_type="sink",
                        is_timeout_error=is_timeout_error,
                        is_connection_test=False,
                        run_code_callback=run_fixed_code_callback
                    )
                    
                    # Handle the action returned by debug analyzer
                    if action == 'claude_fixed':
                        # Use the code fixed by Claude Code SDK directly
                        printer.print("✅ Using code fixed by Claude Code SDK...")
                        self.context.code_generation.generated_code_draft = fixed_code
                        
                        # Cache the entire fixed app directory (Claude Code may have modified app.yaml, requirements.txt, etc.)
                        from workflow_tools.phases.shared.cache_utils import CacheUtils
                        cache_utils = CacheUtils(self.context, self.debug_mode)
                        if self.context.code_generation.app_extract_dir:
                            cache_utils.save_app_directory_to_cache(self.context.code_generation.app_extract_dir)
                        
                        # Update main.py with the fixed code
                        await quix_tools.update_session_file(self.context.workspace.workspace_id, self.context.deployment.session_id, "main.py", fixed_code)
                        printer.print("✅ Updated main.py with Claude-fixed code")
                        
                        # If in auto-debug mode, increment attempt counter
                        if getattr(self, '_auto_debug_mode', False):
                            self._auto_debug_attempt += 1
                        
                        # Continue to retry testing
                        continue
                        
                    # Note: 'regenerate_with_fix' action removed - code_generator no longer exists
                    # Note: 'manual_feedback' action no longer used - option 2 now sends feedback directly to Claude Code
                    # and returns 'claude_fixed' action instead
                        
                    elif action == 'manual_fix':
                        # User wants to fix code manually in IDE and retry
                        printer.print("🔄 Running your manually fixed code from the IDE...")
                        # Just retry - the code in the IDE has been manually fixed
                        retry_count += 1
                        # Continue to next iteration to retry with manual fix
                        
                    elif action == 'fixed_in_ide':
                            # User has fixed the issue in the IDE themselves
                            printer.print("✅ Continuing with the assumption that you have fixed the issue in the IDE.")
                            
                            # Ask if user wants to deploy to production
                            if get_user_approval("Would you like to prepare this code for production deployment?"):
                                # Read the current code from the IDE session (user may have modified it)
                                current_code = await quix_tools.read_session_file(self.context.workspace.workspace_id, self.context.deployment.session_id, "main.py")
                                
                                # Create production-ready code version (remove app.run() limits)
                                printer.print("  - Creating production-ready code version.")
                                production_code = self._create_production_code(current_code)
                                
                                # Update the context with production code and save it back to session
                                self.context.code_generation.generated_code_draft = production_code
                                await quix_tools.update_session_file(self.context.workspace.workspace_id, self.context.deployment.session_id, "main.py", production_code)
                                printer.print("  - Updated main.py with production-ready code.")
                            else:
                                # Update context with the current IDE code but keep it as-is
                                current_code = await quix_tools.read_session_file(self.context.workspace.workspace_id, self.context.deployment.session_id, "main.py")
                                self.context.code_generation.generated_code_draft = current_code
                                printer.print("  - Keeping current IDE code version (with app.run() limits).")
                            
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
                        
                    elif action == 'abort':
                        printer.print("🛑 Aborting workflow as per user request.")
                        # Reset auto-debug mode
                        self._auto_debug_mode = False
                        self._auto_debug_attempt = 0
                        return PhaseResult(success=False, message="Phase failed")
                    
                    # Loop will continue to retry the test with the new code
                else:  # execution_status is either 'success' or 'uncertain'
                    if execution_status == 'success':
                        printer.print("✅ Test run completed successfully with no apparent errors!")

                        # Pause to let user review the success analysis
                        printer.print("")
                        printer.print("📋 Log analysis complete. Press Enter to continue...")
                        try:
                            input()
                        except KeyboardInterrupt:
                            printer.print("\n⚠️ Interrupted. Continuing anyway...")

                    elif execution_status == 'uncertain':
                        printer.print("⚠️ Could not determine if sink is running correctly.")
                        printer.print("  - No clear success or error indicators found in logs")
                        if not get_user_approval("Continue anyway?"):
                            return PhaseResult(success=False, message="User aborted due to uncertain status")
                    
                    # Ask if user wants to deploy to production
                    if get_user_approval("Would you like to prepare this code for production deployment?"):
                        # Create production-ready code version (remove app.run() limits)
                        printer.print("  - Creating production-ready code version.")
                        production_code = self._create_production_code(self.context.code_generation.generated_code_draft)
                        
                        # Update the context with production code and save it back to session
                        self.context.code_generation.generated_code_draft = production_code
                        await quix_tools.update_session_file(self.context.workspace.workspace_id, self.context.deployment.session_id, "main.py", production_code)
                        printer.print("  - Updated main.py with production-ready code.")
                    else:
                        printer.print("  - Keeping sandbox code version (with app.run() limits).")
                    
                    return PhaseResult(success=True, message="Phase completed successfully")

            except quix_tools.QuixApiError as e:
                printer.print(f"🛑 A critical API error occurred during sandbox testing: {e}")
                retry_count += 1
                if retry_count >= max_retries:
                    printer.print(f"❌ Maximum retries ({max_retries}) reached.")
                    return PhaseResult(success=False, message="Phase failed")
                if not get_user_approval(f"An API error occurred. Would you like to try again? (Attempt {retry_count + 1}/{max_retries})"):
                    return PhaseResult(success=False, message="Phase failed")
                continue  # Continue the retry loop
            
            except Exception as e:
                printer.print(f"❌ Unexpected error during sandbox test: {str(e)}")
                retry_count += 1
                if retry_count >= max_retries:
                    printer.print(f"❌ Maximum retries ({max_retries}) reached.")
                    return PhaseResult(success=False, message="Phase failed")
                printer.print(f"Retrying... (Attempt {retry_count + 1}/{max_retries})")
                continue  # Continue the retry loop