"""Simplified Claude Code interruption mechanism.

This provides a simpler way to interrupt Claude Code by monitoring keyboard input
and allowing users to cancel and restart with additional guidance.
"""

import asyncio
import threading
from typing import Optional, Any
from datetime import datetime

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("Warning: keyboard library not available, interruption feature disabled")

from workflow_tools.common import printer
from workflow_tools.core.enhanced_input import get_enhanced_input_async


class SimpleInterruptionMonitor:
    """Simple keyboard monitor for Claude Code interruption."""

    def __init__(self):
        self.interrupted = False
        # Use F2 key by default (configurable via env var)
        # Good alternatives: f2, f3, f4, ctrl+g, ctrl+b
        import os
        self.interrupt_key = os.environ.get('KLAUS_INTERRUPT_KEY', 'f2').lower()
        self.monitoring = False
        self._monitor_thread = None
        self._stop_event = threading.Event()
        self.last_interrupt_time = None
        self.guidance_queue = []
        # Context preservation
        self.claude_responses = []
        self.claude_thoughts = []
        self.tool_uses = []

    def start(self):
        """Start monitoring for interruption key."""
        if not KEYBOARD_AVAILABLE:
            return

        if self.monitoring:
            return

        self.monitoring = True
        self.interrupted = False
        self._stop_event.clear()

        def monitor():
            """Background thread to monitor keyboard."""
            def on_interrupt():
                if not self.interrupted:
                    self.interrupted = True
                    self.last_interrupt_time = datetime.now()
                    printer.print("\n\n🛑 Interruption requested! Current operation will complete, then you can add guidance.")
                    printer.print("   (Note: Tool operations in progress will finish first)\n")

            keyboard.add_hotkey(self.interrupt_key, on_interrupt)

            # Keep thread alive
            while not self._stop_event.is_set():
                self._stop_event.wait(0.1)

            # Cleanup
            try:
                keyboard.remove_hotkey(self.interrupt_key)
            except:
                pass

        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()

        # Format key name for display
        key_display = self.interrupt_key.upper().replace('+', '-')
        printer.print(f"   💡 Press {key_display} to interrupt and add guidance")

    def stop(self):
        """Stop monitoring."""
        if not self.monitoring:
            return

        self.monitoring = False
        self._stop_event.set()

        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            self._monitor_thread = None

    def check_interrupted(self) -> bool:
        """Check if interruption was requested."""
        return self.interrupted

    def reset(self):
        """Reset interruption flag and context."""
        self.interrupted = False
        self.guidance_queue.clear()
        self.claude_responses.clear()
        self.claude_thoughts.clear()
        self.tool_uses.clear()

    def save_context(self, message_type: str, content: Any):
        """Save Claude's context for preservation."""
        if message_type == "response":
            self.claude_responses.append(content)
        elif message_type == "thought":
            self.claude_thoughts.append(content)
        elif message_type == "tool_use":
            self.tool_uses.append(content)

    def get_context_summary(self) -> str:
        """Generate a summary of Claude's work so far."""
        summary_parts = []

        if self.claude_thoughts:
            summary_parts.append("=== CLAUDE'S THINKING SO FAR ===")
            for thought in self.claude_thoughts[-3:]:  # Last 3 thoughts
                summary_parts.append(f"• {thought[:200]}..." if len(thought) > 200 else f"• {thought}")

        if self.claude_responses:
            summary_parts.append("\n=== CLAUDE'S ACTIONS SO FAR ===")
            for response in self.claude_responses[-5:]:  # Last 5 responses
                summary_parts.append(f"• {response[:100]}..." if len(response) > 100 else f"• {response}")

        if self.tool_uses:
            summary_parts.append("\n=== TOOLS USED SO FAR ===")
            for tool in self.tool_uses[-10:]:  # Last 10 tool uses
                summary_parts.append(f"• {tool}")

        return "\n".join(summary_parts) if summary_parts else ""

    async def get_guidance(self) -> Optional[str]:
        """Get guidance from user after interruption."""
        printer.print("\n" + "=" * 60)
        printer.print("🔄 INTERRUPTION HANDLER")
        printer.print("=" * 60)

        printer.print("\n💡 You interrupted Claude. What guidance would you like to add?")
        printer.print("   (Press Enter with no text to cancel interruption)\n")

        guidance = await get_enhanced_input_async(
            prompt="Additional guidance",
            default="",
            multiline=True,
            show_border=True
        )

        guidance = guidance.strip()

        if guidance:
            printer.print(f"\n✅ Guidance received. Claude will restart with your input.")
            self.guidance_queue.append(guidance)
        else:
            printer.print("\n✅ No guidance added. Continuing without changes.")

        printer.print("=" * 60 + "\n")

        # Reset flag
        self.interrupted = False

        return guidance if guidance else None


