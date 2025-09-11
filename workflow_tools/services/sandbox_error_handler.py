# sandbox_error_handler.py - Centralized error handling for sandbox phases

import re
import asyncio
from typing import Tuple, Optional
from workflow_tools.common import printer, get_user_approval
from workflow_tools.contexts import WorkflowContext
from workflow_tools.exceptions import NavigationBackRequest


class SandboxErrorHandler:
    """Centralized error handling for sandbox testing phases."""
    
    def __init__(self, context: Optional[WorkflowContext] = None, debug_mode: bool = False):
        """Initialize the sandbox error handler.
        
        Args:
            context: Optional workflow context for AI analysis
            debug_mode: Whether to enable debug mode
        """
        self.context = context
        self.debug_mode = debug_mode
        self.ai_analyzer = None
        
        # Only create AI analyzer if context is provided
        if context:
            try:
                from workflow_tools.services.log_analyzer import LogAnalyzer
                self.ai_analyzer = LogAnalyzer(context, debug_mode)
            except ImportError:
                if debug_mode:
                    printer.print_debug("⚠️ LogAnalyzer not available, using deterministic analysis only")
    
    def analyze_logs(self, logs: str, workflow_type: str = "sink") -> Tuple[bool, bool, bool]:
        """Analyze logs for errors, timeouts, and success indicators.
        
        Args:
            logs: The execution logs to analyze
            workflow_type: Either "sink" or "source"
            
        Returns:
            Tuple of (has_error, is_timeout_error, has_success)
        """
        # Check for critical errors and exit codes
        critical_error_indicators = [
            "Traceback", 
            "Exception:", 
            "AttributeError:", 
            "NameError:", 
            "TypeError:",
            "ValueError:",
            "KeyError:",
            "ImportError:",
            "SyntaxError:",
            "exit code 1",
            "exit code: 1",
            "terminated with non-zero exit code",
            "quixstreams.sources.base.exceptions.SourceException"
        ]
        
        # Check for general errors - use case-sensitive matching for better accuracy
        # Only match "Error" at word boundaries to avoid false positives from data like "temperature"
        error_indicators = ["Error:", "ERROR:", "Exception", "Failed", "FAILED", "Traceback"]
        
        # Check if there's a critical error (these override any success indicators)
        has_critical_error = any(indicator in logs for indicator in critical_error_indicators)
        
        # For general errors, be more careful to avoid false positives
        has_general_error = any(indicator in logs for indicator in error_indicators)
        
        # Also check for standalone "error" or "failed" with word boundaries
        has_word_error = bool(re.search(r'\berror\b', logs, re.IGNORECASE)) or bool(re.search(r'\bfailed\b', logs, re.IGNORECASE))
        
        # Combine all error checks, but exclude common false positives
        has_error = has_critical_error or has_general_error or (has_word_error and not any(fp in logs.lower() for fp in ["temperature", "parameter", "configured"]))
        
        # Check for timeout errors specifically
        is_timeout_error = "ReadTimeout" in logs or "timeout" in logs.lower()
        
        # Check for success indicators based on workflow type
        if workflow_type == "source":
            success_indicators = ["Publishing", "Sending", "Produced", "producing", "sent", "published"]
        else:  # sink
            success_indicators = ["Successfully", "Completed", "Connected", "processed", "inserted", "written"]
        
        # Only consider it a success if there are success indicators AND no critical errors
        has_success = (not has_critical_error) and any(indicator.lower() in logs.lower() for indicator in success_indicators)
        
        return has_error, is_timeout_error, has_success
    
    async def determine_execution_status_with_ai(
        self, 
        logs: str,
        test_objective: str,
        workflow_type: str = "sink",
        code_context: Optional[str] = None,
        is_connection_test: bool = False
    ) -> str:
        """Determine execution status using AI analysis.
        
        Args:
            logs: The execution logs
            test_objective: What the test was trying to achieve
            workflow_type: Either "sink" or "source"
            code_context: Optional code that was executed
            is_connection_test: Whether this is a connection test
            
        Returns:
            Status string: 'error', 'success', or 'uncertain'
        """
        # ALWAYS use AI analysis if available
        if self.ai_analyzer:
            try:
                if self.debug_mode:
                    printer.print_debug("🤖 Using AI to analyze execution logs...")
                
                # Run AI analysis
                ai_result = await self.ai_analyzer.analyze_execution_logs(
                    logs=logs,
                    test_objective=test_objective,
                    workflow_type=workflow_type,
                    code_context=code_context,
                    is_connection_test=is_connection_test
                )
                
                # Display AI analysis results
                printer.print("\n" + "="*60)
                printer.print("🤖 AI LOG ANALYSIS RESULTS")
                printer.print("="*60)
                printer.print(f"✅ Success: {ai_result.success}")
                printer.print(f"📊 Confidence: {ai_result.confidence.upper()}")
                printer.print(f"💭 Reasoning: {ai_result.reasoning}")
                
                if ai_result.key_indicators:
                    printer.print("\n📍 Key Indicators:")
                    for indicator in ai_result.key_indicators[:5]:  # Show top 5
                        printer.print(f"  • {indicator}")
                
                if ai_result.recommendation:
                    printer.print(f"\n💡 Recommendation: {ai_result.recommendation}")
                
                printer.print("="*60)
                
                # Return status based on AI analysis
                if ai_result.success:
                    return 'success'
                else:
                    # For failures, check confidence to decide between error and uncertain
                    if ai_result.confidence in ['high', 'medium']:
                        return 'error'
                    else:
                        return 'uncertain'
                    
            except Exception as e:
                printer.print(f"⚠️ AI analysis failed: {e}")
                printer.print("Falling back to deterministic analysis...")
                # Fall back to deterministic if AI fails
                has_error, is_timeout_error, has_success = self.analyze_logs(logs, workflow_type)
                return self.determine_execution_status(has_error, has_success)
        
        # If no AI analyzer available, use deterministic analysis
        printer.print("ℹ️ AI analyzer not available, using deterministic analysis")
        has_error, is_timeout_error, has_success = self.analyze_logs(logs, workflow_type)
        return self.determine_execution_status(has_error, has_success)
    
    def determine_execution_status(self, has_error: bool, has_success: bool) -> str:
        """Determine the overall execution status based on error and success indicators.
        
        Args:
            has_error: Whether any error was detected
            has_success: Whether any success indicator was found
            
        Returns:
            Status string: 'error', 'success', or 'uncertain'
        """
        # Critical errors always mean failure, regardless of success indicators
        if has_error:
            return 'error'
        
        # No errors and success indicators mean success
        if has_success and not has_error:
            return 'success'
        
        # No clear indicators either way
        return 'uncertain'
    
    @staticmethod
    def display_logs(logs: str, has_error: bool, max_chars: int = 2000):
        """Display logs with appropriate truncation.
        
        Args:
            logs: The logs to display
            has_error: Whether an error was detected
            max_chars: Maximum characters to display
        """
        printer.print("\n--- Execution Logs ---")
        printer.print("=" * 50)
        
        # Always show the last N characters (more relevant for debugging)
        if len(logs) > max_chars:
            printer.print(f"... (showing last {max_chars} characters)")
            printer.print(logs[-max_chars:])
        else:
            printer.print(logs)
            
        printer.print("=" * 50)
    
    @staticmethod
    def get_error_handling_choice(is_timeout_error: bool) -> str:
        """Get user's choice for error handling.
        
        Args:
            is_timeout_error: Whether this is a timeout error
            
        Returns:
            User's choice as a string
        """
        from workflow_tools.core.questionary_utils import select
        
        printer.print("⚠️ Errors detected in the logs!")
        
        if is_timeout_error:
            choices = [
                {'name': '🔄 Retry running the code (recommended for timeout errors)', 'value': 'retry'},
                {'name': '🤖 Let AI analyze the error and propose a fix', 'value': '1'},
                {'name': '✏️ Provide manual feedback yourself', 'value': '2'},
                {'name': '✅ Continue anyway (error not serious or fixed in IDE)', 'value': '3'},
                {'name': '❌ Abort the workflow', 'value': '4'},
                {'name': '← Go back to previous phase', 'value': 'back'}
            ]
            choice = select("Choose debugging approach:", choices, show_border=True)
            
            if choice == 'back':
                raise NavigationBackRequest("User requested to go back")
            return choice
        else:
            choices = [
                {'name': '🤖 Let AI analyze the error and propose a fix', 'value': '1'},
                {'name': '✏️ Provide manual feedback yourself', 'value': '2'},
                {'name': '✅ Continue anyway (error not serious or fixed in IDE)', 'value': '3'},
                {'name': '❌ Abort the workflow', 'value': '4'},
                {'name': '← Go back to previous phase', 'value': 'back'}
            ]
            choice = select("Choose debugging approach:", choices, show_border=True)
            
            if choice == 'back':
                raise NavigationBackRequest("User requested to go back")
            return choice