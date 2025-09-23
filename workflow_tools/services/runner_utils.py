"""Utility functions for running agents with retry logic and error handling.

This module provides centralized retry logic for Anthropic API calls,
handling overloaded errors gracefully with exponential backoff.
"""

import asyncio
from typing import Any, Optional
from agents import Runner, RunResult
from workflow_tools.common import printer


async def run_agent_with_retry(
    starting_agent: Any,
    input: str,
    context: Any,
    max_retries: int = 3,
    base_delay: float = 5.0,
    operation_name: str = "AI operation"
) -> Optional[RunResult]:
    """
    Run an agent with automatic retry logic for overloaded errors.

    This function handles Anthropic API overloaded errors gracefully by
    implementing exponential backoff retry logic. It's designed to be used
    throughout the application wherever we call Runner.run().

    Args:
        starting_agent: The agent to run
        input: The input prompt/text for the agent
        context: The context object to pass to the agent
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 5)
        operation_name: Name of the operation for logging (default: "AI operation")

    Returns:
        RunResult on success, None if all retries are exhausted

    Raises:
        Exception: For non-overloaded errors
    """
    for attempt in range(max_retries):
        try:
            # Attempt to run the agent
            result = await Runner.run(
                starting_agent=starting_agent,
                input=input,
                context=context
            )

            # Success - return the result
            return result

        except Exception as e:
            error_str = str(e)

            # Check if it's an overloaded error from Anthropic
            if any(indicator in error_str for indicator in [
                "overloaded_error",
                "Overloaded",
                "rate_limit_error",
                "RateLimitError",
                "429",  # HTTP 429 Too Many Requests
                "503",  # HTTP 503 Service Unavailable
            ]):
                if attempt < max_retries - 1:
                    # Calculate delay with exponential backoff
                    delay = base_delay * (2 ** attempt)

                    # Add some jitter to avoid thundering herd
                    import random
                    jitter = random.uniform(0, delay * 0.1)
                    total_delay = delay + jitter

                    printer.print(f"\n⚠️ Anthropic API is busy. Waiting {total_delay:.1f} seconds before retry {attempt + 1}/{max_retries}...")
                    printer.print(f"   (This happens when many users are using Claude at once)")
                    printer.print(f"   Operation: {operation_name}")

                    await asyncio.sleep(total_delay)
                    continue
                else:
                    # Max retries exhausted
                    printer.print(f"\n❌ Anthropic API is still overloaded after {max_retries} attempts.")
                    printer.print(f"   Operation failed: {operation_name}")
                    printer.print("   Please try again in a few minutes when the service is less busy.")
                    printer.print("")
                    printer.print("   💡 Tip: You can also:")
                    printer.print("      - Wait a few minutes and retry")
                    printer.print("      - Try during off-peak hours")
                    printer.print("      - Check https://status.anthropic.com for service status")

                    return None
            else:
                # Not an overloaded/rate limit error - raise it normally
                raise

    # This shouldn't be reached, but just in case
    return None


async def run_agent_with_fallback(
    starting_agent: Any,
    input: str,
    context: Any,
    fallback_agent: Optional[Any] = None,
    max_retries: int = 3,
    base_delay: float = 5.0,
    operation_name: str = "AI operation"
) -> Optional[RunResult]:
    """
    Run an agent with retry logic and optional fallback to a simpler model.

    This extends run_agent_with_retry by allowing a fallback to a simpler,
    less resource-intensive model if the primary model is consistently overloaded.

    Args:
        starting_agent: The primary agent to run
        input: The input prompt/text for the agent
        context: The context object to pass to the agent
        fallback_agent: Optional fallback agent to use if primary fails
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 5)
        operation_name: Name of the operation for logging (default: "AI operation")

    Returns:
        RunResult on success, None if all attempts fail
    """
    # Try primary agent first
    result = await run_agent_with_retry(
        starting_agent=starting_agent,
        input=input,
        context=context,
        max_retries=max_retries,
        base_delay=base_delay,
        operation_name=operation_name
    )

    if result is not None:
        return result

    # If primary failed and we have a fallback, try it
    if fallback_agent is not None:
        printer.print(f"\n🔄 Attempting with fallback model for {operation_name}...")

        result = await run_agent_with_retry(
            starting_agent=fallback_agent,
            input=input,
            context=context,
            max_retries=2,  # Fewer retries for fallback
            base_delay=3.0,  # Shorter delay for fallback
            operation_name=f"{operation_name} (fallback)"
        )

        if result is not None:
            printer.print("✅ Fallback model succeeded")
            return result

    return None