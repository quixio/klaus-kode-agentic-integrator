# common.py - Shared utilities for the workflow

import os
import re
import json
import random
import string
import logging
import sys
import signal
import atexit
import ast
import getpass
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Enable nested event loops to allow questionary to work in async contexts
import nest_asyncio
nest_asyncio.apply()

# Rich imports for syntax highlighting and formatting
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.rule import Rule
from rich.markdown import Markdown

# --- Logging Setup ---
def setup_logging() -> logging.Logger:
    """Set up logging to both console and timestamped file."""
    # Create logging directory if it doesn't exist
    os.makedirs("logging", exist_ok=True)
    
    # Create timestamped log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logging/workflow_{timestamp}.log"
    
    # Create logger
    logger = logging.getLogger("workflow")
    logger.setLevel(logging.INFO)
    
    # Suppress verbose logging from external libraries in non-verbose mode
    verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
    if not verbose_mode:
        # Suppress OpenAI HTTP trace logs
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        # Suppress other noisy libraries
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("agents").setLevel(logging.WARNING)
    
    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(message)s')
    
    # File handler - detailed logging with immediate flushing
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)
    
    # Force immediate flushing to ensure logs are written even if process is interrupted
    class FlushingFileHandler(logging.FileHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()  # Force flush after each log entry
    
    # Replace the standard FileHandler with our flushing version
    file_handler = FlushingFileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Console handler - adjust based on verbose mode
    console_handler = logging.StreamHandler(sys.stdout)
    if verbose_mode:
        # In verbose mode, show INFO and above with timestamps
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(detailed_formatter)
    else:
        # In non-verbose mode, only show critical errors (not regular errors)
        console_handler.setLevel(logging.CRITICAL)
        console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Set up signal handling to ensure logs are flushed on interruption
    def flush_logs():
        """Flush all log handlers to ensure logs are written to disk."""
        for handler in logger.handlers:
            handler.flush()
    
    def signal_handler(signum, frame):
        """Handle signals (like Ctrl+C) to flush logs before exit."""
        flush_logs()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    # Register cleanup function to run on normal exit
    atexit.register(flush_logs)
    
    return logger

# Global logger instance
workflow_logger = setup_logging()

class WorkflowPrinter:
    """Custom printer that logs to file and prints to console without duplication."""
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        # Check if verbose mode is enabled
        self.verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
        # Find the file handler to log to file only
        self.file_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                self.file_handler = handler
                break
    
    def print(self, message: str = "", end: str = "\n"):
        """Print message to console and log to file."""
        # Print to console directly
        print(message, end=end)

        # Log to file only if we have a file handler
        if self.file_handler:
            safe_message = self._sanitize_for_logging(message)
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=safe_message,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)

    def print_markup(self, message: str = "", end: str = "\n"):
        """Print message with Rich markup support to console and log to file."""
        console = Console()
        # Use Rich console to print with markup support
        console.print(message, end=end)

        # Log to file only if we have a file handler (strip markup for log)
        if self.file_handler:
            # Create Text object to strip markup
            text_obj = Text.from_markup(message)
            plain_text = text_obj.plain
            safe_message = self._sanitize_for_logging(plain_text)
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=safe_message,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)
    
    def _sanitize_for_logging(self, text: str) -> str:
        """Sanitize text to prevent Unicode encoding errors in logging."""
        try:
            # Try to encode/decode to catch any encoding issues
            sanitized = text.encode('utf-8', errors='replace').decode('utf-8')
            return sanitized
        except Exception:
            # If all else fails, return a safe representation
            return repr(text)

    def input(self, prompt: str) -> str:
        """Get user input and log both prompt and response."""
        from workflow_tools.core.enhanced_input import get_enhanced_input
        
        # Log the prompt to file only
        if self.file_handler:
            safe_prompt = self._sanitize_for_logging(prompt)
            prompt_record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"PROMPT: {safe_prompt}",
                args=(),
                exc_info=None
            )
            self.file_handler.emit(prompt_record)
        
        try:
            response = get_enhanced_input(prompt=prompt)
            # Sanitize the actual response to prevent encoding issues downstream
            clean_response = response.encode('utf-8', errors='replace').decode('utf-8')
            
            # Log the response to file only
            if self.file_handler:
                safe_response = self._sanitize_for_logging(clean_response)
                response_record = logging.LogRecord(
                    name=self.logger.name,
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"USER INPUT: {safe_response}",
                    args=(),
                    exc_info=None
                )
                self.file_handler.emit(response_record)
            return clean_response
        except (EOFError, KeyboardInterrupt):
            # Log the interruption to file only
            if self.file_handler:
                interrupt_record = logging.LogRecord(
                    name=self.logger.name,
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg="USER INPUT: [Interrupted]",
                    args=(),
                    exc_info=None
                )
                self.file_handler.emit(interrupt_record)
            raise
    
    def secure_input(self, prompt: str) -> str:
        """Get secure user input without displaying characters (for passwords/secrets).
        
        Args:
            prompt: Input prompt to display
            
        Returns:
            User input string (without trailing newline)
        """
        # Log the prompt to file only
        if self.file_handler:
            safe_prompt = self._sanitize_for_logging(prompt)
            prompt_record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"SECURE PROMPT: {safe_prompt}",
                args=(),
                exc_info=None
            )
            self.file_handler.emit(prompt_record)
        
        try:
            # Use questionary password field to hide input characters
            from workflow_tools.core.questionary_utils import password
            response = password(prompt)
            # Sanitize the actual response to prevent encoding issues downstream
            clean_response = response.encode('utf-8', errors='replace').decode('utf-8')
            
            # Log that a secure input was received (but NOT the actual value)
            if self.file_handler:
                response_record = logging.LogRecord(
                    name=self.logger.name,
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"SECURE INPUT: [REDACTED - {len(clean_response)} characters]",
                    args=(),
                    exc_info=None
                )
                self.file_handler.emit(response_record)
            return clean_response
        except (EOFError, KeyboardInterrupt):
            # Log the interruption to file only
            if self.file_handler:
                interrupt_record = logging.LogRecord(
                    name=self.logger.name,
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg="SECURE INPUT: [Interrupted]",
                    args=(),
                    exc_info=None
                )
                self.file_handler.emit(interrupt_record)
            raise
    
    def print_code(self, code: str, language: str = "python", title: Optional[str] = None, 
                   line_numbers: bool = False, theme: str = "monokai"):
        """Print code with syntax highlighting using Rich.
        
        Args:
            code: The code to display
            language: Programming language for syntax highlighting (default: "python")
            title: Optional title for the code block
            line_numbers: Whether to show line numbers (default: False)
            theme: Color theme for syntax highlighting (default: "monokai")
        """
        # Create a console instance
        console = Console()
        
        # Create syntax object with the code
        syntax = Syntax(
            code,
            language,
            theme=theme,
            line_numbers=line_numbers,
            word_wrap=True
        )
        
        # If a title is provided, wrap in a panel
        if title:
            panel = Panel(syntax, title=title, border_style="blue")
            console.print(panel)
        else:
            console.print(syntax)
        
        # Also log to file (without colors)
        if self.file_handler:
            safe_code = self._sanitize_for_logging(code)
            log_msg = f"Code block ({language}):\n{safe_code}"
            if title:
                log_msg = f"{title}\n{log_msg}"
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=log_msg,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)
    
    def print_markdown(self, markdown_text: str, title: Optional[str] = None):
        """Print markdown content with Rich formatting.
        
        Args:
            markdown_text: The markdown text to display
            title: Optional title for the markdown block
        """
        console = Console()
        
        # Create markdown object
        md = Markdown(markdown_text)
        
        # If a title is provided, wrap in a panel
        if title:
            panel = Panel(md, title=title, border_style="cyan", padding=(1, 2))
            console.print(panel)
        else:
            console.print(md)
        
        # Also log to file (without colors)
        if self.file_handler:
            safe_text = self._sanitize_for_logging(markdown_text)
            log_msg = f"Markdown content:\n{safe_text}"
            if title:
                log_msg = f"{title}\n{log_msg}"
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=log_msg,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)
    
    def print_verbose(self, message: str = "", end: str = "\n"):
        """Print message only in verbose mode. Always logs to file."""
        # Log to file regardless of verbose mode
        if self.file_handler:
            safe_message = self._sanitize_for_logging(message)
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.DEBUG,
                pathname="",
                lineno=0,
                msg=safe_message,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)
        
        # Only print to console in verbose mode
        if self.verbose_mode:
            print(message, end=end)
    
    def print_debug(self, message: str = "", end: str = "\n"):
        """Print debug information only in verbose mode."""
        if self.verbose_mode:
            print(f"[DEBUG] {message}", end=end)
        
        # Always log debug messages to file
        if self.file_handler:
            safe_message = self._sanitize_for_logging(f"[DEBUG] {message}")
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.DEBUG,
                pathname="",
                lineno=0,
                msg=safe_message,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)
    
    def print_cache_panel(self, title: str, cache_file: str, content_dict: dict, 
                         border_style: str = "cyan", title_style: str = "bold cyan"):
        """Print a beautiful cache panel using Rich.
        
        Args:
            title: Title for the cache panel (e.g., "Cached Sink Prerequisites")
            cache_file: Path to the cache file
            content_dict: Dictionary of key-value pairs to display
            border_style: Rich style for the panel border
            title_style: Rich style for the title
        """
        console = Console()
        
        # Create a table for the cache content
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Key", style="bold yellow", no_wrap=True)
        table.add_column("Value", style="white")
        
        # Add cache file path as first row
        table.add_row("📁 Cache File", cache_file)
        table.add_row("", "")  # Empty row for spacing
        
        # Add all content items
        for key, value in content_dict.items():
            # Format the key nicely
            formatted_key = key.replace('_', ' ').title()
            table.add_row(f"▸ {formatted_key}", str(value))
        
        # Create the panel with the table
        panel = Panel(
            table,
            title=f"✨ {title} ✨",
            border_style=border_style,
            padding=(1, 2),
            expand=False
        )
        
        console.print(panel)
        
        # Also log to file (without colors)
        if self.file_handler:
            log_lines = [f"--- {title} ---", f"Cache file: {cache_file}"]
            for key, value in content_dict.items():
                log_lines.append(f"{key}: {value}")
            log_lines.append("---")
            
            safe_text = self._sanitize_for_logging('\n'.join(log_lines))
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=safe_text,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)
    
    def print_phase_header(self, phase_name: str, icon: str = "🚀", 
                          border_style: str = "bold cyan", width: int = 80):
        """Print a beautiful phase header using Rich.
        
        Args:
            phase_name: Name of the phase being started
            icon: Icon to display (default: rocket)
            border_style: Rich style for the panel border
            width: Width of the panel
        """
        console = Console()
        
        # Create centered text for the phase name
        phase_text = Text(f"{icon} {phase_name} {icon}", style="bold white")
        centered_text = Align.center(phase_text)
        
        # Create the panel
        panel = Panel(
            centered_text,
            title="[bold yellow]◆ PHASE START ◆[/bold yellow]",
            border_style=border_style,
            padding=(1, 2),
            width=width,
            expand=False
        )
        
        console.print("\n")
        console.print(panel)
        console.print("")
        
        # Also log to file (without colors)
        if self.file_handler:
            safe_text = self._sanitize_for_logging(f"\n{'='*50}\nStarting {phase_name}\n{'='*50}\n")
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=safe_text,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)
    
    def print_section_header(self, title: str, subtitle: str = None, 
                           icon: str = "📋", style: str = "cyan"):
        """Print a beautiful section header using Rich.
        
        Args:
            title: Main section title
            subtitle: Optional subtitle
            icon: Icon to display
            style: Rich color style
        """
        console = Console()
        
        # Create the title text
        if subtitle:
            content = Text()
            content.append(f"{icon} {title}\n", style=f"bold {style}")
            content.append(subtitle, style=f"dim {style}")
            aligned_content = Align.center(content)
        else:
            content = Text(f"{icon} {title}", style=f"bold {style}")
            aligned_content = Align.center(content)
        
        # Create a lighter panel for sections
        panel = Panel(
            aligned_content,
            border_style=style,
            padding=(0, 2),
            expand=False
        )
        
        console.print(panel)
        
        # Also log to file
        if self.file_handler:
            log_text = f"\n--- {title} ---"
            if subtitle:
                log_text += f"\n{subtitle}"
            safe_text = self._sanitize_for_logging(log_text)
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=safe_text,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)
    
    def print_spaced(self, message: str, spacing_before: int = 1, spacing_after: int = 0):
        """Print a message with configurable spacing before and after.
        
        Args:
            message: The message to print
            spacing_before: Number of blank lines before message (default: 1)
            spacing_after: Number of blank lines after message (default: 0)
        """
        for _ in range(spacing_before):
            self.print("")
        self.print(message)
        for _ in range(spacing_after):
            self.print("")
    
    def print_divider(self, style: str = "dim cyan", width: int = 80):
        """Print a beautiful divider line using Rich.
        
        Args:
            style: Rich style for the divider
            width: Width of the divider
        """
        console = Console()
        console.print(Rule(style=style, characters="─"))
        
        # Also log to file
        if self.file_handler:
            safe_text = self._sanitize_for_logging("-" * 50)
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.DEBUG,
                pathname="",
                lineno=0,
                msg=safe_text,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)
    
    def print_markdown_preview(self, content: str, max_length: int = 500, 
                              title: str = "Content Preview", style: str = "dim"):
        """Display a preview of markdown content in a formatted panel.
        
        Args:
            content: The markdown content to preview
            max_length: Maximum characters to show
            title: Title for the preview panel
            style: Rich style for the panel
        """
        console = Console()
        
        # Truncate content if needed
        if len(content) > max_length:
            preview = content[:max_length]
            truncated = True
        else:
            preview = content
            truncated = False
        
        # Parse the markdown content
        md = Markdown(preview)
        
        # Create a panel for the preview
        panel = Panel(
            md,
            title=f"[bold]{title}[/bold]",
            border_style=style,
            padding=(1, 2),
            expand=False
        )
        
        console.print(panel)
        
        if truncated:
            console.print(f"[dim]... (showing first {max_length} characters of {len(content)} total)[/dim]")
        
        # Also log to file
        if self.file_handler:
            safe_text = self._sanitize_for_logging(f"{title}:\n{preview}")
            if truncated:
                safe_text += f"\n... (truncated from {len(content)} characters)"
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=safe_text,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)

