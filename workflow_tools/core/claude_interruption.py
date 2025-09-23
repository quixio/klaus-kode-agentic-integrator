"""Claude Code SDK interruption mechanism for interactive guidance.

This module provides the ability to interrupt Claude Code during execution
and inject additional prompts while maintaining conversation context.
"""

import asyncio
import threading
import queue
from typing import Any, Optional, AsyncIterator, Dict, List
from collections.abc import AsyncIterable
import keyboard
from datetime import datetime

from claude_code_sdk import Message, UserMessage, AssistantMessage, TextBlock
from claude_code_sdk._internal.transport import Transport
from workflow_tools.common import printer
from workflow_tools.core.enhanced_input import get_enhanced_input_async, enhanced_input


class InterruptionState:
    """Manages the state of interruptions and message flow."""

    def __init__(self):
        self.is_interrupted = False
        self.interruption_queue = queue.Queue()
        self.conversation_history: List[Message] = []
        self.partial_response: List[str] = []
        self.monitoring_active = False
        self.interrupt_key = 'ctrl+i'  # Default interrupt key
        self.last_interrupt_time = None
        self.session_id = None

    def reset(self):
        """Reset the interruption state for a new session."""
        self.is_interrupted = False
        self.conversation_history.clear()
        self.partial_response.clear()
        while not self.interruption_queue.empty():
            try:
                self.interruption_queue.get_nowait()
            except queue.Empty:
                break


