class DjangoNativeMCPError(Exception):
    """Base exception for django-native-mcp."""


class RegistrationError(DjangoNativeMCPError):
    """Base exception for tool registration failures."""


class ToolAlreadyRegistered(RegistrationError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Tool '{name}' is already registered.")
        self.name = name


class InvalidToolError(RegistrationError):
    """Raised when a callable cannot be registered as an MCP tool."""


class AppNotConfigured(DjangoNativeMCPError):
    """Raised when no MCP application is configured."""


class AppFinalized(DjangoNativeMCPError):
    """Raised when code attempts to mutate a finalized MCP application."""
