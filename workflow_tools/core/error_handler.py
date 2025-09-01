"""Error handling service for workflow tools."""

import traceback
from typing import Optional, Callable, Any, Dict
from functools import wraps
import asyncio

from workflow_tools.exceptions import (
    WorkflowException, RetryableError, NetworkError,
    TemporaryError, UserCancellationError
)
from .logger_service import LoggerService, WorkflowPrinter


class ErrorHandler:
    """Centralized error handling service."""
    
    def __init__(self, printer: Optional[WorkflowPrinter] = None, debug_mode: bool = False):
        """Initialize error handler.
        
        Args:
            printer: Printer for output
            debug_mode: Enable debug mode
        """
        self.printer = printer or LoggerService.get_instance().get_printer()
        self.debug_mode = debug_mode
        self.error_registry: Dict[type, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default error handlers."""
        self.register_handler(NetworkError, self._handle_network_error)
        self.register_handler(TemporaryError, self._handle_temporary_error)
        self.register_handler(UserCancellationError, self._handle_user_cancellation)
    
    def register_handler(self, error_type: type, handler: Callable) -> None:
        """Register a custom error handler.
        
        Args:
            error_type: Type of error to handle
            handler: Handler function
        """
        self.error_registry[error_type] = handler
    
    def handle_error(self, error: Exception, context: str = None) -> bool:
        """Handle an error with appropriate strategy.
        
        Args:
            error: The error to handle
            context: Context where error occurred
            
        Returns:
            True if error was handled, False otherwise
        """
        # Log the error
        self._log_error(error, context)
        
        # Find appropriate handler
        handler = self._find_handler(error)
        
        if handler:
            try:
                return handler(error)
            except Exception as e:
                self.printer.print(f"Error in error handler: {str(e)}")
                return False
        
        # Default handling
        return self._default_error_handling(error)
    
    def _find_handler(self, error: Exception) -> Optional[Callable]:
        """Find appropriate handler for error type.
        
        Args:
            error: The error to handle
            
        Returns:
            Handler function or None
        """
        # Check exact type match
        error_type = type(error)
        if error_type in self.error_registry:
            return self.error_registry[error_type]
        
        # Check inheritance chain
        for registered_type, handler in self.error_registry.items():
            if isinstance(error, registered_type):
                return handler
        
        return None
    
    def _log_error(self, error: Exception, context: str = None) -> None:
        """Log error details.
        
        Args:
            error: The error to log
            context: Context where error occurred
        """
        error_msg = f"Error occurred"
        if context:
            error_msg += f" in {context}"
        error_msg += f": {str(error)}"
        
        self.printer.print(f"\n❌ {error_msg}")
        
        if self.debug_mode:
            self.printer.print("\nError details:")
            self.printer.print(traceback.format_exc())
            
            if isinstance(error, WorkflowException) and error.details:
                self.printer.print(f"Additional details: {error.details}")
    
    def _default_error_handling(self, error: Exception) -> bool:
        """Default error handling strategy.
        
        Args:
            error: The error to handle
            
        Returns:
            True if handled, False otherwise
        """
        if isinstance(error, RetryableError):
            self.printer.print(f"This error may be temporary. Consider retrying.")
            return True
        
        if isinstance(error, WorkflowException):
            # Provide specific guidance based on error type
            self._provide_error_guidance(error)
            return True
        
        return False
    
    def _provide_error_guidance(self, error: WorkflowException) -> None:
        """Provide user guidance for specific errors.
        
        Args:
            error: The workflow error
        """
        from .exceptions import (
            ConfigurationError, ValidationError, DependencyError,
            APIError, SandboxError, DeploymentError, CredentialError,
            TemplateNotFoundError
        )
        
        if isinstance(error, ConfigurationError):
            self.printer.print("\n💡 Configuration issue detected:")
            self.printer.print("  - Check your configuration files")
            self.printer.print("  - Ensure all required settings are present")
        
        elif isinstance(error, ValidationError):
            self.printer.print("\n💡 Validation failed:")
            self.printer.print("  - Review the input data")
            self.printer.print("  - Ensure it meets the required format")
        
        elif isinstance(error, DependencyError):
            self.printer.print("\n💡 Dependency issue:")
            if error.missing_packages:
                self.printer.print(f"  Missing packages: {', '.join(error.missing_packages)}")
            self.printer.print("  - Try installing missing packages")
        
        elif isinstance(error, APIError):
            self.printer.print("\n💡 API call failed:")
            if error.status_code:
                self.printer.print(f"  Status code: {error.status_code}")
            self.printer.print("  - Check your API credentials")
            self.printer.print("  - Verify network connectivity")
        
        elif isinstance(error, SandboxError):
            self.printer.print("\n💡 Sandbox testing failed:")
            if error.error_type:
                self.printer.print(f"  Error type: {error.error_type}")
            self.printer.print("  - Review the generated code")
            self.printer.print("  - Check for syntax errors")
        
        elif isinstance(error, DeploymentError):
            self.printer.print("\n💡 Deployment failed:")
            if error.deployment_status:
                self.printer.print(f"  Status: {error.deployment_status}")
            self.printer.print("  - Check deployment logs")
            self.printer.print("  - Verify resource availability")
        
        elif isinstance(error, CredentialError):
            self.printer.print("\n💡 Credential issue:")
            if error.missing_credentials:
                self.printer.print(f"  Missing: {', '.join(error.missing_credentials)}")
            self.printer.print("  - Provide required credentials")
        
        elif isinstance(error, TemplateNotFoundError):
            self.printer.print("\n💡 Template not found:")
            if error.technology:
                self.printer.print(f"  Technology: {error.technology}")
            if error.available_templates:
                self.printer.print(f"  Available: {', '.join(error.available_templates)}")
    
    def _handle_network_error(self, error: NetworkError) -> bool:
        """Handle network errors.
        
        Args:
            error: Network error
            
        Returns:
            True if handled
        """
        self.printer.print("\n🌐 Network error occurred:")
        self.printer.print("  - Check your internet connection")
        self.printer.print("  - Verify API endpoints are accessible")
        self.printer.print("  - Consider retrying in a few moments")
        return True
    
    def _handle_temporary_error(self, error: TemporaryError) -> bool:
        """Handle temporary errors.
        
        Args:
            error: Temporary error
            
        Returns:
            True if handled
        """
        self.printer.print("\n⏳ Temporary error occurred:")
        self.printer.print("  - This may be a transient issue")
        self.printer.print(f"  - Retry up to {error.max_retries} times")
        self.printer.print(f"  - Wait {error.retry_delay}s between attempts")
        return True
    
    def _handle_user_cancellation(self, error: UserCancellationError) -> bool:
        """Handle user cancellation.
        
        Args:
            error: User cancellation error
            
        Returns:
            True if handled
        """
        self.printer.print("\n👤 Workflow cancelled by user")
        self.printer.print("  - Progress has been saved where possible")
        self.printer.print("  - You can resume from the last checkpoint")
        return True


def with_error_handling(phase_name: str = None, retryable: bool = False):
    """Decorator for adding error handling to async functions.
    
    Args:
        phase_name: Name of the phase for context
        retryable: Whether errors should be retryable
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            error_handler = ErrorHandler(
                printer=getattr(self, 'printer', None),
                debug_mode=getattr(self, 'debug_mode', False)
            )
            
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                # Convert to appropriate exception type if needed
                if not isinstance(e, WorkflowException):
                    if retryable:
                        e = TemporaryError(str(e))
                    else:
                        e = WorkflowException(str(e), phase=phase_name)
                
                # Handle the error
                handled = error_handler.handle_error(e, phase_name)
                
                if not handled or not retryable:
                    raise
                
                # Retry logic for retryable errors
                if isinstance(e, RetryableError):
                    retry_count = 0
                    while retry_count < e.max_retries:
                        retry_count += 1
                        error_handler.printer.print(
                            f"\nRetrying ({retry_count}/{e.max_retries})."
                        )
                        await asyncio.sleep(e.retry_delay)
                        
                        try:
                            return await func(self, *args, **kwargs)
                        except Exception:
                            if retry_count >= e.max_retries:
                                raise
                
                raise
        
        return wrapper
    return decorator


class ErrorRecoveryStrategy:
    """Strategies for recovering from errors."""
    
    @staticmethod
    async def retry_with_exponential_backoff(
        func: Callable,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0
    ) -> Any:
        """Retry a function with exponential backoff.
        
        Args:
            func: Async function to retry
            max_attempts: Maximum retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            
        Returns:
            Result of successful function call
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        delay = initial_delay
        
        for attempt in range(max_attempts):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                
                if attempt < max_attempts - 1:
                    await asyncio.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
        
        raise last_exception
    
    @staticmethod
    async def fallback_to_default(
        func: Callable,
        default_value: Any
    ) -> Any:
        """Try a function and fallback to default on error.
        
        Args:
            func: Async function to try
            default_value: Default value on error
            
        Returns:
            Function result or default value
        """
        try:
            return await func()
        except Exception:
            return default_value
    
    @staticmethod
    async def circuit_breaker(
        func: Callable,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0
    ) -> Any:
        """Implement circuit breaker pattern.
        
        Args:
            func: Async function to protect
            failure_threshold: Failures before opening circuit
            recovery_timeout: Time before attempting recovery
            
        Returns:
            Function result
            
        Raises:
            Exception if circuit is open or function fails
        """
        # This is a simplified implementation
        # A full implementation would maintain state across calls
        try:
            return await func()
        except Exception as e:
            # In a real implementation, track failures
            raise e