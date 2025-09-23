"""Service for analyzing and debugging code errors."""

import os
import re
import traceback
from typing import Dict, Any, Optional, List, Tuple
from agents import Agent, RunConfig

from workflow_tools.contexts import WorkflowContext
from workflow_tools.services.runner_utils import run_agent_with_retry
from workflow_tools.common import extract_python_code_from_llm_output
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.core.prompt_manager import PromptManager
from workflow_tools.core.config_loader import ConfigLoader
from workflow_tools.services.model_utils import create_agent_with_model_config
config = ConfigLoader()


class DebugAnalyzer:
    """Analyzes errors and provides debugging solutions."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        """Initialize the debug analyzer.
        
        Args:
            context: Workflow context
            debug_mode: Whether to enable debug mode
        """
        self.context = context
        self.debug_mode = debug_mode
        self.run_config = RunConfig(workflow_name="Debug Analysis")
        self.prompt_manager = PromptManager()
    
    async def analyze_error(self, code: str, error_logs: str, 
                           workflow_type: str = "sink") -> Dict[str, Any]:
        """Analyze an error and suggest fixes.
        
        Args:
            code: The code that produced the error
            error_logs: Error logs from execution
            workflow_type: Type of workflow (sink or source)
        
        Returns:
            Dictionary containing analysis results and suggested fixes
        """
        # Parse error details
        error_info = self._parse_error_logs(error_logs)
        
        # Create debug agent
        agent = self._create_debug_agent(workflow_type)
        
        # Prepare debug prompt
        prompt = self._prepare_debug_prompt(code, error_logs, error_info)
        
        # Run analysis
        result = await self._run_agent(agent, prompt)
        
        if result:
            return self._parse_debug_response(result)
        
        return {
            "success": False,
            "error_type": error_info.get("type", "Unknown"),
            "message": "Failed to analyze error",
            "suggested_fix": None
        }
    
    async def suggest_fix(self, code: str, error_logs: str,
                         workflow_type: str = "sink") -> Optional[str]:
        """Suggest a fixed version of the code.
        
        Args:
            code: The code that produced the error
            error_logs: Error logs from execution
            workflow_type: Type of workflow (sink or source)
        
        Returns:
            Fixed code or None if fix generation failed
        """
        try:
            analysis = await self.analyze_error(code, error_logs, workflow_type)
            
            if self.debug_mode:
                print(f"Debug: Analysis result: success={analysis.get('success')}, has_suggested_fix={bool(analysis.get('suggested_fix'))}")
            
            if not analysis.get("suggested_fix"):
                print("❌ Debug: No suggested fix in analysis result")
                return None
            
            # Extract Python code from the suggested fix
            fixed_code = extract_python_code_from_llm_output(analysis["suggested_fix"])
            
            if not fixed_code:
                print("❌ Debug: Failed to extract Python code from AI response")
                if self.debug_mode:
                    print(f"Debug: AI response was: {analysis['suggested_fix'][:500]}...")
                return None
            
            return fixed_code
            
        except Exception as e:
            print(f"❌ Debug: Exception in suggest_fix: {type(e).__name__}: {str(e)}")
            if self.debug_mode:
                traceback.print_exc()
            return None

    async def run_auto_debug_loop(self, code: str, error_logs: str,
                                 workflow_type: str = "sink",
                                 is_timeout_error: bool = False,
                                 is_connection_test: bool = False,
                                 max_attempts: int = 10,
                                 run_code_callback=None) -> Tuple[str, Optional[str]]:
        """Centralized auto-debug loop that automatically retries Claude Code fixes.

        Args:
            code: The code that produced the error
            error_logs: Error logs from execution
            workflow_type: Type of workflow (sink or source)
            is_timeout_error: Whether this is a timeout error
            is_connection_test: Whether this is debugging a connection test
            max_attempts: Maximum number of auto-debug attempts
            run_code_callback: Optional async callback to run fixed code and get new logs

        Returns:
            Tuple of (action, fixed_code) where action indicates the result:
            'claude_fixed' if Claude successfully fixed the code
            'auto_debug_failed' if max attempts reached without success
        """
        from workflow_tools.common import printer

        printer.print(f"🚀 Starting auto-debug mode (max {max_attempts} attempts)...")

        # Initialize error log history to track all attempts
        error_log_history = []
        cumulative_error_logs = error_logs
        current_code = code

        for attempt in range(1, max_attempts + 1):
            printer.print(f"🤖 Auto-debug attempt {attempt}/{max_attempts} - using Claude Code SDK...")

            # Build cumulative error context
            if error_log_history:
                cumulative_error_logs = self._build_cumulative_error_logs(error_log_history, error_logs)

            # Always use Claude Code SDK option automatically
            action, fixed_code = await self.interactive_debug_workflow(
                code=current_code,
                error_logs=cumulative_error_logs,
                workflow_type=workflow_type,
                is_timeout_error=is_timeout_error,
                is_connection_test=is_connection_test,
                auto_debug_attempt=attempt  # Pass current attempt
            )

            # Handle the result
            if action == 'claude_fixed' and fixed_code:
                # If we have a callback to run the code, test the fix
                if run_code_callback and attempt < max_attempts:
                    printer.print(f"🧪 Testing fix from attempt {attempt}...")
                    try:
                        new_logs = await run_code_callback(fixed_code)

                        # Check if new logs contain errors
                        if self._contains_errors(new_logs):
                            # Add to history and continue
                            error_log_history.append({
                                'attempt': attempt,
                                'logs': new_logs,
                                'code_snippet': fixed_code[:500] + "..." if len(fixed_code) > 500 else fixed_code
                            })
                            current_code = fixed_code
                            printer.print(f"⚠️ Fix from attempt {attempt} still has errors. Continuing...")
                            continue
                        else:
                            # Success!
                            printer.print(f"✅ Auto-debug succeeded on attempt {attempt}!")
                            return ('claude_fixed', fixed_code)
                    except Exception as e:
                        printer.print(f"⚠️ Error testing fix: {e}")
                        # Add error to history
                        error_log_history.append({
                            'attempt': attempt,
                            'logs': str(e),
                            'code_snippet': fixed_code[:500] + "..." if len(fixed_code) > 500 else fixed_code
                        })
                        current_code = fixed_code
                        continue
                else:
                    # No callback or last attempt, assume success
                    printer.print(f"✅ Auto-debug completed on attempt {attempt}!")
                    return ('claude_fixed', fixed_code)

            elif action == 'auto_debug_failed':
                # Continue to next attempt
                if attempt < max_attempts:
                    printer.print(f"🔄 Auto-debug attempt {attempt} failed. Retrying...")
                    # Update code for next attempt if we have any changes
                    if fixed_code:
                        current_code = fixed_code
                        # Add failed attempt to history
                        error_log_history.append({
                            'attempt': attempt,
                            'logs': "Claude unable to fix the error",
                            'code_snippet': fixed_code[:500] + "..." if len(fixed_code) > 500 else fixed_code
                        })
                else:
                    printer.print(f"❌ Auto-debug reached maximum attempts ({max_attempts}). Failed to fix the error.")
                    return ('auto_debug_failed', None)
            else:
                # Unexpected action during auto-debug
                printer.print(f"⚠️ Unexpected action '{action}' during auto-debug. Treating as failure.")
                if attempt < max_attempts:
                    continue
                else:
                    return ('auto_debug_failed', None)

        return ('auto_debug_failed', None)

    async def handle_debug_workflow(self, code: str, error_logs: str,
                                   workflow_type: str = "sink",
                                   is_timeout_error: bool = False,
                                   is_connection_test: bool = False,
                                   env_vars_collected: bool = False,
                                   run_code_callback=None) -> Tuple[str, Optional[str]]:
        """Simplified entry point for debug workflows that handles both manual and auto modes.

        This method should be used by phases instead of directly calling interactive_debug_workflow.
        It handles the user choice between manual debugging and auto-debug mode.

        Args:
            code: The code that produced the error
            error_logs: Error logs from execution
            workflow_type: Type of workflow (sink or source)
            is_timeout_error: Whether this is a timeout error
            is_connection_test: Whether this is debugging a connection test
            env_vars_collected: Whether env vars have already been collected (to prevent re-collection)
            run_code_callback: Optional async callback to run fixed code and get new logs

        Returns:
            Tuple of (action, fixed_code) where action indicates the result
        """
        # First, show the interactive menu to let user choose debugging approach
        action, fixed_code = await self.interactive_debug_workflow(
            code=code,
            error_logs=error_logs,
            workflow_type=workflow_type,
            is_timeout_error=is_timeout_error,
            is_connection_test=is_connection_test,
            auto_debug_attempt=0  # Start with manual mode
        )

        # If user chose auto-debug, switch to the centralized auto-debug loop
        if action == 'auto_debug':
            return await self.run_auto_debug_loop(
                code=code,
                error_logs=error_logs,
                workflow_type=workflow_type,
                is_timeout_error=is_timeout_error,
                is_connection_test=is_connection_test,
                max_attempts=10,
                run_code_callback=run_code_callback
            )

        return (action, fixed_code)
    
    async def interactive_debug_workflow(self, code: str, error_logs: str,
                                        workflow_type: str = "sink",
                                        is_timeout_error: bool = False,
                                        is_connection_test: bool = False,
                                        auto_debug_attempt: int = 0) -> Tuple[str, Optional[str]]:
        """Handle the complete interactive debug workflow with user choices.
        
        Args:
            code: The code that produced the error
            error_logs: Error logs from execution
            workflow_type: Type of workflow (sink or source)
            is_timeout_error: Whether this is a timeout error
            is_connection_test: Whether this is debugging a connection test (not full app)
            auto_debug_attempt: Current auto-debug attempt number (0 = not in auto-debug mode)
        
        Returns:
            Tuple of (action, data) where action is one of:
            'retry', 'manual_feedback', 'manual_fix', 'fixed_in_ide', 'abort', 'auto_debug'
            and data is the debug feedback/fix to pass to code generation AI
        """
        from workflow_tools.common import printer, get_user_approval
        from workflow_tools.core.config_loader import ConfigLoader
        
        # Get max auto-debug attempts from config
        config = ConfigLoader()
        # Use a default value since ConfigLoader doesn't have get_value method
        # TODO: Add proper config support for debug settings
        max_auto_attempts = 10
        
        # If in auto-debug mode and under limit, automatically choose option 1
        if auto_debug_attempt > 0 and auto_debug_attempt <= max_auto_attempts:
            printer.print(f"🤖 Auto-debug attempt {auto_debug_attempt}/{max_auto_attempts} - using Claude Code SDK...")
            choice = '1'  # Automatically select Claude Code SDK option
        else:
            # Show menu to user
            if auto_debug_attempt > max_auto_attempts:
                printer.print(f"\n⚠️ Auto-debug reached maximum attempts ({max_auto_attempts}). Switching to manual mode.")
                auto_debug_attempt = 0  # Reset to exit auto-debug mode
            
            printer.print("⚠️ Errors detected in the logs!")
            
            # Use questionary for better menu selection
            from workflow_tools.core.questionary_utils import select
            
            choices = [
                {'name': '🤖 Let Claude Code SDK fix the error directly', 'value': '1'},
                {'name': '✏️ Provide manual feedback yourself', 'value': '2'},
                {'name': '🔧 Retry with manual code fix (fix directly in IDE)', 'value': '3'},
                {'name': '➡️ Continue anyway (error not serious/already fixed)', 'value': '4'},
                {'name': '❌ Abort the workflow', 'value': '5'},
                {'name': '⬅️ Go back to previous phase', 'value': '6'},
                {'name': f'🚀 Auto-debug (keep retrying until fixed or {max_auto_attempts} attempts)', 'value': '7'}
            ]
            
            choice = select("Choose debugging approach:", choices, show_border=True)
            
        # Process the choice
        if choice == '6':
            raise NavigationBackRequest("User requested to go back")
        elif choice == '7' and auto_debug_attempt == 0:  # Only allow option 7 if not already in auto-debug mode
            # User selected auto-debug mode
            printer.print(f"🚀 Starting auto-debug mode (max {max_auto_attempts} attempts)...")
            return ('auto_debug', None)
        elif choice == '1':
            printer.print("🤖 Using Claude Code SDK to fix the error...")
            
            # Use Claude Code SDK to debug and fix the code directly
            from workflow_tools.services.claude_code_service import ClaudeCodeService
            claude_service = ClaudeCodeService(self.context, debug_mode=self.debug_mode)
            
            # Get the app directory from context
            app_dir = self.context.code_generation.app_extract_dir
            if not app_dir:
                printer.print("❌ Error: No app directory found in context")
                if auto_debug_attempt > 0:
                    return ('auto_debug_failed', None)  # Special return for auto-debug failure
                return ('abort', None)
            
            try:
                # Use appropriate debug method based on whether this is a connection test
                if is_connection_test:
                    # Use specialized connection test debugging
                    fixed_code = await claude_service.debug_connection_test(error_logs, app_dir, code)
                else:
                    # Use regular Claude Code SDK debugging
                    fixed_code = await claude_service.debug_code(error_logs, app_dir, code)
                
                if fixed_code:
                    printer.print("✅ Claude Code SDK successfully fixed the code!")
                    # Return the action to regenerate with the fixed code
                    return ('claude_fixed', fixed_code)
                else:
                    printer.print("❌ Claude Code SDK was unable to fix the error.")
                    if auto_debug_attempt > 0:
                        return ('auto_debug_failed', None)  # Special return for auto-debug failure
                    # In manual mode, loop back to menu
                    
            except Exception as e:
                printer.print(f"❌ Error using Claude Code SDK: {str(e)}")
                if auto_debug_attempt > 0:
                    return ('auto_debug_failed', None)  # Special return for auto-debug failure
                # In manual mode, loop back to menu
        
        elif choice == '2':
            printer.print("📝 Please provide feedback on how to fix the error based on the logs:")
            user_feedback = printer.input("> ").strip()
            
            if not user_feedback:
                printer.print("⚠️ No feedback provided. Please try again.")
                if auto_debug_attempt > 0:
                    return ('auto_debug_failed', None)
                # In manual mode, loop back to menu
            else:
                printer.print("🤖 Sending your feedback to Claude Code SDK along with error logs...")
                
                # Use Claude Code SDK with user feedback
                from workflow_tools.services.claude_code_service import ClaudeCodeService
                claude_service = ClaudeCodeService(self.context, debug_mode=self.debug_mode)
                
                # Get the app directory from context
                app_dir = self.context.code_generation.app_extract_dir
                if not app_dir:
                    printer.print("❌ Error: No app directory found in context")
                    if auto_debug_attempt > 0:
                        return ('auto_debug_failed', None)
                    return ('abort', None)
                
                try:
                    # Combine user feedback with error logs for Claude
                    enhanced_error_logs = f"{error_logs}\n\n## User Feedback:\n{user_feedback}"
                    
                    # Use appropriate debug method based on whether this is a connection test
                    if is_connection_test:
                        # Use specialized connection test debugging
                        fixed_code = await claude_service.debug_connection_test(enhanced_error_logs, app_dir, code)
                    else:
                        # Use regular Claude Code SDK debugging
                        fixed_code = await claude_service.debug_code(enhanced_error_logs, app_dir, code)
                    
                    if fixed_code:
                        printer.print("✅ Claude Code SDK successfully fixed the code based on your feedback!")
                        return ('claude_fixed', fixed_code)
                    else:
                        printer.print("❌ Claude Code SDK was unable to fix the error with your feedback.")
                        if auto_debug_attempt > 0:
                            return ('auto_debug_failed', None)
                        # In manual mode, loop back to menu
                        
                except Exception as e:
                    printer.print(f"❌ Error using Claude Code SDK: {str(e)}")
                    if auto_debug_attempt > 0:
                        return ('auto_debug_failed', None)
                    # In manual mode, loop back to menu
        
        elif choice == '3':
            printer.print("📝 Please fix the code directly in the Quix Cloud IDE.")
            printer.print("   You can modify the code and environment variables as needed.")
            printer.input("Press ENTER when you've fixed the code and are ready to retry: ")
            return ('manual_fix', None)
        
        elif choice == '4':
            return ('fixed_in_ide', None)
        
        elif choice == '5':
            return ('abort', None)
            
        else:
            printer.print("❌ Invalid choice. Please enter a number between 1 and 7.")
    
    def identify_error_pattern(self, error_logs: str) -> str:
        """Identify common error patterns.
        
        Args:
            error_logs: Error logs to analyze
        
        Returns:
            Identified error pattern or "unknown"
        """
        patterns = {
            "import_error": r"(ImportError|ModuleNotFoundError).*No module named",
            "syntax_error": r"SyntaxError:",
            "type_error": r"TypeError:",
            "attribute_error": r"AttributeError:",
            "connection_error": r"(ConnectionError|ConnectionRefusedError|TimeoutError)",
            "permission_error": r"PermissionError:",
            "key_error": r"KeyError:",
            "value_error": r"ValueError:",
            "name_error": r"NameError:",
            "index_error": r"IndexError:",
            "file_not_found": r"FileNotFoundError:",
            "authentication_error": r"(AuthenticationError|401|403)",
            "memory_error": r"MemoryError:",
            "runtime_error": r"RuntimeError:"
        }
        
        for pattern_name, pattern_regex in patterns.items():
            if re.search(pattern_regex, error_logs, re.IGNORECASE):
                return pattern_name
        
        return "unknown"
    
    def _build_cumulative_error_logs(self, error_log_history: List[Dict], initial_logs: str) -> str:
        """Build a cumulative error log string from history.

        Args:
            error_log_history: List of previous error attempts
            initial_logs: The initial error logs from the first run

        Returns:
            Formatted cumulative error log string
        """
        sections = []

        # Add initial error
        sections.append("=== INITIAL ERROR (Attempt 0) ===")
        sections.append(initial_logs)

        # Add each attempt's errors
        for entry in error_log_history:
            sections.append(f"\n=== ATTEMPT {entry['attempt']} ERROR LOGS ===")
            sections.append(f"After applying fix, got these NEW errors:")
            sections.append(entry['logs'])
            if 'code_snippet' in entry:
                sections.append(f"\n[Code snippet that produced this error:]")
                sections.append(entry['code_snippet'])

        return "\n".join(sections)

    def _contains_errors(self, logs: str) -> bool:
        """Check if logs contain error indicators.

        Args:
            logs: Log output to check

        Returns:
            True if errors are detected, False otherwise
        """
        if not logs:
            return False

        error_indicators = [
            'error', 'exception', 'traceback', 'failed',
            'Error', 'Exception', 'Traceback', 'Failed',
            'ERROR', 'EXCEPTION', 'FAILED', 'CRITICAL',
            'ModuleNotFoundError', 'ImportError', 'AttributeError',
            'TypeError', 'ValueError', 'KeyError', 'NameError',
            'SyntaxError', 'IndentationError', 'RuntimeError',
            'ConnectionError', 'TimeoutError', 'PermissionError'
        ]

        # Check for any error indicators
        logs_lower = logs.lower()
        for indicator in error_indicators:
            if indicator.lower() in logs_lower:
                # Avoid false positives from success messages
                if 'no error' not in logs_lower and 'error: 0' not in logs_lower:
                    return True

        return False

    def extract_missing_imports(self, error_logs: str) -> List[str]:
        """Extract missing module names from import errors.
        
        Args:
            error_logs: Error logs containing import errors
        
        Returns:
            List of missing module names
        """
        missing_modules = []
        
        # Pattern for ModuleNotFoundError or ImportError
        pattern = r"No module named ['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, error_logs)
        
        for match in matches:
            # Clean up the module name
            module = match.split('.')[0]
            if module not in missing_modules:
                missing_modules.append(module)
        
        return missing_modules
    
    def _parse_error_logs(self, error_logs: str) -> Dict[str, Any]:
        """Parse error logs to extract key information.
        
        Args:
            error_logs: Raw error logs
        
        Returns:
            Dictionary with parsed error information
        """
        info = {
            "type": "Unknown",
            "message": "",
            "line_number": None,
            "file": None,
            "traceback": []
        }
        
        # Extract error type
        error_type_match = re.search(r"(\w+Error):", error_logs)
        if error_type_match:
            info["type"] = error_type_match.group(1)
        
        # Extract error message
        error_msg_match = re.search(r"\w+Error:\s*(.+?)(?:\n|$)", error_logs)
        if error_msg_match:
            info["message"] = error_msg_match.group(1).strip()
        
        # Extract line number if present
        line_match = re.search(r"line (\d+)", error_logs)
        if line_match:
            info["line_number"] = int(line_match.group(1))
        
        # Extract file information
        file_match = re.search(r'File "([^"]+)"', error_logs)
        if file_match:
            info["file"] = file_match.group(1)
        
        # Extract traceback lines
        traceback_lines = []
        for line in error_logs.split('\n'):
            if line.strip().startswith('File '):
                traceback_lines.append(line.strip())
        info["traceback"] = traceback_lines
        
        return info
    
    def _clean_and_truncate_logs(self, logs: str, max_length: int = 8000) -> str:
        """Clean logs of invisible characters and truncate intelligently if needed.
        
        Args:
            logs: Raw log string
            max_length: Maximum length for logs to prevent token limits
        
        Returns:
            Cleaned and potentially truncated logs
        """
        import unicodedata
        
        # Remove zero-width spaces and other invisible Unicode characters
        # These include: zero-width space (U+200B), zero-width non-joiner (U+200C), 
        # zero-width joiner (U+200D), and other format characters
        cleaned = ''.join(
            char for char in logs 
            if unicodedata.category(char) not in ('Cf', 'Cc') or char in ('\n', '\r', '\t')
        )
        
        # Also remove any null bytes
        cleaned = cleaned.replace('\x00', '')
        
        # If logs are within limit, return as is
        if len(cleaned) <= max_length:
            return cleaned
        
        # Otherwise, intelligently truncate while preserving error information
        lines = cleaned.split('\n')
        
        # Find error lines (lines containing common error indicators)
        error_indicators = ['Error', 'Exception', 'Traceback', 'Failed', 'failure', 
                          'error', 'CRITICAL', 'FATAL', 'WARNING']
        error_lines = []
        error_line_indices = []
        
        for i, line in enumerate(lines):
            if any(indicator in line for indicator in error_indicators):
                error_lines.append(line)
                error_line_indices.append(i)
        
        # Strategy: Keep first 1500 chars, error context, and last 1500 chars
        result_parts = []
        
        # Add beginning of logs
        beginning_chars = 0
        beginning_lines = []
        for line in lines[:50]:  # First 50 lines max
            if beginning_chars + len(line) + 1 > 1500:
                break
            beginning_lines.append(line)
            beginning_chars += len(line) + 1
        
        if beginning_lines:
            result_parts.append('\n'.join(beginning_lines))
            result_parts.append('\n... [truncated for brevity] ...\n')
        
        # Add error context (lines around errors)
        if error_line_indices:
            context_lines = set()
            for idx in error_line_indices[:10]:  # First 10 errors
                # Add 5 lines before and after each error
                for i in range(max(0, idx - 5), min(len(lines), idx + 6)):
                    context_lines.add(i)
            
            # Convert to sorted list and group consecutive lines
            sorted_indices = sorted(context_lines)
            if sorted_indices:
                current_group = [lines[sorted_indices[0]]]
                last_idx = sorted_indices[0]
                
                for idx in sorted_indices[1:]:
                    if idx == last_idx + 1:
                        current_group.append(lines[idx])
                    else:
                        result_parts.append('\n'.join(current_group))
                        result_parts.append('\n... [truncated] ...\n')
                        current_group = [lines[idx]]
                    last_idx = idx
                
                result_parts.append('\n'.join(current_group))
                result_parts.append('\n... [truncated] ...\n')
        
        # Add end of logs
        ending_chars = 0
        ending_lines = []
        for line in reversed(lines[-50:]):  # Last 50 lines max
            if ending_chars + len(line) + 1 > 1500:
                break
            ending_lines.insert(0, line)
            ending_chars += len(line) + 1
        
        if ending_lines:
            result_parts.append('\n'.join(ending_lines))
        
        result = '\n'.join(result_parts)
        
        # Final truncation if still too long
        if len(result) > max_length:
            result = result[:max_length - 100] + '\n... [final truncation] ...'
        
        return result
    
    def _create_debug_agent(self, workflow_type: str) -> Agent:
        """Create a debug agent for error analysis.
        
        Args:
            workflow_type: Type of workflow (sink or source)
        
        Returns:
            Configured Agent instance
        """
        agent_name = f"{workflow_type.capitalize()}DebugAgent"
        instructions = self.prompt_manager.load_agent_instructions(agent_name)
        
        # Use centralized agent creation with model configuration handling
        # This will automatically handle GPT-5 specific parameters like verbosity and reasoning
        return create_agent_with_model_config(
            agent_name=agent_name,
            task_type="debugging",
            workflow_type=workflow_type,
            instructions=instructions,
            context_type=WorkflowContext
        )
    
    def _prepare_debug_prompt(self, code: str, error_logs: str, 
                             error_info: Dict[str, Any]) -> str:
        """Prepare the prompt for debug analysis.
        
        Args:
            code: The code that failed
            error_logs: Error logs
            error_info: Parsed error information
        
        Returns:
            Formatted debug prompt
        """
        # Clean and prepare logs before including in prompt
        cleaned_logs = self._clean_and_truncate_logs(error_logs)
        
        # Check if we have original connection test code for context
        connection_code_section = ""
        if (hasattr(self.context, 'code_generation') and 
            hasattr(self.context.code_generation, 'connection_test_code') and 
            self.context.code_generation.connection_test_code):
            connection_code_section = f"""
        
        For reference, here is some earlier more basic connection code that worked fine before we added functionality to use QuixStreams. The current code we are trying to run was created using this earlier connection code as a basis:
        ```python
        {self.context.code_generation.connection_test_code}
        ```
        """
        
        prompt = f"""
        Please analyze the following error and provide a solution:
        
        Error Type: {error_info.get('type', 'Unknown')}
        Error Message: {error_info.get('message', 'No message')}
        {f"Line Number: {error_info['line_number']}" if error_info.get('line_number') else ""}
        
        Error Logs:
        ```
        {cleaned_logs}
        ```{connection_code_section}
        
        Code that produced the error:
        ```python
        {code}
        ```
        
        Please provide:
        1. Root cause analysis
        2. Specific fix for the error
        3. Complete corrected code
        """
        
        return prompt
    
    def _parse_debug_response(self, response: str) -> Dict[str, Any]:
        """Parse the debug agent's response.
        
        Args:
            response: Raw response from debug agent
        
        Returns:
            Parsed debug information
        """
        result = {
            "success": True,
            "root_cause": "",
            "fix_description": "",
            "suggested_fix": None
        }
        
        # Extract root cause if mentioned
        root_cause_match = re.search(r"root cause[:\s]+(.+?)(?:\n|$)", response, re.IGNORECASE)
        if root_cause_match:
            result["root_cause"] = root_cause_match.group(1).strip()
        
        # Extract fix description
        fix_match = re.search(r"fix[:\s]+(.+?)(?:\n|$)", response, re.IGNORECASE)
        if fix_match:
            result["fix_description"] = fix_match.group(1).strip()
        
        # The entire response contains the suggested fix
        result["suggested_fix"] = response
        
        return result
    
    
    async def _run_agent(self, agent: Agent, prompt: str) -> Optional[str]:
        """Run an agent with the given prompt.
        
        Args:
            agent: The agent to run
            prompt: The prompt to send
        
        Returns:
            Agent response string or None if failed
        """
        try:
            result = await run_agent_with_retry(
                starting_agent=agent,
                input=prompt,
                context=self.context,
                operation_name=f"Debug analysis for {workflow_type}"
            )

            # Handle retry exhaustion
            if result is None:
                if self.debug_mode:
                    print("❌ Debug: Agent failed after retries due to API overload")
                return None

            # Extract the final output string from the RunResult object
            if result:
                if hasattr(result, 'final_output'):
                    if self.debug_mode:
                        print(f"Debug: Agent returned response, length: {len(result.final_output) if result.final_output else 0}")
                    return result.final_output
                else:
                    print(f"❌ Debug: RunResult has no 'final_output' attribute. Available attributes: {dir(result)}")
            else:
                print("❌ Debug: Agent returned None/empty result")
            
            return None
            
        except Exception as e:
            print(f"❌ Debug: Error running debug agent: {type(e).__name__}: {str(e)}")
            if self.debug_mode:
                traceback.print_exc()
            return None