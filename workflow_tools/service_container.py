"""Service container for dependency injection."""

from typing import Any, Callable, Dict, Optional, TypeVar, Type
from functools import wraps
import inspect


T = TypeVar('T')


class ServiceContainer:
    """Container for managing service dependencies."""
    
    def __init__(self):
        """Initialize the service container."""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._singleton_flags: Dict[str, bool] = {}
    
    def register(self, name: str, factory: Callable, singleton: bool = True) -> None:
        """Register a service factory.
        
        Args:
            name: Service name
            factory: Factory function that creates the service
            singleton: Whether to create only one instance (default: True)
        """
        self._factories[name] = factory
        self._singleton_flags[name] = singleton
        if not singleton:
            # Non-singletons don't get cached
            self._services.pop(name, None)
    
    def register_instance(self, name: str, instance: Any) -> None:
        """Register an existing instance as a service.
        
        Args:
            name: Service name
            instance: Service instance
        """
        self._singletons[name] = instance
        self._singleton_flags[name] = True
    
    def get(self, name: str) -> Any:
        """Get a service by name.
        
        Args:
            name: Service name
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not registered
        """
        # Check if we have a pre-registered instance
        if name in self._singletons:
            return self._singletons[name]
        
        # Check if this is a singleton that's already created
        if name in self._services and self._singleton_flags.get(name, True):
            return self._services[name]
        
        # Create the service
        if name not in self._factories:
            raise KeyError(f"Service '{name}' is not registered")
        
        factory = self._factories[name]
        
        # Check if factory expects the container as argument
        sig = inspect.signature(factory)
        if len(sig.parameters) > 0:
            # Factory expects container
            service = factory(self)
        else:
            # Factory doesn't need container
            service = factory()
        
        # Cache if singleton
        if self._singleton_flags.get(name, True):
            self._services[name] = service
        
        return service
    
    def get_typed(self, name: str, service_type: Type[T]) -> T:
        """Get a typed service by name.
        
        Args:
            name: Service name
            service_type: Expected type of the service
            
        Returns:
            Service instance of the specified type
        """
        service = self.get(name)
        if not isinstance(service, service_type):
            raise TypeError(f"Service '{name}' is not of type {service_type.__name__}")
        return service
    
    def has(self, name: str) -> bool:
        """Check if a service is registered.
        
        Args:
            name: Service name
            
        Returns:
            True if service is registered
        """
        return name in self._factories or name in self._singletons
    
    def reset(self) -> None:
        """Reset all cached services."""
        self._services.clear()
        self._singletons.clear()
    
    def create_child(self) -> 'ServiceContainer':
        """Create a child container that inherits from this one.
        
        Returns:
            New ServiceContainer with access to parent's services
        """
        child = ChildServiceContainer(self)
        return child


class ChildServiceContainer(ServiceContainer):
    """Child container that can access parent's services."""
    
    def __init__(self, parent: ServiceContainer):
        """Initialize child container.
        
        Args:
            parent: Parent service container
        """
        super().__init__()
        self._parent = parent
    
    def get(self, name: str) -> Any:
        """Get service from this container or parent.
        
        Args:
            name: Service name
            
        Returns:
            Service instance
        """
        # Try to get from this container first
        if self.has(name):
            return super().get(name)
        
        # Fall back to parent
        return self._parent.get(name)
    
    def has(self, name: str) -> bool:
        """Check if service exists in this container or parent.
        
        Args:
            name: Service name
            
        Returns:
            True if service is registered
        """
        return super().has(name) or self._parent.has(name)


def inject(**dependencies):
    """Decorator for automatic dependency injection.
    
    Usage:
        @inject(db='database', logger='logger')
        def my_function(db, logger):
            # db and logger are automatically injected
            pass
    
    Args:
        **dependencies: Mapping of parameter names to service names
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the container from the first argument if it's a method
            if args and hasattr(args[0], 'container'):
                container = args[0].container
            elif 'container' in kwargs:
                container = kwargs['container']
            else:
                raise ValueError("No service container available for injection")
            
            # Inject dependencies
            for param_name, service_name in dependencies.items():
                if param_name not in kwargs:
                    kwargs[param_name] = container.get(service_name)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Global service container instance (optional, for convenience)
_global_container: Optional[ServiceContainer] = None


def get_global_container() -> ServiceContainer:
    """Get the global service container, creating it if necessary.
    
    Returns:
        Global ServiceContainer instance
    """
    global _global_container
    if _global_container is None:
        _global_container = ServiceContainer()
    return _global_container


def set_global_container(container: ServiceContainer) -> None:
    """Set the global service container.
    
    Args:
        container: ServiceContainer to use globally
    """
    global _global_container
    _global_container = container