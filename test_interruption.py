#!/usr/bin/env python3
"""Test script for Claude Code interruption mechanism.

This script demonstrates the interruption feature by running a simple
Claude Code task that can be interrupted with Ctrl+I.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from workflow_tools.contexts import WorkflowContext
from workflow_tools.services.claude_code_service import ClaudeCodeService
from workflow_tools.common import printer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_interruption():
    """Test the interruption mechanism with a simple Claude Code task."""

    # Enable interruption feature
    os.environ["KLAUS_ENABLE_INTERRUPTION"] = "true"

    printer.print_section_header("Claude Code Interruption Test", icon="🧪")
    printer.print("")
    printer.print("This test will demonstrate the interruption feature.")
    printer.print("During Claude's execution, you can press Ctrl+I to interrupt and add guidance.")
    printer.print("")

    # Create context and service
    context = WorkflowContext()
    service = ClaudeCodeService(context, debug_mode=True)

    # Check if interruption is enabled
    if service.enable_interruption:
        printer.print("✅ Interruption feature is ENABLED")
    else:
        printer.print("❌ Interruption feature is DISABLED")
        printer.print("   Set KLAUS_ENABLE_INTERRUPTION=true to enable")
        return

    # Create a test app directory
    test_app_dir = project_root / "test_app"
    test_app_dir.mkdir(exist_ok=True)

    # Create a simple starter file
    starter_file = test_app_dir / "main.py"
    starter_file.write_text("""# Starter application
print("Hello from starter app")

# TODO: Add functionality here
""")

    printer.print(f"\n📁 Test app directory: {test_app_dir}")
    printer.print("")

    # Test prompt
    test_prompt = """
Please create a simple Python application that:
1. Counts from 1 to 100
2. For each number, prints whether it's prime or not
3. At the end, prints the total count of prime numbers found

Take your time and think through the implementation step by step.
"""

    printer.print("📝 Test Task:")
    printer.print(test_prompt)
    printer.print("")
    printer.print("=" * 60)
    printer.print("🚀 Starting Claude Code with interruption support...")
    printer.print("   Press Ctrl+I at any time to interrupt and add guidance")
    printer.print("=" * 60)
    printer.print("")

    try:
        # Run the code generation with interruption enabled
        code, env_vars = await service.generate_code(
            user_prompt=test_prompt,
            app_dir=str(test_app_dir),
            workflow_type="source"
        )

        if code:
            printer.print("")
            printer.print("=" * 60)
            printer.print("✅ Code generation completed successfully!")
            printer.print("")
            printer.print("Generated code preview:")
            printer.print("-" * 40)
            lines = code.split('\n')[:20]  # Show first 20 lines
            for line in lines:
                printer.print(f"  {line}")
            if len(code.split('\n')) > 20:
                printer.print("  ...")
            printer.print("-" * 40)
        else:
            printer.print("❌ Code generation failed")

    except KeyboardInterrupt:
        printer.print("\n\n⚠️ Test interrupted by user (Ctrl+C)")
    except Exception as e:
        printer.print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if test_app_dir.exists():
            import shutil
            shutil.rmtree(test_app_dir)
            printer.print(f"\n🧹 Cleaned up test directory: {test_app_dir}")


async def main():
    """Main entry point."""
    printer.print("")
    printer.print("=" * 60)
    printer.print("CLAUDE CODE INTERRUPTION MECHANISM TEST")
    printer.print("=" * 60)
    printer.print("")

    # Check for required environment variables
    if not os.environ.get("ANTHROPIC_API_KEY"):
        printer.print("❌ Error: ANTHROPIC_API_KEY not set in environment")
        printer.print("   Please set your Anthropic API key in .env file")
        return 1

    # Run the test
    await test_interruption()

    printer.print("")
    printer.print("=" * 60)
    printer.print("Test completed!")
    printer.print("=" * 60)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)