class ClaudeInterruptionHandler:
    """Handles keyboard monitoring and interruption logic."""

    def __init__(self, state: InterruptionState):
        self.state = state
        self.monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()

    def start_monitoring(self):
        """Start monitoring for keyboard interrupts in a background thread."""
        if self.state.monitoring_active:
            return

        self.state.monitoring_active = True
        self._stop_monitoring.clear()

        def monitor_keyboard():
            """Background thread function to monitor keyboard."""
            printer.print(f"🎹 Interrupt monitoring active (press {self.state.interrupt_key} to interrupt Claude)")

            def on_interrupt():
                """Handle interrupt key press."""
                if not self.state.is_interrupted:
                    self.state.is_interrupted = True
                    self.state.last_interrupt_time = datetime.now()
                    printer.print("\n\n🛑 Interrupting Claude... Please wait for current operation to complete.")
                    printer.print("   You'll be prompted to add guidance shortly.\n")

            # Register the hotkey
            keyboard.add_hotkey(self.state.interrupt_key, on_interrupt)

            # Keep thread alive until stop is signaled
            while not self._stop_monitoring.is_set():
                self._stop_monitoring.wait(0.1)

            # Cleanup
            try:
                keyboard.remove_hotkey(self.state.interrupt_key)
            except:
                pass

        self.monitor_thread = threading.Thread(target=monitor_keyboard, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring for keyboard interrupts."""
        if not self.state.monitoring_active:
            return

        self.state.monitoring_active = False
        self._stop_monitoring.set()

        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            self.monitor_thread = None

        printer.print("🎹 Interrupt monitoring stopped")

    async def handle_interruption(self) -> Optional[str]:
        """Handle an interruption and get user guidance.

        Returns:
            User's guidance message or None if no guidance provided
        """
        printer.print("\n" + "=" * 60)
        printer.print("🔄 CLAUDE INTERRUPTION HANDLER")
        printer.print("=" * 60)

        # Show current partial response if any
        if self.state.partial_response:
            printer.print("\n📝 Claude's response so far:")
            for line in self.state.partial_response[-5:]:  # Show last 5 lines
                printer.print(f"   {line[:80]}..." if len(line) > 80 else f"   {line}")

        # Get user guidance
        printer.print("\n💡 Add guidance for Claude to help with the current task.")
        printer.print("   (Press Enter with no text to let Claude continue)\n")

        guidance = await get_enhanced_input_async(
            prompt="Your guidance",
            default="",
            multiline=True,
            show_border=True
        )

        guidance = guidance.strip()

        if guidance:
            printer.print(f"\n✅ Guidance added: '{guidance[:50]}...' " if len(guidance) > 50 else f"\n✅ Guidance added: '{guidance}'")
            printer.print("   Claude will incorporate this and continue.\n")
            self.state.interruption_queue.put(guidance)
        else:
            printer.print("\n✅ No guidance added. Claude will continue.")

        printer.print("=" * 60 + "\n")

        # Reset interruption flag
        self.state.is_interrupted = False

        return guidance if guidance else None


class InterruptibleTransport(Transport):
    """Custom transport that supports interruption during Claude Code execution.

    This wraps another transport and adds interruption capabilities.
    """

    def __init__(self, base_transport: Optional[Transport] = None):
        """Initialize the interruptible transport.

        Args:
            base_transport: The underlying transport to wrap. If None, will use default.
        """
        super().__init__()
        self.base_transport = base_transport
        self.state = InterruptionState()
        self.handler = ClaudeInterruptionHandler(self.state)
        self._message_buffer = []
        self._is_processing = False

    async def connect(
        self,
        prompt: str | AsyncIterable[dict[str, Any]],
        options: Any
    ) -> None:
        """Connect to the Claude service with interruption support.

        Args:
            prompt: Initial prompt or stream of prompts
            options: Claude Code options
        """
        # Start keyboard monitoring
        self.handler.start_monitoring()

        # If we have a base transport, use it
        if self.base_transport:
            await self.base_transport.connect(prompt, options)
        else:
            # Create default transport if none provided
            from claude_code_sdk._internal.transport import create_default_transport
            self.base_transport = create_default_transport()
            await self.base_transport.connect(prompt, options)

        self._is_processing = True

    async def send(self, message: dict[str, Any]) -> None:
        """Send a message through the transport.

        Args:
            message: Message to send
        """
        if self.base_transport:
            await self.base_transport.send(message)

    async def receive(self) -> AsyncIterator[Message]:
        """Receive messages with interruption support.

        Yields:
            Messages from Claude, with interruption handling
        """
        if not self.base_transport:
            return

        try:
            async for message in self.base_transport.receive():
                # Store message in conversation history
                self.state.conversation_history.append(message)

                # Track partial responses
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            self.state.partial_response.append(block.text)

                # Check for interruption
                if self.state.is_interrupted and not self._is_processing:
                    # Handle the interruption
                    guidance = await self.handler.handle_interruption()

                    if guidance:
                        # Create a user message with the guidance
                        # This will be injected into the conversation
                        user_msg = UserMessage(
                            role="user",
                            content=[TextBlock(text=f"Additional guidance: {guidance}")]
                        )
                        yield user_msg

                        # Send the guidance through the base transport
                        await self.send({
                            "type": "user",
                            "message": {"role": "user", "content": guidance}
                        })

                # Yield the original message
                yield message

        except Exception as e:
            printer.print(f"❌ Error in interruptible transport: {e}")
            raise
        finally:
            self._is_processing = False

    async def close(self) -> None:
        """Close the transport and cleanup."""
        # Stop monitoring
        self.handler.stop_monitoring()

        # Reset state
        self.state.reset()

        # Close base transport
        if self.base_transport:
            await self.base_transport.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Ensure monitoring is stopped
        self.handler.stop_monitoring()

        # Clean up base transport if needed
        if self.base_transport and hasattr(self.base_transport, '__exit__'):
            self.base_transport.__exit__(exc_type, exc_val, exc_tb)


class InterruptibleClaudeQuery:
    """Wrapper for making Claude queries interruptible."""

    @staticmethod
    async def query_with_interruption(
        prompt: str | AsyncIterable[dict[str, Any]],
        options: Any,
        transport: Optional[Transport] = None
    ) -> AsyncIterator[Message]:
        """Execute a Claude query with interruption support.

        Args:
            prompt: The prompt or prompt stream
            options: Claude Code options
            transport: Optional custom transport (will be wrapped with interruption support)

        Yields:
            Messages from Claude with interruption handling
        """
        from claude_code_sdk import query

        # Create interruptible transport
        interruptible = InterruptibleTransport(transport)

        try:
            # Use the interruptible transport with the query
            async for message in query(
                prompt=prompt,
                options=options,
                transport=interruptible
            ):
                yield message
        finally:
            # Ensure cleanup
            await interruptible.close()