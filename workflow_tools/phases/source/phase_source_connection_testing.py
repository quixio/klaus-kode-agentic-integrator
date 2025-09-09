# phase_source_connection_testing.py - Source Connection Testing Phase

import os
import re
from datetime import datetime
from typing import List
from agents import RunConfig
from workflow_tools.common import WorkflowContext, printer, get_user_approval
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.integrations import quix_tools
from workflow_tools.services.claude_code_service import ClaudeCodeService
from workflow_tools.services.dependency_parser import DependencyParser
from workflow_tools.services import SandboxErrorHandler, DebugAnalyzer
from workflow_tools.core.url_builder import QuixPortalURLBuilder
from workflow_tools.core.working_directory import WorkingDirectory
from workflow_tools.exceptions import NavigationBackRequest

class SourceConnectionTestingPhase(BasePhase):
    """Handles connection testing for source applications."""
    
    phase_name = "source_connection_testing"
    phase_description = "Test source connection"
    
    def __init__(self, context: WorkflowContext, run_config=None, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.run_config = run_config or RunConfig(workflow_name="Create Quix Source (V1)")
        
        # Use centralized services
        self.claude_code_service = ClaudeCodeService(context, debug_mode)
        self.dependency_parser = DependencyParser()
        self.debug_analyzer = DebugAnalyzer(context, debug_mode)
        self.error_handler = SandboxErrorHandler(context, debug_mode)
    
    async def execute(self) -> PhaseResult:
        """Execute the connection testing workflow."""
        printer.print("🔌 **Phase 4: Source Connection Testing**")
        printer.print("")
        
        try:
            # Initialize cache utils
            from workflow_tools.phases.shared.cache_utils import CacheUtils
            from workflow_tools.exceptions import NavigationBackRequest
            cache_utils = CacheUtils(self.context, self.debug_mode)
            
            # Step 0: Check for cached connection requirements or ask user
            printer.print("📝 **Connection Test Requirements**")
            printer.print("-" * 40)
            
            # Check for cached user prompt (connection requirements)
            cached_prompt = cache_utils.check_cached_user_prompt()
            if cached_prompt:
                # Extract the actual prompt from the cached file (skip header comments)
                prompt_lines = cached_prompt.split('\n')
                actual_prompt_lines = []
                skip_comments = True
                for line in prompt_lines:
                    if skip_comments and line.strip() and not line.strip().startswith('#'):
                        skip_comments = False
                    if not skip_comments:
                        actual_prompt_lines.append(line)
                actual_prompt = '\n'.join(actual_prompt_lines).strip()
                
                if cache_utils.use_cached_user_prompt(actual_prompt):
                    user_requirements = actual_prompt
                    self.context.technology.source_technology = user_requirements
                    printer.print(f"✅ Using cached requirements: {user_requirements}")
                else:
                    # User wants to enter fresh requirements
                    from workflow_tools.common import clear_screen
                    clear_screen()
                    printer.print("What system do you want to connect to?")
                    printer.print("(Tip: Mention any specific API endpoints, data fields, or requirements)")
                    printer.print("")
                    user_requirements = printer.input("Describe what system you want to connect to and the data you want to get [or press Enter for default]: ").strip()
                    
                    if user_requirements:
                        self.context.technology.source_technology = user_requirements
                        printer.print(f"✅ Will test: {user_requirements}")
                        # Cache the new requirements
                        cache_utils.save_user_prompt_to_cache(user_requirements)
                    else:
                        # Use default
                        self.context.technology.source_technology = "Connect to the source and retrieve sample data"
                        printer.print(f"✅ Using default: {self.context.technology.source_technology}")
            else:
                # No cached prompt, ask user
                from workflow_tools.common import clear_screen
                clear_screen()
                printer.print("What system do you want to connect to?")
                printer.print("(Tip: Mention any specific API endpoints, data fields, or requirements)")
                printer.print("")
                user_requirements = printer.input("Describe what system you want to connect to and the data you want to get [or press Enter for default]: ").strip()
                
                if user_requirements:
                    self.context.technology.source_technology = user_requirements
                    printer.print(f"✅ Will test: {user_requirements}")
                    # Cache the new requirements
                    cache_utils.save_user_prompt_to_cache(user_requirements)
                else:
                    # Use existing or default
                    if not hasattr(self.context.technology, 'source_technology') or not self.context.technology.source_technology:
                        self.context.technology.source_technology = "Connect to the source and retrieve sample data"
                    printer.print(f"✅ Using: {self.context.technology.source_technology}")
            
            printer.print("")
            
            # Step 1: Generate connection test code
            if not await self._generate_connection_test_code():
                return PhaseResult(success=False, message="Phase failed")
            
            # Step 2: Run connection test and collect samples
            if not await self._run_connection_test():
                return PhaseResult(success=False, message="Phase failed")
            
            # Step 3: Save sample data for schema analysis
            if not self._save_sample_data():
                return PhaseResult(success=False, message="Phase failed")
            
            printer.print("✅ Source connection testing completed successfully!")
            return PhaseResult(success=True, message="Phase completed successfully")
            
        except NavigationBackRequest:
            # Re-raise navigation requests to be handled by phase orchestrator
            raise
        except Exception as e:
            printer.print(f"❌ Error in source connection testing: {str(e)}")
            return PhaseResult(success=False, message="Phase failed")
    
    async def _generate_connection_test_code(self) -> bool:
        """Generate connection test code using Claude Code service with centralized caching."""
        printer.print("🧠 Generating connection test code using Claude Code SDK.")
        
        try:
            from workflow_tools.phases.shared.cache_utils import CacheUtils
            from workflow_tools.exceptions import NavigationBackRequest
            cache_utils = CacheUtils(self.context, self.debug_mode)
            
            # Use centralized method to check for cached connection test
            connection_code = cache_utils.get_cached_connection_test()
            
            if connection_code is None:
                # Either no cache or user declined - generate fresh code
                connection_code = await self._generate_with_claude_code()
            
            if not connection_code:
                printer.print("❌ Failed to generate connection test code.")
                return False
            
            # Store code in context
            self.context.code_generation.connection_test_code = connection_code
            
            # Connection test code will be cached as part of the full app directory later
            
            # Use centralized method to backup and swap main.py
            app_dir = self.context.code_generation.app_extract_dir
            if not cache_utils.backup_and_swap_main_py(app_dir, connection_code):
                printer.print("❌ Failed to setup connection test files")
                return False
            
            # Store the connection test file path in context
            self.context.code_generation.connection_test_file = os.path.join(app_dir, "connection_test.py")
            
            return True
            
        except NavigationBackRequest:
            # Re-raise navigation requests to be handled by phase orchestrator
            raise
        except Exception as e:
            printer.print(f"❌ Error generating connection test code: {str(e)}")
            return False
    
    async def _generate_with_claude_code(self) -> str:
        """Generate connection test code using Claude Code service with feedback loop."""
        
        # Get the user's source requirements/prompt
        user_requirements = getattr(self.context.technology, 'source_technology', None) or \
                          self.context.technology.destination_technology or "external system"
        
        # Use the app directory that already has app.yaml configured
        test_dir = self.context.code_generation.app_extract_dir
        
        # Use Claude Code's feedback loop for generation
        feedback = None
        while True:
            # Build the connection test request
            if feedback:
                # Add feedback to the user requirements
                test_request = f"{user_requirements}\n\n## Additional Requirements:\n{feedback}"
            else:
                test_request = user_requirements
            
            # Generate code using the specialized connection test method
            connection_code, _ = await self.claude_code_service.generate_code_for_connection_test(
                user_prompt=test_request,
                app_dir=test_dir,
                workflow_type="source"
            )
            
            if not connection_code:
                printer.print("❌ Failed to generate connection test code with Claude Code SDK.")
                return None
            
            # Display the code
            printer.print(f"\n--- Generated Connection Test Code ---")
            printer.print("```python")
            printer.print(connection_code)
            printer.print("```")
            printer.print("-" * 50)
            
            # Get user approval
            if get_user_approval("Does the generated connection test code look correct?"):
                printer.print("✅ Connection test code approved by user.")
                return connection_code
            
            # Get feedback for regeneration
            feedback = printer.input("Please provide feedback on what to change: ").strip()
            if not feedback:
                printer.print("No feedback provided. Aborting connection test generation.")
                return None
            
            printer.print("🔄 Regenerating code based on your feedback.")
    

    async def _run_connection_test(self, auto_debug_attempt: int = 0) -> bool:
        """Run the connection test - wrapper that calls internal method."""
        return await self._run_connection_test_internal(auto_debug_attempt)
    
    async def _run_connection_test_internal(self, auto_debug_attempt: int = 0) -> bool:
        """Run the connection test using the same robust API-based pattern as the sink sandbox.
        
        Args:
            auto_debug_attempt: Current auto-debug attempt (0 = not in auto-debug mode, 1+ = auto-debug mode)
        """
        printer.print("🧪 Running connection test in IDE.")

        # ALWAYS collect environment variable values from user BEFORE creating IDE session
        # This ensures users provide values that will be used in the connection test
        from workflow_tools.phases.shared.env_var_management import EnvVarManager
        env_var_manager = EnvVarManager(self.context, self.run_config, self.debug_mode)
        
        # Detect variables in the connection test code first
        detected_env_vars = env_var_manager.detect_environment_variables(self.context.code_generation.connection_test_code)
        if detected_env_vars:
            printer.print(f"📋 Environment variables detected in code: {detected_env_vars}")
            
            # Sync variables to app.yaml if needed
            await env_var_manager.sync_or_update_app_variables(
                detected_code_vars=detected_env_vars,
                force_update=False  # Preserve existing variables
            )
        
        # Collect environment variable values from user based on app.yaml
        # Pass auto_debug_mode flag to automatically reuse values during auto-debug
        printer.print("\n📋 Collecting environment variable values before connection test...")
        await env_var_manager.collect_env_vars_from_app_yaml(
            self.context.code_generation.app_extract_dir,
            auto_debug_mode=(auto_debug_attempt > 0)
        )
        
        # Save the updated app directory back to cache after user provides env var values
        # Mark this as a connection test cache, not a main app cache
        from workflow_tools.phases.shared.cache_utils import CacheUtils
        cache_utils = CacheUtils(self.context, self.debug_mode)
        if self.context.code_generation.app_extract_dir:
            cache_utils.save_app_directory_to_cache(self.context.code_generation.app_extract_dir, is_connection_test=True)
            printer.print("✅ Saved connection test environment variables to cache for future use")

        if not hasattr(self.context, 'session_id') or not self.context.deployment.session_id:
            printer.print("\nCreating IDE session for connection testing.")
            
            # Log the application URL for reference
            url_builder = QuixPortalURLBuilder()
            branch = self.context.workspace.branch_name or "main"
            app_url = url_builder.get_application_url(
                workspace=self.context.workspace.workspace_id,
                application_name=self.context.deployment.application_name,
                branch=branch
            )
            printer.print(f"🔗 Running session in application: {app_url}")
            
            session_result = await quix_tools.manage_session(
                action=quix_tools.SessionAction.start,
                workspace_id=self.context.workspace.workspace_id,
                application_id=self.context.deployment.application_id,
                branch_name=self.context.workspace.branch_name
            )
            if not session_result or 'sessionId' not in session_result:
                printer.print("❌ Failed to start IDE session.")
                return False
            self.context.deployment.session_id = session_result['sessionId']
            printer.print(f"✅ Created IDE session: {self.context.deployment.session_id}")

        session_id = self.context.deployment.session_id

        try:
            printer.print("Configuring connection test environment.")

            # 1. Upload connection test code as main.py
            printer.print("  - Uploading connection test code to IDE as main.py.")
            try:
                await quix_tools.update_session_file(
                    self.context.workspace.workspace_id,
                    session_id,
                    "main.py",
                    self.context.code_generation.connection_test_code
                )
                printer.print("  - Updated main.py with connection test code.")
            except Exception as e:
                error_msg = str(e)
                if "404" in error_msg and "app.yaml" in error_msg:
                    printer.print("  - ⚠️ Session appears to be corrupted. Recreating session.")
                    await quix_tools.manage_session(
                        action=quix_tools.SessionAction.stop,
                        workspace_id=self.context.workspace.workspace_id,
                        session_id=session_id
                    )
                    new_session = await quix_tools.manage_session(
                        action=quix_tools.SessionAction.start,
                        workspace_id=self.context.workspace.workspace_id,
                        application_id=self.context.deployment.application_id,
                        branch_name=self.context.workspace.branch_name
                    )
                    self.context.deployment.session_id = new_session['sessionId']
                    session_id = self.context.deployment.session_id
                    printer.print(f"  - Created new session: {session_id}")
                    await quix_tools.update_session_file(self.context.workspace.workspace_id, session_id, "main.py",
                                                         self.context.code_generation.connection_test_code)
                else:
                    raise e

            # 2. Update requirements.txt
            printer.print("  - Updating requirements.txt.")
            template_requirements_lines = []
            if self.context.code_generation.template_requirements:
                for line in self.context.code_generation.template_requirements.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        template_requirements_lines.append(line)
            else:
                template_requirements_lines = ["python-dotenv", "requests"]
            ai_dependencies = self.dependency_parser.parse_dependency_comments(self.context.code_generation.connection_test_code)
            additional_packages = ai_dependencies or self.dependency_parser.detect_required_packages(self.context.code_generation.connection_test_code)
            all_packages = list(dict.fromkeys(template_requirements_lines + additional_packages))
            requirements = "\n".join(all_packages) + "\n"
            await quix_tools.update_session_file(self.context.workspace.workspace_id, session_id, "requirements.txt",
                                                 requirements)

            # 3. Install dependencies
            printer.print("  - Installing dependencies.")
            await quix_tools.setup_session(self.context.workspace.workspace_id, session_id, force=True)

            # 4. Inject environment variables that were already collected before session creation
            # The env_var_manager was already created and used above
            session_env_vars, session_secrets = env_var_manager.prepare_session_variables()
            
            if session_env_vars or session_secrets:
                await quix_tools.update_session_environment(
                    self.context.workspace.workspace_id,
                    session_id,
                    environment_variables=session_env_vars if session_env_vars else None,
                    secrets=session_secrets if session_secrets else None
                )
                printer.print("  - Injected variables into the running IDE session.")

            printer.print("✅ Connection test environment configured.")

            # 5. Run the code
            printer.print("\nInitiating connection test run.")
            logs = await quix_tools.run_code_in_session(
                self.context.workspace.workspace_id,
                session_id,
                "main.py"
            )

            # 6. Analyze results using centralized error handler
            has_error, is_timeout_error, has_success = self.error_handler.analyze_logs(logs, workflow_type="source")
            self.error_handler.display_logs(logs, has_error)
            
            # Determine overall status using AI analysis when appropriate
            execution_status = await self.error_handler.determine_execution_status_with_ai(
                logs=logs,
                test_objective="Testing connection to the external data source to ensure it can retrieve data",
                workflow_type="source",
                code_context=self.context.code_generation.connection_test_code,
                is_connection_test=True
            )
            
            if execution_status == 'error':
                # Use centralized debug analyzer for interactive debugging
                action, debug_feedback = await self.debug_analyzer.interactive_debug_workflow(
                    code=self.context.code_generation.connection_test_code,
                    error_logs=logs,
                    workflow_type="source",
                    is_timeout_error=is_timeout_error,
                    is_connection_test=True,  # This is a connection test, not a full app
                    auto_debug_attempt=auto_debug_attempt  # Pass through auto-debug state
                )
                
                # Handle the action returned by debug analyzer
                if action == 'claude_fixed':
                    # Use the code fixed by Claude Code SDK directly
                    printer.print("✅ Using code fixed by Claude Code SDK...")
                    self.context.code_generation.connection_test_code = debug_feedback
                    # Save the fixed code to file
                    test_code_path = os.path.join(self.context.code_generation.app_extract_dir, "connection_test.py")
                    with open(test_code_path, 'w', encoding='utf-8') as file:
                        file.write(debug_feedback)
                    # If we're in auto-debug mode, the loop will call us again
                    # Just return False to trigger the next iteration
                    if auto_debug_attempt > 0:
                        return False  # Will trigger next auto-debug attempt
                    else:
                        return await self._run_connection_test()
                elif action == 'manual_feedback':
                    # Get manual feedback and regenerate
                    feedback = printer.input("Please provide feedback on how to fix the error: ").strip()
                    if feedback:
                        if await self._regenerate_connection_test_with_feedback(feedback):
                            return await self._run_connection_test()
                    return False
                    
                elif action == 'manual_fix':
                    # User fixed code manually in IDE, just retry
                    printer.print("🔄 Running your manually fixed code from the IDE...")
                    return await self._run_manual_connection_test()
                    
                elif action == 'fixed_in_ide':
                    # User says they fixed it - run one final test to get the output
                    printer.print("✅ Running final connection test with your fixes...")
                    return await self._run_manual_connection_test()
                    
                elif action == 'abort':
                    printer.print("🛑 Aborting workflow as per user request.")
                    return False
                    
                elif action == 'auto_debug':
                    # User selected auto-debug mode - continue with debugging using existing logs
                    printer.print("🚀 Auto-debug mode activated. Will automatically retry debugging.")
                    # Pass the existing logs directly to auto-debug instead of re-running sandbox
                    return await self._run_connection_test_with_auto_debug(
                        auto_debug_attempt=1,
                        existing_logs=logs,
                        existing_code=self.context.code_generation.connection_test_code
                    )
                    
                elif action == 'auto_debug_failed':
                    # Auto-debug attempt failed but we're in auto-debug mode
                    # This shouldn't happen in connection test as we handle it differently
                    printer.print("❌ Auto-debug failed.")
                    return False
                    
            elif execution_status == 'success':
                printer.print("✅ Connection test completed successfully with no apparent errors!")
                self.context.connection_test_output = logs
                return True  # Return success status
            elif execution_status == 'uncertain':
                printer.print("⚠️ Could not determine if connection test succeeded.")
                printer.print("  - No clear success or error indicators found in logs")
                if get_user_approval("Continue anyway?"):
                    self.context.connection_test_output = logs
                else:
                    return False
                printer.print("📊 **Sample Data Output:**")
                printer.print(logs[:2000] + "..." if len(logs) > 2000 else logs)
                return True

        except Exception as e:
            printer.print(f"❌ Error during connection test: {str(e)}")
            return False

    async def _run_connection_test_with_auto_debug(self, auto_debug_attempt: int = 1, max_attempts: int = 10, 
                                                    existing_logs: str = None, existing_code: str = None) -> bool:
        """Wrapper for _run_connection_test that handles auto-debug mode.
        
        Args:
            auto_debug_attempt: Current auto-debug attempt number (starts at 1)
            max_attempts: Maximum number of auto-debug attempts
            existing_logs: Existing error logs from initial run (to avoid re-running sandbox on first attempt)
            existing_code: Existing code that produced the error
            
        Returns:
            True if successful, False otherwise
        """
        # On the first attempt, if we have existing logs, use them directly for debugging
        if auto_debug_attempt == 1 and existing_logs and existing_code:
            printer.print("🔄 Using existing error logs for auto-debug...")
            
            # Use the debug analyzer directly with existing logs
            from workflow_tools.services.claude_code_service import ClaudeCodeService
            claude_service = ClaudeCodeService(self.context, debug_mode=self.debug_mode)
            
            # Get the app directory from context
            app_dir = self.context.code_generation.app_extract_dir
            if not app_dir:
                printer.print("❌ Error: No app directory found in context")
                return False
            
            try:
                # Use specialized connection test debugging with existing logs
                fixed_code = await claude_service.debug_connection_test(existing_logs, app_dir, existing_code)
                
                if fixed_code:
                    printer.print("✅ Claude Code SDK successfully fixed the code!")
                    
                    # Save the fixed code
                    test_code_path = f"{app_dir}/main.py"
                    with open(test_code_path, 'w', encoding='utf-8') as file:
                        file.write(fixed_code)
                    printer.print(f"📝 Fixed code saved to {test_code_path}")
                    
                    # Update context with fixed code
                    self.context.code_generation.connection_test_code = fixed_code
                    
                    # Now run the fixed code (increment attempt for next iteration)
                    auto_debug_attempt = 2
                else:
                    printer.print("❌ Claude Code SDK was unable to fix the error.")
                    return False
                    
            except Exception as e:
                printer.print(f"❌ Error using Claude Code SDK: {str(e)}")
                return False
        
        # Continue with normal auto-debug loop
        while auto_debug_attempt <= max_attempts:
            # Call _run_connection_test_internal with the auto_debug_attempt parameter
            result = await self._run_connection_test_internal(auto_debug_attempt=auto_debug_attempt)
            
            if result:
                # Success!
                return True
            
            # If we get here, the test failed
            if auto_debug_attempt < max_attempts:
                printer.print(f"🔄 Auto-debug attempt {auto_debug_attempt}/{max_attempts} failed. Retrying...")
                auto_debug_attempt += 1
            else:
                printer.print(f"❌ Auto-debug reached maximum attempts ({max_attempts}). Failed to fix the error.")
                return False
                
        return False

    async def _run_manual_connection_test(self) -> bool:
        """Run connection test using the code that's already in the IDE (after manual fixes).
        
        This method does NOT re-upload code or reset environment variables.
        It runs whatever is currently in the IDE session.
        """
        printer.print("🧪 Running the connection test with your manual changes from the IDE.")
        
        if not hasattr(self.context.deployment, 'session_id') or not self.context.deployment.session_id:
            printer.print("❌ No session ID found. Cannot run manual test.")
            return False
        
        session_id = self.context.deployment.session_id
        
        try:
            # Just run the code that's already in the IDE - no uploads or resets
            printer.print("  - Executing main.py from the current IDE state.")
            logs = await quix_tools.run_code_in_session(
                self.context.workspace.workspace_id,
                session_id,
                "main.py"
            )
            
            printer.print("📊 **Connection Test Output:**")
            printer.print("=" * 50)
            printer.print(logs[:2000] + "..." if len(logs) > 2000 else logs)
            printer.print("=" * 50)
            
            # Check for errors using centralized error handler
            has_error, is_timeout_error, has_success = self.error_handler.analyze_logs(logs, workflow_type="source")
            self.error_handler.display_logs(logs, has_error)
            
            # Determine overall status using AI analysis when appropriate
            execution_status = await self.error_handler.determine_execution_status_with_ai(
                logs=logs,
                test_objective="Testing connection to the external data source to ensure it can retrieve data",
                workflow_type="source",
                code_context=self.context.code_generation.connection_test_code,
                is_connection_test=True
            )
            
            if execution_status == 'error':
                # Use centralized debug analyzer for interactive debugging
                action, debug_feedback = await self.debug_analyzer.interactive_debug_workflow(
                    code=self.context.code_generation.connection_test_code,
                    error_logs=logs,
                    workflow_type="source",
                    is_timeout_error=is_timeout_error,
                    is_connection_test=True,  # This is a connection test, not a full app
                    auto_debug_attempt=auto_debug_attempt  # Pass through auto-debug state
                )
                
                # Handle the action returned by debug analyzer
                if action == 'claude_fixed':
                    # Use the code fixed by Claude Code SDK directly
                    printer.print("✅ Using code fixed by Claude Code SDK...")
                    self.context.code_generation.connection_test_code = debug_feedback
                    # Save the fixed code to file
                    test_code_path = os.path.join(self.context.code_generation.app_extract_dir, "connection_test.py")
                    with open(test_code_path, 'w', encoding='utf-8') as file:
                        file.write(debug_feedback)
                    # If we're in auto-debug mode, the loop will call us again
                    # Just return False to trigger the next iteration
                    if auto_debug_attempt > 0:
                        return False  # Will trigger next auto-debug attempt
                    else:
                        return await self._run_connection_test()
                elif action == 'manual_feedback':
                    # Get manual feedback and regenerate
                    feedback = printer.input("Please provide feedback on how to fix the error: ").strip()
                    if feedback:
                        if await self._regenerate_connection_test_with_feedback(feedback):
                            return await self._run_connection_test()
                    return False
                    
                elif action == 'manual_fix':
                    # User fixed code manually in IDE, just retry
                    printer.print("🔄 Running your manually fixed code from the IDE...")
                    return await self._run_manual_connection_test()
                    
                elif action == 'fixed_in_ide':
                    # User says they fixed it - run one final test to get the output
                    printer.print("✅ Running final connection test with your fixes...")
                    return await self._run_manual_connection_test()
                    
                elif action == 'abort':
                    printer.print("🛑 Aborting workflow as per user request.")
                    return False
                    
                elif action == 'auto_debug':
                    # User selected auto-debug mode - continue with debugging using existing logs
                    printer.print("🚀 Auto-debug mode activated. Will automatically retry debugging.")
                    # Pass the existing logs directly to auto-debug instead of re-running sandbox
                    return await self._run_connection_test_with_auto_debug(
                        auto_debug_attempt=1,
                        existing_logs=logs,
                        existing_code=self.context.code_generation.connection_test_code
                    )
                    
                elif action == 'auto_debug_failed':
                    # Auto-debug attempt failed but we're in auto-debug mode
                    # This shouldn't happen in connection test as we handle it differently
                    printer.print("❌ Auto-debug failed.")
                    return False
                    
            elif execution_status == 'success':
                printer.print("✅ Connection test completed successfully with no apparent errors!")
                self.context.connection_test_output = logs
                return True  # Return success status
            elif execution_status == 'uncertain':
                printer.print("⚠️ Could not determine if connection test succeeded.")
                printer.print("  - No clear success or error indicators found in logs")
                if get_user_approval("Continue anyway?"):
                    self.context.connection_test_output = logs
                else:
                    return False
                printer.print("📊 **Sample Data Output:**")
                printer.print(logs[:2000] + "..." if len(logs) > 2000 else logs)
                return True
                
        except Exception as e:
            printer.print(f"❌ Error during manual connection test: {str(e)}")
            return False
    
    
    async def _regenerate_connection_test_with_feedback(self, feedback: str) -> bool:
        """Regenerate connection test code with feedback from debug analysis."""
        try:
            # Get the user's source requirements/prompt
            user_requirements = getattr(self.context.technology, 'source_technology', None) or \
                              self.context.technology.destination_technology or "external system"
            
            # Use the app directory that already has app.yaml configured
            test_dir = self.context.code_generation.app_extract_dir
            
            # Add feedback to the user requirements
            test_request_with_feedback = f"{user_requirements}\n\n## Debug Feedback:\n{feedback}"
            
            # Use Claude Code to regenerate with feedback using the specialized method
            regenerated_code, _ = await self.claude_code_service.generate_code_for_connection_test(
                user_prompt=test_request_with_feedback,
                app_dir=test_dir,
                workflow_type="source"
            )
            
            if regenerated_code:
                self.context.code_generation.connection_test_code = regenerated_code
                printer.print("✅ Connection test code regenerated with fixes using Claude Code SDK.")
                
                # IMPORTANT: Update session environment variables after regeneration
                # The regenerated code might have new or modified environment variables
                from workflow_tools.phases.shared.env_var_management import EnvVarManager
                env_var_manager = EnvVarManager(self.context, self.run_config, self.debug_mode)
                
                if hasattr(self.context.deployment, 'session_id') and self.context.deployment.session_id:
                    printer.print("\n📋 Updating environment variables after code regeneration...")
                    await env_var_manager.sync_and_update_session_environment(
                        session_id=self.context.deployment.session_id,
                        code=regenerated_code,
                        force_re_collect=True  # Re-collect values since code changed
                    )
                
                return True
            else:
                printer.print("❌ Failed to regenerate connection test code with Claude Code SDK.")
                return False
                
        except Exception as e:
            printer.print(f"❌ Error regenerating code: {str(e)}")
            return False
    
    def _save_sample_data(self) -> bool:
        """Save sample data for schema analysis."""
        printer.print("💾 Saving sample data for schema analysis.")
        
        try:
            if not hasattr(self.context, 'connection_test_output'):
                printer.print("⚠️  No connection test output to save.")
                return True
            
            # Save sample data to temp directory
            sample_data_path = WorkingDirectory.get_temp_sample_path()
            
            with open(sample_data_path, 'w', encoding='utf-8') as file:
                tech_name = getattr(self.context.technology, 'source_technology', None) or self.context.technology.destination_technology
                file.write(f"Source Technology: {tech_name}\n")
                file.write(f"Sample Data Collected: {datetime.now()}\n")
                file.write("=" * 50 + "\n")
                file.write(self.context.connection_test_output)
            
            self.context.sample_data_file = sample_data_path
            printer.print(f"✅ Sample data saved: {sample_data_path}")
            
            return True
            
        except Exception as e:
            printer.print(f"❌ Error saving sample data: {str(e)}")
            return False
    

    