# Global printer instance
printer = WorkflowPrinter(workflow_logger)

# --- Workflow Context ---
# Import the refactored WorkflowContext from contexts.py
from .contexts import WorkflowContext

# --- Common Utility Functions ---
def extract_json_from_llm_output(llm_output: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from LLM output that might be wrapped in markdown."""
    try:
        match = re.search(r'```json\s*(\{.*?\})\s*```', llm_output, re.DOTALL)
        if match: return json.loads(match.group(1))
        match = re.search(r'(\{.*?\})', llm_output, re.DOTALL)
        if match: return json.loads(match.group(1))
        if llm_output.strip().startswith('{'): return json.loads(llm_output)
        return None
    except (json.JSONDecodeError, IndexError):
        return None

def extract_python_code_from_llm_output(llm_output: str) -> str:
    """Extract raw Python code from a string that might be wrapped in markdown.
    
    This function attempts to extract Python code from AI responses, handling
    various formatting issues that may occur.
    """
    # First, try to find all code blocks (there might be multiple)
    code_blocks = re.findall(r'```(?:python)?\s*\n(.*?)\n```', llm_output, re.DOTALL)
    
    # If we found code blocks, validate and return the first valid Python code
    for code_block in code_blocks:
        code = code_block.strip()
        # Try to parse it as valid Python
        try:
            ast.parse(code)
            return code  # Return the first valid Python code block
        except SyntaxError:
            continue  # Try the next code block
    
    # If no valid code blocks found, try to extract code without markdown
    # Look for DEPENDENCIES comments or import statements as a sign of Python code starting
    code_start_match = re.search(r'^(#\s*DEPENDENCIES:|import\s+\S+|from\s+\S+\s+import)', llm_output, re.MULTILINE)
    if code_start_match:
        # Find where the code likely starts
        code_start = code_start_match.start()
        potential_code = llm_output[code_start:].strip()
        
        # Try to find where code ends (look for non-code indicators)
        end_markers = [
            '\n\n##',  # Markdown headers
            '\n\nThis code',  # Explanatory text
            '\n\nThe above',  # Explanatory text
            '\n\nHere\'s',  # Explanatory text
            '\n\nNote:',  # Notes
            '\n\n---',  # Markdown separator
        ]
        
        for marker in end_markers:
            marker_pos = potential_code.find(marker)
            if marker_pos > 0:
                potential_code = potential_code[:marker_pos].strip()
                break
        
        # Validate it's Python code
        try:
            ast.parse(potential_code)
            return potential_code
        except SyntaxError:
            pass
    
    # Last resort: return the original output stripped
    # The calling code should validate syntax
    return llm_output.strip()

def sanitize_name(name: str) -> str:
    """Sanitize a name for use in file paths and identifiers."""
    sanitized = name.lower().replace(" ", "-")
    sanitized = re.sub(r'[^a-z0-9-]', '-', sanitized)
    return re.sub(r'-+', '-', sanitized).strip('-')

def generate_unique_app_name(base_name: str) -> str:
    """Generate a unique application name by adding a random suffix."""
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{base_name}-{random_suffix}"

def ensure_name_length_limit(name: str, max_length: int = 50) -> str:
    """
    Ensure a name doesn't exceed the maximum length limit.
    If it does, intelligently truncate it while preserving important parts.
    
    Args:
        name: The name to check/truncate
        max_length: Maximum allowed length (default 50 for Quix application names)
    
    Returns:
        The name, truncated if necessary to fit within the limit
    """
    if len(name) <= max_length:
        return name
    
    # For names with suffixes like "-draft", "-source", "-sink", preserve them
    important_suffixes = ['-draft', '-source', '-sink', '-test', '-sandbox']
    suffix = ''
    for s in important_suffixes:
        if name.endswith(s):
            suffix = s
            name = name[:-len(s)]
            break
    
    # Calculate how much we need to truncate
    available_length = max_length - len(suffix)
    
    # If the name has multiple parts separated by hyphens, try to shorten intelligently
    parts = name.split('-')
    if len(parts) > 1:
        # Keep first and last parts if possible, truncate middle parts
        if len(parts[0]) + len(parts[-1]) + len(suffix) + 2 < max_length:
            # We can keep first and last parts
            remaining_length = available_length - len(parts[0]) - len(parts[-1]) - 1
            middle_parts = '-'.join(parts[1:-1])
            if remaining_length > 0 and middle_parts:
                middle_parts = middle_parts[:remaining_length - 1]
                truncated = f"{parts[0]}-{middle_parts}-{parts[-1]}"
            else:
                truncated = f"{parts[0]}-{parts[-1]}"
        else:
            # Even first and last parts are too long, just truncate from the end
            truncated = name[:available_length]
    else:
        # Simple truncation for single-part names
        truncated = name[:available_length]
    
    # Remove any trailing hyphens from truncation
    truncated = truncated.rstrip('-')
    
    # Add back the suffix
    result = truncated + suffix
    
    # Final safety check
    if len(result) > max_length:
        result = result[:max_length]
    
    return result

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')

def get_user_approval(prompt: str, clear_before: bool = False, default: str = 'yes') -> bool:
    """Get user approval for an action.
    
    Uses questionary select for arrow key navigation.
    
    Args:
        prompt: The prompt to display to the user
        clear_before: Whether to clear screen before showing prompt
        default: Default selection ('yes' or 'no'), defaults to 'yes' for better UX
    """
    from workflow_tools.core.questionary_utils import select_yes_no
    
    if clear_before:
        clear_screen()
    
    # Add "ACTION REQUIRED:" prefix for consistency
    full_prompt = f"ACTION REQUIRED: {prompt}"
    
    response = select_yes_no(full_prompt, default=default, show_border=True)
    return response == 'yes'

def get_user_approval_with_back(prompt: str, allow_back: bool = True, clear_before: bool = False) -> str:
    """Get user approval for an action with optional 'go back' support.
    
    Uses questionary select for arrow key navigation instead of text input.
    
    Args:
        prompt: The prompt to display to the user
        allow_back: Whether to allow 'go back' option
        clear_before: Whether to clear screen before showing prompt
        
    Returns:
        'yes', 'no', or 'back'
    """
    from workflow_tools.core.questionary_utils import select_yes_no_back, select_yes_no
    
    if clear_before:
        clear_screen()
    
    # Add "ACTION REQUIRED:" prefix for consistency
    full_prompt = f"ACTION REQUIRED: {prompt}"
    
    if allow_back:
        return select_yes_no_back(full_prompt, show_border=True)
    else:
        result = select_yes_no(full_prompt, show_border=True)
        return result  # Returns 'yes' or 'no'


async def run_agent_with_retry(agent_runner_func, max_retries: int = 3, delay_seconds: float = 2.0):
    """
    Run an agent with retry logic for handling API failures.
    
    Args:
        agent_runner_func: Async function that returns the agent result
        max_retries: Maximum number of retry attempts (default: 3)
        delay_seconds: Delay between retries in seconds (default: 2.0)
    
    Returns:
        Agent result on success, None on failure
    """
    import asyncio
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await agent_runner_func()
        
        except Exception as e:
            last_exception = e
            error_str = str(e).lower()
            
            # Check if it's a retryable error (network, API rate limits, server issues)
            retryable_errors = [
                'server disconnected',
                'connection reset',
                'timeout',
                'rate limit',
                'internal server error',
                'service unavailable',
                'bad gateway',
                'gateway timeout',
                'anthropicexception',
                'openaiexception'
            ]
            
            is_retryable = any(retry_pattern in error_str for retry_pattern in retryable_errors)
            
            if not is_retryable or attempt >= max_retries:
                # Don't retry on non-retryable errors or if we've exhausted retries
                printer.print(f"❌ AI Agent Error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                if attempt >= max_retries:
                    printer.print(f"🛑 Max retries ({max_retries}) exhausted for AI agent call")
                break
            
            # Retryable error - wait and try again
            printer.print(f"⚠️ AI Agent Error (attempt {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                wait_time = delay_seconds * (2 ** attempt)  # Exponential backoff
                printer.print(f"🔄 Retrying in {wait_time:.1f} seconds.")
                await asyncio.sleep(wait_time)
                continue  # Go back to the top of the loop for retry
    
    # If we get here, all retries failed
    printer.print(f"❌ AI agent call failed after {max_retries + 1} attempts")
    return None