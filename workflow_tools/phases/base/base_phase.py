"""Base phase class for all workflow phases."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
import time
import traceback

from workflow_tools.common import printer
from workflow_tools.contexts import WorkflowContext
from workflow_tools.core.config_loader import config
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.core.questionary_utils import select_yes_no
from workflow_tools.core.enhanced_input import get_enhanced_input


@dataclass
class PhaseResult:
    """Result of a phase execution."""
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    duration: float = 0.0


class BasePhase(ABC):
    """Abstract base class for all workflow phases."""
    
    # Phase metadata - should be overridden by subclasses
    phase_name: str = "base_phase"
    phase_description: str = "Base phase description"
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        """Initialize the phase.
        
        Args:
            context: Workflow context object
            debug_mode: Whether to enable debug mode
        """
        self.context = context
        self.debug_mode = debug_mode or config.is_feature_enabled("enable_debug_mode")
        self.phase_config = config.get_phase_config(self.phase_name)
        self._start_time: Optional[float] = None
    
    @abstractmethod
    async def execute(self) -> PhaseResult:
        """Execute the main phase logic.
        
        This method must be implemented by all subclasses.
        
        Returns:
            PhaseResult object containing execution results
        """
        pass
    
    async def run(self) -> bool:
        """Run the phase with error handling and context saving.
        
        Returns:
            True if phase succeeded, False otherwise
        """
        self._start_time = time.time()
        
        try:
            # Pre-execution hook
            await self.pre_execute()
            
            # Clear screen before starting the phase
            from workflow_tools.common import clear_screen
            clear_screen()
            
            # Execute main phase logic with beautiful header
            printer.print_phase_header(self.phase_description)
            
            result = await self.execute()
            
            # Post-execution hook
            await self.post_execute(result)
            
            # Handle result
            if result.success:
                self._log_success(result)
                return True
            else:
                self._log_failure(result)
                return False
                
        except NavigationBackRequest:
            # Re-raise navigation requests to be handled by workflow orchestrator
            raise
        except Exception as e:
            # Handle unexpected errors
            result = PhaseResult(
                success=False,
                message=f"Unexpected error in {self.phase_name}: {str(e)}",
                error=e,
                duration=self._get_duration()
            )
            self._log_error(result)
            if self.debug_mode:
                traceback.print_exc()
            return False
    
    async def pre_execute(self) -> None:
        """Hook called before phase execution.
        
        Can be overridden by subclasses for setup tasks.
        """
        if self.debug_mode:
            printer.print_debug(f"Pre-execution: {self.phase_name}")
    
    async def post_execute(self, result: PhaseResult) -> None:
        """Hook called after phase execution.
        
        Can be overridden by subclasses for cleanup tasks.
        
        Args:
            result: The result of the phase execution
        """
        if self.debug_mode:
            printer.print_debug(f"Post-execution: {self.phase_name}")
            printer.print_debug(f"Duration: {result.duration:.2f}s")
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if the phase should be retried.
        
        Args:
            attempt: Current attempt number (1-based)
            error: The exception that occurred
        
        Returns:
            True if should retry, False otherwise
        """
        retry_config = self.phase_config.get("retry", {})
        max_attempts = retry_config.get("max_attempts", 3)
        
        # Check if we've exceeded max attempts
        if attempt >= max_attempts:
            return False
        
        # Check if error is retryable
        retryable_errors = [
            ConnectionError,
            TimeoutError,
            IOError,
        ]
        
        return any(isinstance(error, err_type) for err_type in retryable_errors)
    
    async def retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """Execute a function with exponential backoff retry.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        
        Returns:
            Result of the function execution
        
        Raises:
            Last exception if all retries fail
        """
        retry_config = self.phase_config.get("retry", {})
        max_attempts = retry_config.get("max_attempts", 3)
        initial_delay = retry_config.get("initial_delay", 2)
        max_delay = retry_config.get("max_delay", 30)
        exponential_base = retry_config.get("exponential_base", 2)
        
        last_exception = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(attempt, e):
                    raise
                
                if attempt < max_attempts:
                    delay = min(initial_delay * (exponential_base ** (attempt - 1)), max_delay)
                    printer.print(f"Attempt {attempt} failed: {str(e)}")
                    printer.print(f"Retrying in {delay} seconds.")
                    time.sleep(delay)
        
        raise last_exception
    
    def get_user_input(self, prompt: str, default: Optional[str] = None, 
                       required: bool = True, validator=None) -> Optional[str]:
        """Get input from the user with validation.
        
        Args:
            prompt: The prompt to display
            default: Default value if user presses enter
            required: Whether the input is required
            validator: Optional function to validate input
        
        Returns:
            User input or None if not required and no input given
        """
        while True:
            if default:
                full_prompt = f"{prompt} [{default}]: "
            else:
                full_prompt = f"{prompt}: "
            
            user_input = get_enhanced_input(full_prompt).strip()
            
            # Use default if no input
            if not user_input and default:
                user_input = default
            
            # Check if required
            if required and not user_input:
                printer.print("This field is required. Please provide a value.")
                continue
            
            # Validate input if validator provided
            if validator and user_input:
                try:
                    if not validator(user_input):
                        printer.print("Invalid input. Please try again.")
                        continue
                except Exception as e:
                    printer.print(f"Validation error: {str(e)}")
                    continue
            
            return user_input if user_input else None
    
    def get_user_confirmation(self, message: str, default: bool = True) -> bool:
        """Get yes/no confirmation from the user.
        
        Args:
            message: The confirmation message
            default: Default value if user presses enter
        
        Returns:
            True for yes, False for no
        """
        return select_yes_no(message, default=default)
    
    def _get_duration(self) -> float:
        """Get the duration since phase started.
        
        Returns:
            Duration in seconds
        """
        if self._start_time:
            return time.time() - self._start_time
        return 0.0
    
    def _log_success(self, result: PhaseResult) -> None:
        """Log successful phase completion.
        
        Args:
            result: The phase result
        """
        result.duration = self._get_duration()
        printer.print(f"\n✅ {self.phase_description} completed successfully")
        if result.message:
            printer.print(f"   {result.message}")
        printer.print(f"   Duration: {result.duration:.2f}s\n")
    
    def _log_failure(self, result: PhaseResult) -> None:
        """Log phase failure.
        
        Args:
            result: The phase result
        """
        result.duration = self._get_duration()
        printer.print(f"\n❌ {self.phase_description} failed")
        if result.message:
            printer.print(f"   {result.message}")
        if result.error and self.debug_mode:
            printer.print(f"   Error: {str(result.error)}")
        printer.print(f"   Duration: {result.duration:.2f}s\n")
    
    def _log_error(self, result: PhaseResult) -> None:
        """Log unexpected error.
        
        Args:
            result: The phase result
        """
        result.duration = self._get_duration()
        printer.print(f"\n⚠️ Unexpected error in {self.phase_description}")
        printer.print(f"   {result.message}")
        if self.debug_mode and result.error:
            printer.print(f"   Error details: {str(result.error)}")
        printer.print(f"   Duration: {result.duration:.2f}s\n")