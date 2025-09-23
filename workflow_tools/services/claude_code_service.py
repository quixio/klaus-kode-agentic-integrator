"""Claude Code SDK service for code generation and debugging.

This service provides integration with Claude Code SDK for generating
and debugging Quix applications. All AI operations now use Anthropic's
Claude models exclusively.
"""

import os
import sys
import platform
import subprocess
import yaml
import anyio
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, TextBlock, ToolUseBlock, ResultMessage, ThinkingBlock
from rich.console import Console
from workflow_tools.core.claude_interruption import InterruptibleTransport, InterruptibleClaudeQuery
from rich.panel import Panel
from workflow_tools.contexts import WorkflowContext
from workflow_tools.common import printer, extract_python_code_from_llm_output
from workflow_tools.core.enhanced_input import get_enhanced_input_async
from workflow_tools.core.config_loader import config
from workflow_tools.core.questionary_utils import text


def monkey_patch_claude_sdk_for_windows(cli_path: str):
    """Monkey-patch the Claude SDK to use our configured CLI path on Windows.
    
    This is necessary because the SDK doesn't properly support Windows paths
    and doesn't provide a way to override the CLI path through its public API.
    """
    try:
        from claude_code_sdk._internal.transport import subprocess_cli
        
        # Store the original method
        original_find_cli = subprocess_cli.SubprocessCLITransport._find_cli
        
        # Create a patched version that returns our configured path
        def patched_find_cli(self):
            """Return the configured CLI path directly."""
            return cli_path
        
        # Replace the method
        subprocess_cli.SubprocessCLITransport._find_cli = patched_find_cli
        
        printer.print(f"🔧 Monkey-patched Claude SDK to use: {cli_path}")
        return True
    except Exception as e:
        printer.print(f"⚠️ Failed to monkey-patch Claude SDK: {e}")
        return False