# Global monitor instance
interruption_monitor = SimpleInterruptionMonitor()


async def run_with_interruption_support(
    query_func,
    initial_prompt: str,
    options: Any,
    operation_name: str = "Claude Code operation"
) -> tuple[Any, bool]:
    """Run a Claude query with interruption support and context preservation.

    This wrapper monitors for interruption and allows restarting with additional
    guidance while preserving Claude's previous work and thoughts.

    Args:
        query_func: The async function to call (e.g., _query_with_balance_retry)
        initial_prompt: The initial prompt
        options: Claude Code options
        operation_name: Name of the operation for logging

    Returns:
        Tuple of (result, was_interrupted)
    """
    from claude_code_sdk import AssistantMessage, TextBlock, ThinkingBlock, ToolUseBlock

    monitor = interruption_monitor
    monitor.reset()
    monitor.start()

    accumulated_guidance = []
    all_messages = []  # Keep ALL messages across restarts
    current_prompt = initial_prompt
    max_restarts = 3
    restart_count = 0

    try:
        while restart_count < max_restarts:
            was_interrupted = False

            # Collect messages from Claude
            async for message in query_func(current_prompt, options, operation_name):
                all_messages.append(message)

                # Save context based on message type
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            monitor.save_context("response", block.text)
                        elif isinstance(block, ThinkingBlock):
                            monitor.save_context("thought", block.thinking)
                        elif isinstance(block, ToolUseBlock):
                            monitor.save_context("tool_use", f"{block.name}: {block.input}")

                # Check for interruption periodically
                if monitor.check_interrupted():
                    was_interrupted = True
                    printer.print("\n⚠️ Interruption detected. Waiting for current operation to complete...")
                    # Let current operation finish but break after
                    break

            if was_interrupted:
                # Show Claude's context so far
                context_summary = monitor.get_context_summary()
                if context_summary:
                    printer.print("\n📋 Claude's work before interruption:")
                    printer.print(context_summary)

                # Get guidance from user
                guidance = await monitor.get_guidance()

                if guidance:
                    accumulated_guidance.append(guidance)
                    restart_count += 1

                    # Rebuild prompt with context and guidance
                    current_prompt = initial_prompt

                    # Add Claude's previous context
                    if context_summary:
                        current_prompt += "\n\n=== CONTEXT FROM PREVIOUS ATTEMPT ===\n"
                        current_prompt += "You were working on this task and made the following progress:\n"
                        current_prompt += context_summary
                        current_prompt += "\n\nPlease continue from where you left off, taking into account the following guidance:"

                    # Add all accumulated guidance
                    if accumulated_guidance:
                        current_prompt += "\n\n=== ADDITIONAL GUIDANCE FROM USER ===\n"
                        for i, g in enumerate(accumulated_guidance, 1):
                            current_prompt += f"{i}. {g}\n"

                    printer.print(f"\n🔄 Restarting {operation_name} with context and guidance (attempt {restart_count + 1}/{max_restarts + 1})...")

                    # Don't reset context - keep accumulating
                    continue
                else:
                    # No guidance, return what we have
                    return all_messages, True
            else:
                # Completed without interruption
                return all_messages, False

        printer.print(f"\n⚠️ Maximum restart attempts ({max_restarts}) reached.")
        return all_messages, True

    finally:
        monitor.stop()


def is_interruption_enabled() -> bool:
    """Check if interruption feature is enabled and available."""
    import os
    enabled = os.environ.get("KLAUS_ENABLE_INTERRUPTION", "false").lower() == "true"
    return enabled and KEYBOARD_AVAILABLE