"""Custom exception hierarchy for workflow tools."""


class WorkflowException(Exception):
    """Base exception for all workflow-related errors."""
    
    def __init__(self, message: str, phase: str = None, details: dict = None):
        """Initialize workflow exception.
        
        Args:
            message: Error message
            phase: Phase where error occurred
            details: Additional error details
        """
        super().__init__(message)
        self.phase = phase
        self.details = details or {}


class ConfigurationError(WorkflowException):
    """Raised when there's a configuration issue."""
    pass


class ValidationError(WorkflowException):
    """Raised when validation fails."""
    pass


class PhaseExecutionError(WorkflowException):
    """Raised when a phase fails to execute."""
    
    def __init__(self, message: str, phase: str, retry_possible: bool = False, **kwargs):
        """Initialize phase execution error.
        
        Args:
            message: Error message
            phase: Phase that failed
            retry_possible: Whether retry is possible
            **kwargs: Additional details
        """
        super().__init__(message, phase, kwargs)
        self.retry_possible = retry_possible


class CodeGenerationError(WorkflowException):
    """Raised when code generation fails."""
    pass


class DependencyError(WorkflowException):
    """Raised when dependency resolution fails."""
    
    def __init__(self, message: str, missing_packages: list = None, **kwargs):
        """Initialize dependency error.
        
        Args:
            message: Error message
            missing_packages: List of missing packages
            **kwargs: Additional details
        """
        super().__init__(message, details=kwargs)
        self.missing_packages = missing_packages or []


class APIError(WorkflowException):
    """Raised when API calls fail."""
    
    def __init__(self, message: str, status_code: int = None, 
                 api_endpoint: str = None, **kwargs):
        """Initialize API error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            api_endpoint: API endpoint that failed
            **kwargs: Additional details
        """
        super().__init__(message, details=kwargs)
        self.status_code = status_code
        self.api_endpoint = api_endpoint


class QuixAPIError(APIError):
    """Raised when Quix API calls fail."""
    pass


class AIModelError(APIError):
    """Raised when AI model calls fail."""
    
    def __init__(self, message: str, model: str = None, 
                 provider: str = None, **kwargs):
        """Initialize AI model error.
        
        Args:
            message: Error message
            model: Model that failed
            provider: Model provider
            **kwargs: Additional details
        """
        super().__init__(message, **kwargs)
        self.model = model
        self.provider = provider


class SandboxError(WorkflowException):
    """Raised when sandbox testing fails."""
    
    def __init__(self, message: str, error_logs: str = None, 
                 error_type: str = None, **kwargs):
        """Initialize sandbox error.
        
        Args:
            message: Error message
            error_logs: Error logs from sandbox
            error_type: Type of error
            **kwargs: Additional details
        """
        super().__init__(message, phase="sandbox", details=kwargs)
        self.error_logs = error_logs
        self.error_type = error_type


class DeploymentError(WorkflowException):
    """Raised when deployment fails."""
    
    def __init__(self, message: str, deployment_id: str = None,
                 deployment_status: str = None, **kwargs):
        """Initialize deployment error.
        
        Args:
            message: Error message
            deployment_id: Deployment ID
            deployment_status: Current deployment status
            **kwargs: Additional details
        """
        super().__init__(message, phase="deployment", details=kwargs)
        self.deployment_id = deployment_id
        self.deployment_status = deployment_status


class TimeoutError(WorkflowException):
    """Raised when an operation times out."""
    
    def __init__(self, message: str, timeout_seconds: int = None, **kwargs):
        """Initialize timeout error.
        
        Args:
            message: Error message
            timeout_seconds: Timeout duration
            **kwargs: Additional details
        """
        super().__init__(message, details=kwargs)
        self.timeout_seconds = timeout_seconds


class UserCancellationError(WorkflowException):
    """Raised when user cancels the workflow."""
    pass

class NavigationBackRequest(WorkflowException):
    """Raised when user requests to go back to previous phase."""
    def __init__(self, message: str = "User requested to go back to previous phase"):
        super().__init__(message)


class FileOperationError(WorkflowException):
    """Raised when file operations fail."""
    
    def __init__(self, message: str, file_path: str = None, 
                 operation: str = None, **kwargs):
        """Initialize file operation error.
        
        Args:
            message: Error message
            file_path: File path involved
            operation: Operation that failed
            **kwargs: Additional details
        """
        super().__init__(message, details=kwargs)
        self.file_path = file_path
        self.operation = operation


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails."""
    
    def __init__(self, message: str, schema_errors: list = None, **kwargs):
        """Initialize schema validation error.
        
        Args:
            message: Error message
            schema_errors: List of schema validation errors
            **kwargs: Additional details
        """
        super().__init__(message, details=kwargs)
        self.schema_errors = schema_errors or []


class TemplateNotFoundError(WorkflowException):
    """Raised when a required template is not found."""
    
    def __init__(self, message: str, technology: str = None, 
                 available_templates: list = None, **kwargs):
        """Initialize template not found error.
        
        Args:
            message: Error message
            technology: Technology requested
            available_templates: List of available templates
            **kwargs: Additional details
        """
        super().__init__(message, details=kwargs)
        self.technology = technology
        self.available_templates = available_templates or []


class CredentialError(WorkflowException):
    """Raised when credential issues occur."""
    
    def __init__(self, message: str, missing_credentials: list = None, **kwargs):
        """Initialize credential error.
        
        Args:
            message: Error message
            missing_credentials: List of missing credential names
            **kwargs: Additional details
        """
        super().__init__(message, details=kwargs)
        self.missing_credentials = missing_credentials or []


class RetryableError(WorkflowException):
    """Base class for errors that can be retried."""
    
    def __init__(self, message: str, max_retries: int = 3, 
                 retry_delay: float = 2.0, **kwargs):
        """Initialize retryable error.
        
        Args:
            message: Error message
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries
            **kwargs: Additional details
        """
        super().__init__(message, details=kwargs)
        self.max_retries = max_retries
        self.retry_delay = retry_delay


class NetworkError(RetryableError):
    """Raised when network operations fail."""
    pass


class TemporaryError(RetryableError):
    """Raised for temporary failures that may succeed on retry."""
    pass