class ClaudeCodeService:
    """Service for integrating Claude Code SDK with the Quix workflow."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        """Initialize the Claude Code service.
        
        Args:
            context: Workflow context containing app details
            debug_mode: Whether to enable debug logging
        """
        self.context = context
        self.debug_mode = debug_mode
        
        # Load Claude Code SDK configuration from models.yaml
        models_config = config.load_models_config()
        self.claude_config = models_config.get("models", {}).get("claude_code_sdk", {})
        
        # Set defaults if not in config
        if not self.claude_config:
            printer.print("⚠️ Warning: Claude Code SDK config not found in models.yaml, using defaults")
            self.claude_config = {
                "model": "sonnet-4.1",
                "max_turns": 10,
                "max_thinking_tokens": 8000,
                "allowed_tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep","MultiEdit"],
                "permission_mode": "acceptEdits"
            }
        
        # Initialize cache utils for caching Claude Code SDK generated code and user inputs
        from workflow_tools.phases.shared.cache_utils import CacheUtils
        self.cache_utils = CacheUtils(context, debug_mode)
        
        # Detect and configure Claude Code CLI path
        self.claude_cli_path = self._detect_claude_cli_path()
        
        # Initialize thought process tracking for debug cycles
        self._debug_attempt_counters = {"main": 0, "connection_test": 0}

        # Interruption feature flag - can be controlled via environment or config
        self.enable_interruption = os.environ.get("KLAUS_ENABLE_INTERRUPTION", "false").lower() == "true"
    
    def _detect_claude_cli_path(self) -> Optional[str]:
        """Detect Claude Code CLI installation path.

        Returns:
            Path to Claude CLI executable or None if not found
        """
        # Ensure Node.js is in PATH for Claude CLI to work
        self._ensure_node_in_path()

        # First check environment variable
        env_cli_path = os.environ.get("CLAUDE_CLI_PATH")
        if env_cli_path:
            if os.path.isfile(env_cli_path):
                printer.print(f"✅ Using Claude CLI from environment variable: {env_cli_path}")
                if platform.system() == "Windows":
                    monkey_patch_claude_sdk_for_windows(env_cli_path)
                return env_cli_path
            elif self._verify_claude_cli(env_cli_path):
                printer.print(f"✅ Using Claude CLI path from environment variable: {env_cli_path}")
                if platform.system() == "Windows":
                    for ext in [".exe", ".cmd", ".bat", ""]:
                        claude_exe = os.path.join(env_cli_path, f"claude{ext}")
                        if os.path.exists(claude_exe):
                            printer.print(f"   Found executable: {claude_exe}")
                            monkey_patch_claude_sdk_for_windows(claude_exe)
                            break
                return env_cli_path
        
        # Check local config override file (not in version control)
        local_config_path = Path("config/local.yaml")
        if local_config_path.exists():
            try:
                with open(local_config_path, 'r', encoding='utf-8') as f:
                    local_config = yaml.safe_load(f) or {}
                    local_cli_path = local_config.get("claude_cli_path")
                    if local_cli_path:
                        if os.path.isfile(local_cli_path):
                            printer.print(f"✅ Using Claude CLI from local config: {local_cli_path}")
                            if platform.system() == "Windows":
                                monkey_patch_claude_sdk_for_windows(local_cli_path)
                            return local_cli_path
                        elif self._verify_claude_cli(local_cli_path):
                            printer.print(f"✅ Using Claude CLI path from local config: {local_cli_path}")
                            if platform.system() == "Windows":
                                for ext in [".exe", ".cmd", ".bat", ""]:
                                    claude_exe = os.path.join(local_cli_path, f"claude{ext}")
                                    if os.path.exists(claude_exe):
                                        printer.print(f"   Found executable: {claude_exe}")
                                        monkey_patch_claude_sdk_for_windows(claude_exe)
                                        break
                            return local_cli_path
            except Exception:
                pass  # Ignore errors in local config
        
        # Then check if path is configured in models.yaml (for backwards compatibility)
        configured_path = self.claude_config.get("cli_path")
        if configured_path:
            # If it's a direct path to executable, use it directly
            if os.path.isfile(configured_path):
                printer.print(f"✅ Using configured Claude CLI executable: {configured_path}")
                # Monkey-patch the SDK to use this exact path (necessary for Windows)
                if platform.system() == "Windows":
                    monkey_patch_claude_sdk_for_windows(configured_path)
                return configured_path
            # If it's a directory, verify the CLI exists there
            elif self._verify_claude_cli(configured_path):
                printer.print(f"✅ Using configured Claude CLI path: {configured_path}")
                # For directories, construct the full path and monkey-patch if on Windows
                if platform.system() == "Windows":
                    # Find the actual executable in the directory
                    for ext in [".exe", ".cmd", ".bat", ""]:
                        claude_exe = os.path.join(configured_path, f"claude{ext}")
                        if os.path.exists(claude_exe):
                            printer.print(f"   Found executable: {claude_exe}")
                            monkey_patch_claude_sdk_for_windows(claude_exe)
                            break
                return configured_path
        
        # Common search paths based on OS and installation method
        search_paths = []
        home = Path.home()
        
        # Get npm global prefix
        npm_prefix = self._get_npm_prefix()
        if npm_prefix:
            npm_bin = os.path.join(npm_prefix, "bin")
            search_paths.append(npm_bin)
        
        # Platform-specific paths
        system = platform.system()
        
        if system == "Windows":
            # Windows paths
            search_paths.extend([
                os.path.join(os.environ.get("APPDATA", ""), "npm"),
                os.path.join(home, "AppData", "Roaming", "npm"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "npm"),
                os.path.join(home, ".local", "bin"),  # Windows .local/bin path
                "C:\\npm",
                "C:\\Program Files\\nodejs",
            ])
        elif system == "Darwin":  # macOS
            # macOS paths
            search_paths.extend([
                "/opt/homebrew/bin",
                "/usr/local/bin",
                os.path.join(home, ".npm-global", "bin"),
                os.path.join(home, "node_modules", ".bin"),
                "/opt/homebrew/Cellar/node/*/bin",
            ])
        else:  # Linux and others
            # Linux paths
            search_paths.extend([
                "/usr/local/bin",
                "/usr/bin",
                os.path.join(home, ".npm-global", "bin"),
                os.path.join(home, ".local", "bin"),
                os.path.join(home, "node_modules", ".bin"),
            ])
        
        # Add user-specific custom installation paths
        search_paths.extend([
            os.path.join(home, ".claude", "local", "node_modules", ".bin"),  # Custom install
            os.path.join(home, ".claude", "bin"),
            os.path.join(home, ".local", "share", "npm", "bin"),
        ])
        
        # Check each path
        for path in search_paths:
            if path and self._verify_claude_cli(path):
                printer.print(f"✅ Found Claude CLI at: {path}")
                self._save_cli_path_to_config(path)
                return path
        
        # Check if claude is in PATH
        if self._is_claude_in_path():
            printer.print("✅ Claude CLI found in system PATH")
            return None  # No need to add to PATH
        
        # If not found, prompt user
        return self._prompt_for_claude_path()
    
    async def _query_with_balance_retry(self, prompt: str, options: ClaudeCodeOptions, operation_name: str = "Claude Code operation", enable_interruption: bool = False):
        """Execute a Claude query with automatic retry on balance errors and optional interruption support.

        This centralized method handles credit balance errors gracefully by:
        1. Catching balance-related errors
        2. Showing a helpful message to the user
        3. Waiting for user to top up and press Enter
        4. Retrying the operation

        Args:
            prompt: The prompt to send to Claude
            options: Claude Code SDK options
            operation_name: Name of the operation for logging
            enable_interruption: Whether to enable keyboard interruption during execution

        Yields:
            Messages from Claude Code SDK

        Raises:
            Exception: For non-balance related errors
        """
        try:
            if enable_interruption:
                # Use interruptible query
                async for message in InterruptibleClaudeQuery.query_with_interruption(prompt=prompt, options=options):
                    yield message
            else:
                # Use standard query
                async for message in query(prompt=prompt, options=options):
                    yield message
        except Exception as e:
            error_msg = str(e)
            
            # Check if this is a balance error
            if "Credit balance is too low" in error_msg or "balance" in error_msg.lower():
                printer.print_section_header("Credit Balance Too Low", icon="⚠️", style="red")
                printer.print("")
                printer.print(f"Your Claude credit balance is insufficient for {operation_name}.")
                printer.print("Please top up your balance and then press Enter to retry.")
                printer.print("")
                printer.print("Visit: https://console.anthropic.com/settings/billing")
                printer.print("=" * 60)
                
                # Wait for user to top up and press Enter
                await get_enhanced_input_async("\n🔄 Press Enter when you're ready to retry (after topping up)...")
                
                printer.print(f"\n🔄 Retrying {operation_name}...")

                # Retry the query with same interruption settings
                if enable_interruption:
                    async for message in InterruptibleClaudeQuery.query_with_interruption(prompt=prompt, options=options):
                        yield message
                else:
                    async for message in query(prompt=prompt, options=options):
                        yield message
            else:
                # Re-raise non-balance errors
                raise
    
    def _ensure_node_in_path(self):
        """Ensure Node.js is in PATH for Claude CLI to work."""
        if shutil.which("node"):
            return

        # Find Node.js from NVM or standard locations
        import glob
        nvm_paths = glob.glob(os.path.expanduser("~/.nvm/versions/node/*/bin"))
        standard_paths = ["/usr/local/bin", "/usr/bin", "/opt/homebrew/bin"]

        for path in nvm_paths + standard_paths:
            node_exe = os.path.join(path, "node")
            if os.path.exists(node_exe):
                self._add_to_path(path)
                printer.print(f"✅ Added Node.js to PATH: {path}")
                return

    def _add_to_path(self, new_path: str):
        """Add a path to the system PATH environment variable."""
        current_path = os.environ.get("PATH", "")
        sep = ";" if platform.system() == "Windows" else ":"
        os.environ["PATH"] = f"{new_path}{sep}{current_path}"

    def _verify_claude_cli(self, path: str) -> bool:
        """Verify if Claude CLI exists at the given path.
        
        Args:
            path: Directory path or full executable path to check
            
        Returns:
            True if claude executable found, False otherwise
        """
        if not os.path.exists(path):
            return False
        
        # Check if path is a file (full executable path)
        if os.path.isfile(path):
            # Check if it's a claude executable
            basename = os.path.basename(path).lower()
            if basename.startswith("claude"):
                return True
            return False
        
        # Path is a directory, check for claude executable inside
        claude_exe = os.path.join(path, "claude")
        if platform.system() == "Windows":
            # Check for .exe, .cmd, .bat on Windows (order matters - .exe is most common)
            for ext in [".exe", ".cmd", ".bat", ""]:
                if os.path.exists(claude_exe + ext):
                    return True
        else:
            if os.path.exists(claude_exe):
                return True
        
        return False
    
    def _is_claude_in_path(self) -> bool:
        """Check if claude command is available in system PATH.
        
        Returns:
            True if claude is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _get_npm_prefix(self) -> Optional[str]:
        """Get npm global prefix path.
        
        Returns:
            npm prefix path or None if npm not available
        """
        try:
            result = subprocess.run(
                ["npm", "config", "get", "prefix"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return None
    
    def _prompt_for_claude_path(self) -> Optional[str]:
        """Prompt user for Claude CLI installation path.
        
        Returns:
            User-provided path or None if cancelled
        """
        printer.print("\n⚠️ Claude Code CLI not found automatically")
        printer.print("Please install Claude Code CLI or provide the installation path.")
        printer.print("\nTo install Claude Code CLI:")
        printer.print("  npm install -g @anthropic-ai/claude-code")
        printer.print("\nOr if already installed, enter the path to the claude executable")
        printer.print("Examples:")
        printer.print("  - Directory: C:\\Users\\YourName\\AppData\\Roaming\\npm")
        printer.print("  - Full path: C:\\Users\\YourName\\.local\\bin\\claude.exe")
        printer.print("  - Directory: /usr/local/bin")
        
        while True:
            user_path = text(
                "Enter Claude CLI path (or 'skip' to continue without Claude Code):"
            ).strip()
            
            if user_path.lower() == 'skip':
                printer.print("⚠️ Continuing without Claude Code integration")
                return None
            
            if user_path and self._verify_claude_cli(user_path):
                # If user provided full executable path, extract directory for PATH
                if os.path.isfile(user_path):
                    path_to_save = os.path.dirname(user_path)
                    printer.print(f"✅ Claude CLI verified at: {user_path}")
                    printer.print(f"   Will add directory to PATH: {path_to_save}")
                else:
                    path_to_save = user_path
                    printer.print(f"✅ Claude CLI verified in directory: {path_to_save}")
                
                self._save_cli_path_to_config(path_to_save)
                return path_to_save
            else:
                printer.print("❌ Claude CLI not found at that location. Please try again.")
    
    def _save_cli_path_to_config(self, path: str):
        """Save the Claude CLI path to local.yaml configuration (not version controlled).
        
        Args:
            path: Path to save
        """
        try:
            local_config_path = Path("config/local.yaml")
            
            # Load existing local config or create new
            if local_config_path.exists():
                with open(local_config_path, 'r', encoding='utf-8') as f:
                    local_config = yaml.safe_load(f) or {}
            else:
                local_config = {}
            
            # Add cli_path
            local_config["claude_cli_path"] = path
            
            # Ensure config directory exists
            local_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write local config
            with open(local_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)
            
            printer.print(f"💾 Saved Claude CLI path to config/local.yaml (not in version control)")
        except Exception as e:
            printer.print(f"⚠️ Could not save path to local config: {e}")
    
    def _save_thought_process(self, thought_process: str, code_type: str, attempt_number: int):
        """Save Claude's thought process to a file for debug cycle reference.
        
        Args:
            thought_process: The complete thought process from Claude
            code_type: Either 'main' or 'connection_test'
            attempt_number: The attempt number for this debug cycle
        """
        try:
            from workflow_tools.core.working_directory import WorkingDirectory
            
            # Create thoughts directory structure: working_files/current/thoughts/
            thoughts_dir = os.path.join(WorkingDirectory.get_current_app_dir(), "thoughts")
            os.makedirs(thoughts_dir, exist_ok=True)
            
            # Create filename with code type and attempt number
            filename = f"{code_type}_thoughts_attempt{attempt_number}.txt"
            filepath = os.path.join(thoughts_dir, filename)
            
            # Save thought process with timestamp header
            from datetime import datetime
            header = f"# Claude Thought Process - {code_type.title()} App Debug Attempt {attempt_number}\n"
            header += f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            header += f"# Workflow Type: {getattr(self.context, 'selected_workflow', 'unknown')}\n\n"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(header + thought_process)
            
            if self.debug_mode:
                printer.print(f"💭 Saved thought process to: {filepath}")
            
        except Exception as e:
            if self.debug_mode:
                printer.print(f"⚠️ Warning: Could not save thought process: {e}")
    
    def _load_previous_thought_processes(self, code_type: str) -> str:
        """Load all previous thought processes for the given code type.
        
        Args:
            code_type: Either 'main' or 'connection_test'
            
        Returns:
            Concatenated previous thought processes or empty string if none found
        """
        try:
            from workflow_tools.core.working_directory import WorkingDirectory
            
            thoughts_dir = os.path.join(WorkingDirectory.get_current_app_dir(), "thoughts")
            if not os.path.exists(thoughts_dir):
                return ""
            
            # Find all thought files for this code type
            thought_files = []
            for filename in os.listdir(thoughts_dir):
                if filename.startswith(f"{code_type}_thoughts_attempt") and filename.endswith(".txt"):
                    thought_files.append(filename)
            
            if not thought_files:
                return ""
            
            # Sort by attempt number
            thought_files.sort(key=lambda x: int(x.split('attempt')[1].split('.')[0]))
            
            # Load and concatenate all previous thoughts
            previous_thoughts = []
            for filename in thought_files:
                filepath = os.path.join(thoughts_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        previous_thoughts.append(f"=== {filename} ===\n{content}\n")
                except Exception as e:
                    if self.debug_mode:
                        printer.print(f"⚠️ Warning: Could not read {filename}: {e}")
            
            if previous_thoughts:
                combined = "\n".join(previous_thoughts)
                if self.debug_mode:
                    printer.print(f"💭 Loaded {len(previous_thoughts)} previous thought process(es) for {code_type}")
                return combined
            
        except Exception as e:
            if self.debug_mode:
                printer.print(f"⚠️ Warning: Could not load previous thought processes: {e}")
        
        return ""
    
    async def generate_code(
        self, 
        user_prompt: str, 
        app_dir: str, 
        workflow_type: str
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Generate code using Claude Code SDK.
        
        Args:
            user_prompt: User's description of what they want to build
            app_dir: Directory containing the starter app code
            workflow_type: Either "sink" or "source"
            
        Returns:
            Tuple of (generated_code, env_vars_dict) or (None, None) if failed
        """
        printer.print(f"\n🤖 Starting Claude Code for {workflow_type} generation...")
        
        # Get the main workflow directory (where main.py is)
        main_workflow_dir = os.getcwd()
        # Calculate relative path from main workflow dir to app dir
        relative_app_path = os.path.relpath(app_dir, main_workflow_dir)
        
        printer.print_debug(f"   Main workflow directory: {main_workflow_dir}")
        printer.print_debug(f"   App directory (absolute): {app_dir}")
        printer.print_debug(f"   App directory (relative): {relative_app_path}")
        
        # Ensure Claude CLI is in PATH with proper separator for the OS
        if self.claude_cli_path:
            current_path = os.environ.get("PATH", "")
            if self.claude_cli_path not in current_path:
                # Use proper path separator for the OS
                path_separator = ";" if platform.system() == "Windows" else ":"
                os.environ["PATH"] = f"{self.claude_cli_path}{path_separator}{current_path}"
                printer.print_debug(f"   Added Claude CLI to PATH: {self.claude_cli_path}")
        elif not self._is_claude_in_path():
            printer.print("⚠️ Warning: Claude CLI not found. Code generation may fail.")
            return None, None
        
        # Debug: Check app directory contents BEFORE Claude Code SDK runs
        printer.print_debug(f"🔍 DEBUG: App directory: {app_dir}")
        printer.print_debug(f"🔍 DEBUG: App directory exists: {os.path.exists(app_dir)}")
        if os.path.exists(app_dir):
            files = os.listdir(app_dir)
            printer.print_debug(f"🔍 DEBUG: Files in app dir before: {files}")
            main_py_path = os.path.join(app_dir, "main.py")
            if os.path.exists(main_py_path):
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                printer.print_debug(f"🔍 DEBUG: Original main.py length: {len(original_content)} chars")
                printer.print_debug(f"🔍 DEBUG: First 200 chars of original main.py:")
                printer.print_debug(original_content[:200] + "..." if len(original_content) > 200 else original_content)
        
        # Construct the enhanced prompt with explicit path information
        enhanced_prompt = self._build_enhanced_prompt_with_path(user_prompt, workflow_type, relative_app_path)
        
        # Load system prompt from template with path context
        from workflow_tools.core.prompt_manager import load_task_prompt
        system_prompt = load_task_prompt(
            "claude_code_system_prompt", 
            workflow_type=workflow_type,
            app_path=relative_app_path
        )
        
        # Print all prompts being sent to Claude
        printer.print_debug("\n" + "=" * 80)
        printer.print_debug("🔍 CLAUDE CODE PROMPTS - GENERATION")
        printer.print_debug("=" * 80)
        
        # Check prompt sizes
        system_prompt_size = len(system_prompt)
        enhanced_prompt_size = len(enhanced_prompt)
        total_size = system_prompt_size + enhanced_prompt_size
        
        printer.print_debug(f"\n⚠️ PROMPT SIZE CHECK:")
        printer.print_debug(f"   System prompt: {system_prompt_size:,} characters")
        printer.print_debug(f"   User prompt: {enhanced_prompt_size:,} characters")
        printer.print_debug(f"   TOTAL: {total_size:,} characters")
        
        # Warn if exceeding limits
        if platform.system() == "Windows" and total_size > 8000:
            printer.print_debug(f"   ❌ EXCEEDS Windows limit (8KB)!")
        elif total_size > 2000000:  # 2MB for Linux
            printer.print_debug(f"   ❌ EXCEEDS Linux limit (2MB)!")
        
        printer.print_debug("\n📋 SYSTEM PROMPT:")
        printer.print_debug("-" * 40)
        printer.print_debug(system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt)
        printer.print_debug("-" * 40)
        printer.print_debug("\n📝 USER PROMPT:")
        printer.print_debug("-" * 40)
        printer.print_debug(enhanced_prompt[:500] + "..." if len(enhanced_prompt) > 500 else enhanced_prompt)
        printer.print_debug("-" * 40)
        printer.print_debug("=" * 80 + "\n")
        
        # Configure Claude Code options from config
        # Start Claude Code in the main workflow directory, NOT the app directory
        options = ClaudeCodeOptions(
            allowed_tools=self.claude_config.get("allowed_tools", ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]),
            permission_mode=self.claude_config.get("permission_mode", "acceptEdits"),
            cwd=main_workflow_dir,  # Use main workflow directory as working directory
            system_prompt=system_prompt,
            max_turns=self.claude_config.get("max_turns", 10),
            model=self.claude_config.get("model", "sonnet-4.1")
        )
        
        # Debug: Log Claude Code SDK configuration
        printer.print_debug(f"🔍 DEBUG: Claude Code SDK configuration:")
        printer.print_debug(f"   - Working directory (cwd): {main_workflow_dir}")
        printer.print_debug(f"   - Target app path (relative): {relative_app_path}")
        printer.print_debug(f"   - Model: {self.claude_config.get('model', 'sonnet-4.1')}")
        printer.print_debug(f"   - Max turns: {self.claude_config.get('max_turns', 10)}")
        printer.print_debug(f"   - Allowed tools: {self.claude_config.get('allowed_tools', ['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep'])}")
        printer.print_debug(f"   - Permission mode: {self.claude_config.get('permission_mode', 'acceptEdits')}")
        
        # Track the conversation and collect responses
        full_response = []
        code_content = None
        total_cost = 0.0
        
        try:
            printer.print("\n📝 Claude Code is working on your application...")
            if self.enable_interruption:
                printer.print("   💡 Press Ctrl+I to interrupt and add guidance")
            printer.print("=" * 60)

            async for message in self._query_with_balance_retry(enhanced_prompt, options, f"{workflow_type} code generation", enable_interruption=self.enable_interruption):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            # Display Claude's thoughts
                            printer.print(f"Claude: {block.text}")
                            full_response.append(block.text)
                        elif isinstance(block, ThinkingBlock):
                            # Log Claude's internal thinking (in debug mode)
                            if self.debug_mode:
                                printer.print_debug(f"   💭 Thinking: {block.thinking[:200]}..." if len(block.thinking) > 200 else f"   💭 Thinking: {block.thinking}")
                        elif isinstance(block, ToolUseBlock):
                            # Log tool usage
                            if self.debug_mode:
                                printer.print_debug(f"   🔧 Using tool: {block.name}")
                
                elif isinstance(message, ResultMessage):
                    if message.total_cost_usd > 0:
                        total_cost = message.total_cost_usd
            
            printer.print("=" * 60)
            printer.print(f"✅ Claude Code completed (Cost: ${total_cost:.4f})")
            
            # Debug: Check app directory contents AFTER Claude Code SDK runs
            printer.print_debug(f"🔍 DEBUG: Checking app directory after Claude Code SDK...")
            if os.path.exists(app_dir):
                files = os.listdir(app_dir)
                printer.print_debug(f"🔍 DEBUG: Files in app dir after: {files}")
            
            # Read the modified main.py
            main_py_path = os.path.join(app_dir, "main.py")
            if os.path.exists(main_py_path):
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    code_content = f.read()
                printer.print_debug(f"🔍 DEBUG: Updated main.py length: {len(code_content)} chars")
                printer.print_debug(f"🔍 DEBUG: First 200 chars of updated main.py:")
                printer.print_debug(code_content[:200] + "..." if len(code_content) > 200 else code_content)
                printer.print_debug("✅ Successfully read updated main.py")
            else:
                printer.print("❌ Error: main.py not found after generation")
                return None, None
            
            # Read the updated app.yaml to get environment variables
            env_vars = self._read_app_yaml_env_vars(app_dir)
            
            return code_content, env_vars
            
        except Exception as e:
            printer.print(f"❌ Error during Claude Code generation: {str(e)}")
            if self.debug_mode:
                import traceback
                printer.print(traceback.format_exc())
            return None, None
    
    async def debug_code(
        self, 
        error_logs: str, 
        app_dir: str,
        current_code: str,
        is_connection_test: bool = False
    ) -> Optional[str]:
        """Debug code using Claude Code SDK.
        
        Args:
            error_logs: The error logs from running the code
            app_dir: Directory containing the app code
            current_code: The current code that produced errors
            is_connection_test: Whether this is a connection test (vs full app)
            
        Returns:
            Fixed code or None if debugging failed
        """
        printer.print("\n🔧 Starting Claude Code for debugging...")
        
        # Increment debug attempt counter based on type
        counter_key = "connection_test" if is_connection_test else "main"
        self._debug_attempt_counters[counter_key] += 1
        current_attempt = self._debug_attempt_counters[counter_key]
        debug_type = "connection test" if is_connection_test else "main app"
        printer.print(f"💭 Debug attempt #{current_attempt} for {debug_type}")
        
        # Load previous thought processes to avoid repeating mistakes
        previous_thoughts = self._load_previous_thought_processes(counter_key)
        
        # Get the main workflow directory (where main.py is)
        main_workflow_dir = os.getcwd()
        # Calculate relative path from main workflow dir to app dir
        relative_app_path = os.path.relpath(app_dir, main_workflow_dir)
        
        printer.print(f"   Main workflow directory: {main_workflow_dir}")
        printer.print(f"   App directory (absolute): {app_dir}")
        printer.print(f"   App directory (relative): {relative_app_path}")
        
        # Ensure Claude CLI is in PATH
        if self.claude_cli_path:
            current_path = os.environ.get("PATH", "")
            if self.claude_cli_path not in current_path:
                os.environ["PATH"] = f"{self.claude_cli_path}:{current_path}"
                printer.print_debug(f"   Added Claude CLI to PATH: {self.claude_cli_path}")
        elif not self._is_claude_in_path():
            printer.print("⚠️ Warning: Claude CLI not found. Code generation may fail.")
            return None, None
        
        # Debug: Check app directory contents BEFORE Claude Code SDK runs
        printer.print_debug(f"🔍 DEBUG: App directory: {app_dir}")
        printer.print_debug(f"🔍 DEBUG: App directory absolute path: {os.path.abspath(app_dir)}")
        printer.print_debug(f"🔍 DEBUG: Current working directory: {os.getcwd()}")
        printer.print_debug(f"🔍 DEBUG: App directory exists: {os.path.exists(app_dir)}")
        if os.path.exists(app_dir):
            files = os.listdir(app_dir)
            printer.print_debug(f"🔍 DEBUG: Files in app dir before debug: {files}")
            main_py_path = os.path.join(app_dir, "main.py")
            if os.path.exists(main_py_path):
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                printer.print_debug(f"🔍 DEBUG: Current main.py path: {os.path.abspath(main_py_path)}")
                printer.print_debug(f"🔍 DEBUG: Current main.py length: {len(original_content)} chars")
                printer.print_debug(f"🔍 DEBUG: First 200 chars of current main.py:")
                printer.print_debug(original_content[:200] + "..." if len(original_content) > 200 else original_content)
                
                # Check if this looks like the workflow orchestrator main.py vs app main.py
                if "WorkflowOrchestrator" in original_content:
                    printer.print("🚨 WARNING: This looks like the workflow orchestrator main.py, not the app main.py!")
                elif "quixstreams" in original_content.lower():
                    printer.print("✅ This looks like the correct application main.py")
            else:
                printer.print(f"❌ main.py not found at: {os.path.abspath(main_py_path)}")
        
        # Load debug prompts from templates with path information
        from workflow_tools.core.prompt_manager import load_task_prompt
        
        # Get schema analysis for context during debugging
        schema_analysis = ""
        
        # Determine workflow type from context
        if hasattr(self.context, 'selected_workflow') and self.context.selected_workflow:
            workflow_type = str(self.context.selected_workflow.value).lower()
            if 'source' in workflow_type:
                workflow_type = "source"
            elif 'diagnose' in workflow_type:
                workflow_type = "diagnose"
            else:
                workflow_type = "sink"
        else:
            # Try to infer from what's in context
            if hasattr(self.context, 'diagnose'):
                workflow_type = "diagnose"
            elif hasattr(self.context.technology, 'source_technology') and self.context.technology.source_technology:
                workflow_type = "source"
            else:
                workflow_type = "sink"
        
        # Get appropriate schema/analysis based on workflow type
        if workflow_type == "diagnose":
            # For diagnose workflow, get the app analysis
            if hasattr(self.context, 'diagnose') and self.context.diagnose.get('app_analysis'):
                schema_analysis = self.context.diagnose['app_analysis']
            else:
                # Try to load from cache
                from workflow_tools.core.working_directory import WorkingDirectory
                if hasattr(self.context.workspace, 'app_name'):
                    app_name = self.context.workspace.app_name
                    analysis_path = WorkingDirectory.get_cached_analysis_path("diagnose", app_name)
                    try:
                        with open(analysis_path, "r", encoding='utf-8') as f:
                            schema_analysis = f.read()
                    except:
                        pass
        elif workflow_type == "sink":
            if self.context.schema.data_schema:
                schema_analysis = self.context.schema.data_schema
            else:
                from workflow_tools.core.working_directory import WorkingDirectory
                schema_path = WorkingDirectory.get_cached_schema_path("sink", "schema_analysis")
                try:
                    with open(schema_path, "r", encoding='utf-8') as f:
                        schema_analysis = f.read()
                except:
                    pass
        else:  # source
            if hasattr(self.context.code_generation, 'source_schema_doc_path'):
                try:
                    with open(self.context.code_generation.source_schema_doc_path, 'r', encoding='utf-8') as f:
                        schema_analysis = f.read()
                except:
                    pass
            elif hasattr(self.context.code_generation, 'connection_test_code'):
                schema_analysis = f"## Connection Test Code:\n```python\n{self.context.code_generation.connection_test_code}\n```"
        
        debug_prompt = load_task_prompt(
            "claude_code_debug", 
            error_logs=error_logs,
            app_path=relative_app_path,
            schema_analysis=schema_analysis,
            workflow_type=workflow_type,
            previous_thoughts=previous_thoughts
        )
        debug_system_prompt = load_task_prompt(
            "claude_code_debug_system_prompt",
            app_path=relative_app_path
        )

        # Print all prompts being sent to Claude (only in verbose mode)
        printer.print_debug("\n" + "=" * 80)
        printer.print_debug("🔍 CLAUDE CODE PROMPTS - DEBUGGING")
        printer.print_debug("=" * 80)
        printer.print_debug("\n📋 DEBUG SYSTEM PROMPT:")
        printer.print_debug("-" * 40)
        printer.print_debug(debug_system_prompt)
        printer.print_debug("-" * 40)
        printer.print_debug("\n🐛 DEBUG USER PROMPT:")
        printer.print_debug("-" * 40)
        printer.print_debug(debug_prompt)
        printer.print_debug("-" * 40)
        printer.print_debug("=" * 80 + "\n")

        # Configure Claude Code options for debugging from config
        # Start Claude Code in the main workflow directory, NOT the app directory
        debug_config = self.claude_config.get("debug", {})
        options = ClaudeCodeOptions(
            allowed_tools=self.claude_config.get("allowed_tools", ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]),
            permission_mode=self.claude_config.get("permission_mode", "acceptEdits"),
            cwd=main_workflow_dir,  # Use main workflow directory as working directory
            system_prompt=debug_system_prompt,
            max_turns=debug_config.get("max_turns", 5),
            model=debug_config.get("model", self.claude_config.get("model", "sonnet-4.1"))
        )
        
        # Debug: Log Claude Code SDK configuration for debugging
        printer.print_debug(f"🔍 DEBUG: Claude Code SDK debug configuration:")
        printer.print_debug(f"   - Working directory (cwd): {main_workflow_dir}")
        printer.print_debug(f"   - Target app path (relative): {relative_app_path}")
        printer.print_debug(f"   - Model: {debug_config.get('model', self.claude_config.get('model', 'sonnet-4.1'))}")
        printer.print_debug(f"   - Max turns: {debug_config.get('max_turns', 5)}")
        printer.print_debug(f"   - Allowed tools: {self.claude_config.get('allowed_tools', ['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep'])}")
        printer.print_debug(f"   - Permission mode: {self.claude_config.get('permission_mode', 'acceptEdits')}")
        
        try:
            printer.print("\n🔍 Claude Code is analyzing and fixing the errors...")
            if self.enable_interruption:
                printer.print("   💡 Press Ctrl+I to interrupt and add guidance")
            printer.print("=" * 60)

            # Collect Claude's thought process for saving
            claude_thoughts = []
            claude_outputs = []

            async for message in self._query_with_balance_retry(debug_prompt, options, "code debugging", enable_interruption=self.enable_interruption):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            printer.print(f"Claude: {block.text}")
                            # Collect Claude's output for display
                            claude_outputs.append(block.text)
                        elif isinstance(block, ThinkingBlock):
                            # Collect Claude's actual thinking/reasoning
                            claude_thoughts.append(f"[THINKING]: {block.thinking}")
                            if self.debug_mode:
                                printer.print(f"💭 [Debug] Claude thinking: {block.thinking[:200]}..." if len(block.thinking) > 200 else f"💭 [Debug] Claude thinking: {block.thinking}")
            
            printer.print("=" * 60)
            
            # Save Claude's thought process for future reference
            if claude_thoughts or claude_outputs:
                # Combine actual thinking with outputs for complete context
                combined_process = []
                if claude_thoughts:
                    combined_process.append("=== CLAUDE'S INTERNAL REASONING ===")
                    combined_process.extend(claude_thoughts)
                if claude_outputs:
                    combined_process.append("\n=== CLAUDE'S VISIBLE OUTPUT ===")
                    combined_process.extend(claude_outputs)

                thought_process = "\n\n".join(combined_process)
                self._save_thought_process(thought_process, counter_key, current_attempt)
                printer.print(f"💭 Saved thought process for {debug_type} attempt #{current_attempt} (thinking: {len(claude_thoughts)}, outputs: {len(claude_outputs)})")
            
            # Debug: Check app directory contents AFTER Claude Code SDK runs
            printer.print_debug(f"🔍 DEBUG: Checking app directory after debug...")
            if os.path.exists(app_dir):
                files = os.listdir(app_dir)
                printer.print_debug(f"🔍 DEBUG: Files in app dir after debug: {files}")
            
            # Read the fixed main.py
            main_py_path = os.path.join(app_dir, "main.py")
            if os.path.exists(main_py_path):
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    fixed_code = f.read()
                printer.print_debug(f"🔍 DEBUG: Fixed main.py path: {os.path.abspath(main_py_path)}")
                printer.print_debug(f"🔍 DEBUG: Fixed main.py length: {len(fixed_code)} chars")
                printer.print_debug(f"🔍 DEBUG: First 200 chars of fixed main.py:")
                printer.print_debug(fixed_code[:200] + "..." if len(fixed_code) > 200 else fixed_code)
                
                # Verify what Claude Code actually worked on
                if "WorkflowOrchestrator" in fixed_code:
                    printer.print("🚨 ERROR: Claude Code worked on the workflow orchestrator main.py instead of the app main.py!")
                    printer.print("🚨 This means the wrong directory was used or Claude Code found the wrong file!")
                elif "quixstreams" in fixed_code.lower():
                    printer.print("✅ Claude Code worked on the correct application main.py")
                    # Check if the specific f-string issue was fixed
                    if "metadata String DEFAULT '{{}}'" in fixed_code:
                        printer.print("✅ F-string issue appears to be fixed (found escaped braces)")
                    elif "metadata String DEFAULT '{}'" in fixed_code:
                        printer.print("❌ F-string issue NOT fixed (still has unescaped braces)")
                
                printer.print("✅ Successfully read fixed main.py")
                return fixed_code
            else:
                printer.print(f"❌ Error: main.py not found after debugging at: {os.path.abspath(main_py_path)}")
                return None
                
        except Exception as e:
            printer.print(f"❌ Error during Claude Code debugging: {str(e)}")
            if self.debug_mode:
                import traceback
                printer.print(traceback.format_exc())
            return None
    
    async def debug_connection_test(self, error_logs: str, app_dir: str, code: str = None) -> Optional[str]:
        """Debug connection test code using Claude Code SDK.
        
        This method uses Claude Code to debug connection tests while maintaining test scope.
        
        Args:
            error_logs: The error logs from the failed test
            app_dir: Directory containing the app code
            code: Optional current code (if not provided, reads from main.py)
            
        Returns:
            Fixed code if successful, None otherwise
        """
        printer.print("🔧 Debugging connection test with Claude Code SDK...")
        
        # Use the regular debug_code method with connection test context
        # The debug_code method already handles Claude Code SDK properly
        return await self.debug_code(error_logs, app_dir, code, is_connection_test=True)
    
    def _build_enhanced_prompt_with_path(self, user_prompt: str, workflow_type: str, relative_app_path: str) -> str:
        """Build an enhanced prompt with explicit path instructions for Claude Code.
        
        Args:
            user_prompt: The user's description of what to build
            workflow_type: Either "sink" or "source"
            relative_app_path: Relative path to the app directory from main workflow dir
            
        Returns:
            Enhanced prompt string with explicit path information and full context
        """
        from workflow_tools.core.prompt_manager import load_task_prompt
        
        # No longer loading large content into variables since Claude will read from files
        # The prompts now reference the file paths directly
        
        # Get credentials/environment variables info
        credentials_info = ""
        if self.context.credentials.connection_credentials:
            credentials_info = self.context.credentials.connection_credentials
        elif self.context.credentials.env_var_names:
            # Build credentials info from env var names
            env_vars = []
            for var_name in self.context.credentials.env_var_names:
                env_vars.append(f"- {var_name}: Use os.environ.get('{var_name}')")
            credentials_info = "\n".join(env_vars)
        
        # Get library item ID if available
        library_item_id = self.context.technology.library_item_id or "starter-" + workflow_type
        
        # Get workflow-specific variables
        # Both sink and source should use the actual topic name the user selected
        topic_name = self.context.workspace.topic_name or "output-topic"
        app_name = self.context.deployment.application_name or f"{workflow_type}-app"
        
        # Debug: Check what paths we're working with
        printer.print_debug(f"🔍 DEBUG: app_extract_dir: {self.context.code_generation.app_extract_dir}")
        printer.print_debug(f"🔍 DEBUG: relative_app_path: {relative_app_path}")
        printer.print_debug(f"🔍 DEBUG: topic_name for {workflow_type}: {topic_name}")
        
        # Load the appropriate workflow-specific template directly
        if workflow_type == "sink":
            template_name = "claude_code_sink_instructions"
            # For sinks, we need the topic_id for the schema file path
            topic_id = self.context.workspace.topic_id or "unknown_topic"
        else:  # source
            template_name = "claude_code_source_instructions"
            # For sources, create clean names for the schema file path
            destination_technology_clean = self.context.technology.destination_technology.replace(' ', '_').replace('/', '_').lower() if self.context.technology.destination_technology else "unknown"
            topic_name_clean = topic_name.replace(' ', '_').replace('/', '_').lower() if topic_name else "unknown"
        
        # Load and format the workflow-specific prompt template
        # Now we just pass file paths, not the actual content
        prompt_kwargs = {
            "user_prompt": user_prompt,
            "app_path": relative_app_path,
            "workflow_type": workflow_type,
            "credentials_info": credentials_info,
            "library_item_id": library_item_id,
            "topic_name": topic_name,
            "app_name": app_name,
            "sink_guidance": "",  # Empty - was removed for technology-agnostic approach
        }
        
        # Add workflow-specific variables
        if workflow_type == "sink":
            prompt_kwargs["topic_id"] = topic_id
        else:  # source
            prompt_kwargs["destination_technology"] = self.context.technology.destination_technology or "unknown"
            prompt_kwargs["destination_technology_clean"] = destination_technology_clean
            prompt_kwargs["topic_name_clean"] = topic_name_clean
        
        enhanced_prompt = load_task_prompt(template_name, **prompt_kwargs)
        
        return enhanced_prompt
    
    def _read_app_yaml_env_vars(self, app_dir: str) -> Optional[Dict[str, Any]]:
        """Read environment variables from app.yaml.
        
        Args:
            app_dir: Directory containing app.yaml
            
        Returns:
            Dictionary of environment variables or None
        """
        app_yaml_path = os.path.join(app_dir, "app.yaml")
        
        if not os.path.exists(app_yaml_path):
            printer.print("⚠️ Warning: app.yaml not found")
            return None
        
        try:
            with open(app_yaml_path, 'r', encoding='utf-8') as f:
                app_config = yaml.safe_load(f)
            
            # Extract environment variables
            env_vars = {}
            if 'variables' in app_config:
                for var in app_config['variables']:
                    var_name = var.get('name')
                    if var_name:
                        env_vars[var_name] = {
                            'description': var.get('description', ''),
                            'required': var.get('required', False),
                            'default': var.get('defaultValue', ''),
                            'input_type': var.get('inputType', 'FreeText')
                        }
            
            printer.print(f"📋 Found {len(env_vars)} environment variables in app.yaml")
            return env_vars
            
        except Exception as e:
            printer.print(f"❌ Error reading app.yaml: {str(e)}")
            return None
    
    async def generate_with_feedback_loop(
        self,
        workflow_type: str,
        app_dir: str,
        max_iterations: int = 3
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Generate code with user feedback loop.
        
        Args:
            workflow_type: Either "sink" or "source"
            app_dir: Directory containing the app
            max_iterations: Maximum number of feedback iterations
            
        Returns:
            Tuple of (final_code, env_vars) or (None, None) if aborted
        """
        from workflow_tools.common import printer, get_user_approval
        
        iteration = 0
        while iteration < max_iterations:
            # Get user prompt for what to build
            if iteration == 0:
                # For source workflows, check if we already have requirements from earlier in THIS workflow
                if workflow_type == "source" and hasattr(self.context.technology, 'source_technology') and self.context.technology.source_technology:
                    # We already have requirements from the connection test phase in THIS workflow
                    # No need to check cache or ask if they want to reuse - just show them and ask for additional
                    connection_requirements = self.context.technology.source_technology
                    printer.print(f"\n📝 Your connection test requirements were:")
                    printer.print(f"   \"{connection_requirements}\"")

                    # ALWAYS ask for additional requirements directly - no confusing cache prompts
                    printer.print("\n")
                    additional_requirements = text(
                        "🔄 Is there anything else you'd like to add for the main application?\n   (Or press Enter to use the same requirements)",
                        default=""
                    ).strip()

                    # Cache the additional requirements for future runs
                    if additional_requirements:
                        self.cache_utils.save_additional_requirements_to_cache(additional_requirements)

                    if additional_requirements:
                        # Concatenate the requirements
                        user_prompt = f"{connection_requirements}\n\n{additional_requirements}"
                        printer.print(f"✅ Combined requirements: Connection + Additional")
                    else:
                        # Use connection requirements as-is
                        user_prompt = connection_requirements
                        printer.print(f"✅ Using connection test requirements for main application")

                else:
                    # No requirements in memory - either sink workflow or fresh source workflow
                    # Check for cached user prompt from PREVIOUS runs
                    cached_prompt = self.cache_utils.check_cached_user_prompt()
                    if cached_prompt:
                        # Extract the actual prompt from the cached file (skip header comments)
                        prompt_lines = cached_prompt.split('\n')
                        actual_prompt_lines = []
                        skip_comments = True
                        for line in prompt_lines:
                            if skip_comments and line.strip() and not line.strip().startswith('#'):
                                skip_comments = False
                            if not skip_comments:
                                actual_prompt_lines.append(line)
                        actual_prompt = '\n'.join(actual_prompt_lines).strip()

                        if self.cache_utils.use_cached_user_prompt(actual_prompt):
                            user_prompt = actual_prompt
                        else:
                            # User wants to enter fresh requirements
                            from workflow_tools.common import clear_screen
                            clear_screen()

                            # Standard prompt for sink or source without prior requirements
                            console = Console()
                            console.print(Panel(
                                f"[bold cyan]What kind of {workflow_type} application do you want to build?[/bold cyan]\n\n"
                                f"Please describe the {workflow_type} system and what data you want to {'[bold]send[/bold]' if workflow_type == 'sink' else '[bold]receive[/bold]'}.",
                                title=f"📝 {workflow_type.title()} Application Requirements",
                                border_style="blue"
                            ))

                            user_prompt = text(
                                f"Enter your {workflow_type} requirements:"
                            ).strip()

                            if not user_prompt:
                                printer.print("❌ No description provided. Aborting.")
                                return None, None

                            # Cache the new prompt
                            self.cache_utils.save_user_prompt_to_cache(user_prompt)
                    else:
                        # No cached prompt and no requirements in memory - fresh start
                        # Standard prompt for sink or source without prior requirements
                        console = Console()
                        console.print(Panel(
                            f"[bold cyan]What kind of {workflow_type} application do you want to build?[/bold cyan]\n\n"
                            f"Please describe the {workflow_type} system and what data you want to {'[bold]send[/bold]' if workflow_type == 'sink' else '[bold]receive[/bold]'}.",
                            title=f"📝 {workflow_type.title()} Application Requirements",
                            border_style="blue"
                        ))

                        user_prompt = text(
                            f"Enter your {workflow_type} requirements:"
                        ).strip()

                        if not user_prompt:
                            printer.print("❌ No description provided. Aborting.")
                            return None, None

                        # Cache the new prompt
                        self.cache_utils.save_user_prompt_to_cache(user_prompt)
            else:
                printer.print("\n📝 Please describe what changes you'd like:")
                user_prompt = await get_enhanced_input_async("> ")
                user_prompt = user_prompt.strip() if user_prompt else ""
                
                if not user_prompt:
                    printer.print("❌ No changes requested. Keeping current code.")
                    break
            
            # Generate code
            code, env_vars = await self.generate_code(user_prompt, app_dir, workflow_type)
            
            if not code:
                printer.print("❌ Code generation failed.")
                return None, None
            
            # Show code to user for approval
            printer.print("\n" + "=" * 60)
            printer.print("Generated Code:")
            printer.print("=" * 60)
            printer.print_code(
                code,
                language="python",
                title=f"Generated {workflow_type.title()} Application Code",
                line_numbers=True
            )
            printer.print("=" * 60)
            
            # Ask for approval
            approved = get_user_approval("Does this code look good?")
            
            if approved:
                printer.print("✅ Code approved!")
                # Cache the entire app directory (contains the updated main.py, app.yaml, requirements.txt)
                self.cache_utils.save_app_directory_to_cache(app_dir)
                return code, env_vars
            
            iteration += 1
            
            if iteration < max_iterations:
                printer.print(f"\n🔄 Let's refine the code (iteration {iteration + 1}/{max_iterations})")
            else:
                printer.print(f"\n⚠️ Reached maximum iterations ({max_iterations})")
                retry = get_user_approval("Would you like to continue refining?")
                if retry:
                    iteration = 0  # Reset counter
                else:
                    return None, None
        
        return None, None
    
    async def generate_code_for_connection_test(
        self, 
        user_prompt: str, 
        app_dir: str, 
        workflow_type: str
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Generate code specifically for connection testing.
        
        This method handles the special prompt formatting needed for connection tests,
        where we need to test connecting to an external system before integrating with Quix.
        
        Args:
            user_prompt: User's description of what to test (e.g., "Test connection to PostgreSQL")
            app_dir: Directory containing the starter app code
            workflow_type: Either "sink" or "source"
            
        Returns:
            Tuple of (generated_code, env_vars_dict) or (None, None) if failed
        """
        from workflow_tools.core.prompt_manager import load_task_prompt
        from workflow_tools.common import printer
        
        printer.print(f"\n🤖 Starting Claude Code for {workflow_type} connection test...")
        
        # Get the main workflow directory (where main.py is)
        main_workflow_dir = os.getcwd()
        # Calculate relative path from main workflow dir to app dir
        relative_app_path = os.path.relpath(app_dir, main_workflow_dir)
        
        # Load the connection test prompt template
        connection_test_prompt = load_task_prompt(
            "claude_code_source_connection_test",
            user_prompt=user_prompt,
            app_path=relative_app_path
        )
        
        # Load system prompt for connection testing
        system_prompt = f"""You are helping to create a Quix {workflow_type} application. The user has already set up a starter template and wants you to modify it to test the connection to an external system.

IMPORTANT: You are working from the main workflow directory. The application files are located in: {relative_app_path}
Always read and write files using the full relative path from your current directory (e.g., {relative_app_path}/main.py, {relative_app_path}/requirements.txt, etc.)

This is a connection test only - do NOT integrate with Quix Streams or Kafka yet. Just test that we can connect to and read from the external system."""
        
        printer.print(f"   Main workflow directory: {main_workflow_dir}")
        printer.print(f"   App directory (absolute): {app_dir}")
        printer.print(f"   App directory (relative): {relative_app_path}")
        
        # Ensure Claude CLI is in PATH
        if self.claude_cli_path:
            current_path = os.environ.get("PATH", "")
            if self.claude_cli_path not in current_path:
                path_separator = ";" if platform.system() == "Windows" else ":"
                os.environ["PATH"] = f"{self.claude_cli_path}{path_separator}{current_path}"
        
        # Configure Claude Code options
        options = ClaudeCodeOptions(
            allowed_tools=self.claude_config.get("allowed_tools", ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]),
            permission_mode=self.claude_config.get("permission_mode", "acceptEdits"),
            cwd=main_workflow_dir,
            system_prompt=system_prompt,
            max_turns=self.claude_config.get("max_turns", 10),
            model=self.claude_config.get("model", "sonnet-4.1")
        )
        
        # Print prompts for debugging
        printer.print_debug("\n" + "=" * 80)
        printer.print_debug("🔍 CLAUDE CODE PROMPTS - CONNECTION TEST")
        printer.print_debug("=" * 80)
        
        printer.print_debug(f"\n📋 SYSTEM PROMPT:")
        printer.print_debug("-" * 40)
        printer.print_debug(system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt)
        printer.print_debug("-" * 40)
        
        printer.print_debug(f"\n📝 USER PROMPT:")
        printer.print_debug("-" * 40)
        printer.print_debug(connection_test_prompt[:500] + "..." if len(connection_test_prompt) > 500 else connection_test_prompt)
        printer.print_debug("-" * 40)
        printer.print_debug("=" * 80 + "\n")
        
        # Track the conversation
        full_response = []
        code_content = None
        total_cost = 0.0
        
        try:
            printer.print("\n📝 Claude Code is working on your connection test...")
            if self.enable_interruption:
                printer.print("   💡 Press Ctrl+I to interrupt and add guidance")
            printer.print("=" * 60)

            async for message in self._query_with_balance_retry(connection_test_prompt, options, "connection test generation", enable_interruption=self.enable_interruption):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            printer.print(f"Claude: {block.text}")
                            full_response.append(block.text)
                        elif isinstance(block, ThinkingBlock):
                            # Log Claude's internal thinking (in debug mode)
                            if self.debug_mode:
                                printer.print_debug(f"   💭 Thinking: {block.thinking[:200]}..." if len(block.thinking) > 200 else f"   💭 Thinking: {block.thinking}")
                        elif isinstance(block, ToolUseBlock):
                            if self.debug_mode:
                                printer.print(f"   🔧 Using tool: {block.name}")
                
                elif isinstance(message, ResultMessage):
                    if message.total_cost_usd > 0:
                        total_cost = message.total_cost_usd
            
            printer.print("=" * 60)
            printer.print(f"✅ Claude Code completed (Cost: ${total_cost:.4f})")
            
            # Read the modified main.py
            main_py_path = os.path.join(app_dir, "main.py")
            if os.path.exists(main_py_path):
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    code_content = f.read()
                printer.print("✅ Successfully read updated main.py")
            else:
                printer.print("❌ Error: main.py not found after generation")
                return None, None
            
            # Read the updated app.yaml to get environment variables
            env_vars = self._read_app_yaml_env_vars(app_dir)
            
            return code_content, env_vars
            
        except Exception as e:
            printer.print(f"❌ Error during Claude Code connection test generation: {str(e)}")
            if self.debug_mode:
                import traceback
                printer.print(traceback.format_exc())
            return None, None