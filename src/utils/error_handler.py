"""Error handling utilities."""

import logging
import traceback
from typing import Optional, Callable, Any
from functools import wraps

from .exceptions import (
    QAAgentError,
    ModelAPIError,
    ModelTimeoutError,
    ParsingError,
    AgentExecutionError,
)

logger = logging.getLogger(__name__)


def handle_errors(
    error_message: str = "An error occurred",
    reraise: bool = True,
    default_return: Any = None,
):
    """
    Decorator for error handling.

    Args:
        error_message: Custom error message prefix
        reraise: Whether to reraise the exception after logging
        default_return: Value to return if error occurs and not reraising

    Usage:
        @handle_errors("Failed to parse requirement")
        def parse_requirement(content):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except QAAgentError as e:
                logger.error(f"{error_message}: {e}")
                if reraise:
                    raise
                return default_return
            except Exception as e:
                logger.error(f"{error_message}: Unexpected error: {e}")
                logger.debug(traceback.format_exc())
                if reraise:
                    raise QAAgentError(f"{error_message}: {str(e)}") from e
                return default_return
        return wrapper
    return decorator


def safe_model_call(
    func: Callable,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    timeout: int = 60,
) -> Any:
    """
    Safely call model API with retries and timeout handling.

    Args:
        func: Function to call
        max_retries: Maximum number of retries
        retry_delay: Delay between retries (seconds)
        timeout: Timeout for the call (seconds)

    Returns:
        Function result

    Raises:
        ModelAPIError: If all retries fail
        ModelTimeoutError: If timeout occurs
    """
    import time

    last_error = None

    for attempt in range(max_retries):
        try:
            return func()
        except ModelTimeoutError:
            logger.warning(f"Model call timeout (attempt {attempt + 1}/{max_retries})")
            last_error = ModelTimeoutError("Model API call timed out")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
        except ModelAPIError as e:
            logger.warning(f"Model API error (attempt {attempt + 1}/{max_retries}): {e}")
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
        except Exception as e:
            logger.error(f"Unexpected error in model call: {e}")
            last_error = ModelAPIError(f"Unexpected error: {str(e)}")
            break

    raise last_error or ModelAPIError("Model call failed after retries")


def validate_json_response(response: str, required_fields: list = None) -> dict:
    """
    Validate and parse JSON response from LLM.

    Args:
        response: Response string from LLM
        required_fields: List of required field names

    Returns:
        Parsed JSON dict

    Raises:
        ParsingError: If JSON is invalid or missing required fields
    """
    import json

    # Try to extract JSON from markdown code blocks
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        json_str = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        json_str = response[start:end].strip()
    else:
        json_str = response.strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ParsingError(
            f"Failed to parse JSON response: {e}",
            content=json_str
        )

    # Validate required fields
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ParsingError(
                f"Missing required fields: {', '.join(missing_fields)}",
                content=json_str
            )

    return data


def log_agent_error(
    agent_name: str,
    stage: str,
    error: Exception,
    context: dict = None,
):
    """
    Log agent execution error with context.

    Args:
        agent_name: Name of the agent
        stage: Current execution stage
        error: The exception that occurred
        context: Additional context information
    """
    logger.error(f"Agent '{agent_name}' failed at stage '{stage}': {error}")

    if context:
        logger.debug(f"Context: {context}")

    logger.debug(traceback.format_exc())

    # Create structured error for tracking
    error_info = {
        "agent": agent_name,
        "stage": stage,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {},
    }

    logger.info(f"Error summary: {error_info}")
