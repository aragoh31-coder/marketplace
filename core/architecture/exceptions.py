"""
Custom Exceptions for the Modular System
Provide specific error types for different failure scenarios.
"""


class ModuleError(Exception):
    """Base exception for module-related errors."""

    def __init__(self, message: str, module_name: str = None, error_code: str = None):
        self.message = message
        self.module_name = module_name
        self.error_code = error_code

        if module_name:
            message = f"[{module_name}] {message}"

        super().__init__(message)


class ModuleNotFoundError(ModuleError):
    """Raised when a required module is not found."""

    def __init__(self, module_name: str, required_by: str = None):
        message = f"Module '{module_name}' not found"
        if required_by:
            message += f" (required by '{required_by}')"

        super().__init__(message, module_name, "MODULE_NOT_FOUND")


class ModuleDependencyError(ModuleError):
    """Raised when module dependencies are not satisfied."""

    def __init__(self, module_name: str, missing_dependencies: list, circular_dependencies: list = None):
        message = f"Module '{module_name}' has unsatisfied dependencies: {missing_dependencies}"
        if circular_dependencies:
            message += f" and circular dependencies: {circular_dependencies}"

        super().__init__(message, module_name, "DEPENDENCY_ERROR")


class ModuleInitializationError(ModuleError):
    """Raised when a module fails to initialize."""

    def __init__(self, module_name: str, reason: str = None):
        message = f"Module '{module_name}' failed to initialize"
        if reason:
            message += f": {reason}"

        super().__init__(message, module_name, "INITIALIZATION_ERROR")


class ModuleConfigurationError(ModuleError):
    """Raised when module configuration is invalid."""

    def __init__(self, module_name: str, config_key: str = None, reason: str = None):
        message = f"Module '{module_name}' configuration error"
        if config_key:
            message += f" for '{config_key}'"
        if reason:
            message += f": {reason}"

        super().__init__(message, module_name, "CONFIGURATION_ERROR")


class ModuleConflictError(ModuleError):
    """Raised when modules have conflicts."""

    def __init__(self, module_name: str, conflicting_module: str, reason: str = None):
        message = f"Module '{module_name}' conflicts with '{conflicting_module}'"
        if reason:
            message += f": {reason}"

        super().__init__(message, module_name, "CONFLICT_ERROR")


class ModuleVersionError(ModuleError):
    """Raised when module version requirements are not met."""

    def __init__(self, module_name: str, required_version: str, actual_version: str):
        message = f"Module '{module_name}' requires version {required_version}, but {actual_version} is installed"

        super().__init__(message, module_name, "VERSION_ERROR")


class ServiceError(Exception):
    """Base exception for service-related errors."""

    def __init__(self, message: str, service_name: str = None, error_code: str = None):
        self.message = message
        self.service_name = service_name
        self.error_code = error_code

        if service_name:
            message = f"[{service_name}] {message}"

        super().__init__(message)


class ServiceNotFoundError(ServiceError):
    """Raised when a required service is not found."""

    def __init__(self, service_name: str, required_by: str = None):
        message = f"Service '{service_name}' not found"
        if required_by:
            message += f" (required by '{required_by}')"

        super().__init__(message, service_name, "SERVICE_NOT_FOUND")


class ServiceUnavailableError(ServiceError):
    """Raised when a service is unavailable."""

    def __init__(self, service_name: str, reason: str = None):
        message = f"Service '{service_name}' is unavailable"
        if reason:
            message += f": {reason}"

        super().__init__(message, service_name, "SERVICE_UNAVAILABLE")


class ServiceHealthError(ServiceError):
    """Raised when a service health check fails."""

    def __init__(self, service_name: str, health_status: dict = None):
        message = f"Service '{service_name}' health check failed"
        if health_status:
            message += f": {health_status}"

        super().__init__(message, service_name, "HEALTH_CHECK_FAILED")


class ConfigurationError(Exception):
    """Base exception for configuration-related errors."""

    def __init__(self, message: str, setting_name: str = None):
        self.message = message
        self.setting_name = setting_name

        if setting_name:
            message = f"Configuration error for '{setting_name}': {message}"

        super().__init__(message)


class SettingNotFoundError(ConfigurationError):
    """Raised when a required Django setting is not found."""

    def __init__(self, setting_name: str, module_name: str = None):
        message = f"Required setting '{setting_name}' not found"
        if module_name:
            message += f" (required by module '{module_name}')"

        super().__init__(message, setting_name)


class SettingValidationError(ConfigurationError):
    """Raised when a Django setting value is invalid."""

    def __init__(self, setting_name: str, value: any, reason: str = None):
        message = f"Setting '{setting_name}' has invalid value: {value}"
        if reason:
            message += f" - {reason}"

        super().__init__(message, setting_name)


class DependencyError(Exception):
    """Base exception for dependency-related errors."""

    def __init__(self, message: str, dependency_name: str = None):
        self.message = message
        self.dependency_name = dependency_name

        if dependency_name:
            message = f"Dependency error for '{dependency_name}': {message}"

        super().__init__(message)


class CircularDependencyError(DependencyError):
    """Raised when circular dependencies are detected."""

    def __init__(self, dependency_chain: list):
        message = f"Circular dependency detected: {' -> '.join(dependency_chain)}"

        super().__init__(message)


class VersionConflictError(DependencyError):
    """Raised when version conflicts are detected."""

    def __init__(self, dependency_name: str, required_version: str, installed_version: str):
        message = (
            f"Version conflict for '{dependency_name}': required {required_version}, installed {installed_version}"
        )

        super().__init__(message, dependency_name)


class LifecycleError(Exception):
    """Base exception for lifecycle-related errors."""

    def __init__(self, message: str, hook_name: str = None, module_name: str = None):
        self.message = message
        self.hook_name = hook_name
        self.module_name = module_name

        if module_name and hook_name:
            message = f"[{module_name}] Lifecycle hook '{hook_name}' error: {message}"
        elif module_name:
            message = f"[{module_name}] Lifecycle error: {message}"
        elif hook_name:
            message = f"Lifecycle hook '{hook_name}' error: {message}"

        super().__init__(message)


class HookNotFoundError(LifecycleError):
    """Raised when a lifecycle hook is not found."""

    def __init__(self, hook_name: str, module_name: str = None):
        message = f"Lifecycle hook '{hook_name}' not found"

        super().__init__(message, hook_name, module_name)


class HookExecutionError(LifecycleError):
    """Raised when a lifecycle hook fails to execute."""

    def __init__(self, hook_name: str, module_name: str = None, reason: str = None):
        message = f"Lifecycle hook '{hook_name}' execution failed"
        if reason:
            message += f": {reason}"

        super().__init__(message, hook_name, module_name)
