"""Custom exceptions for VITA QA Agent."""


class QAAgentError(Exception):
    """Base exception for QA Agent."""
    pass


class ModelClientError(QAAgentError):
    """Error related to model client operations."""
    pass


class ModelAPIError(ModelClientError):
    """Error from model API calls."""

    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class ModelTimeoutError(ModelClientError):
    """Model API timeout error."""
    pass


class ParsingError(QAAgentError):
    """Error during requirement or response parsing."""

    def __init__(self, message: str, content: str = None):
        super().__init__(message)
        self.content = content


class ValidationError(QAAgentError):
    """Data validation error."""
    pass


class ConfigurationError(QAAgentError):
    """Configuration error."""
    pass


class FileOperationError(QAAgentError):
    """File operation error."""

    def __init__(self, message: str, file_path: str = None):
        super().__init__(message)
        self.file_path = file_path


class AgentExecutionError(QAAgentError):
    """Error during agent execution."""

    def __init__(self, message: str, agent_name: str = None, stage: str = None):
        super().__init__(message)
        self.agent_name = agent_name
        self.stage = stage
