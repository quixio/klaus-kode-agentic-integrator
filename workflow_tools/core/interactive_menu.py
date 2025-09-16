"""Interactive menu selection with arrow key navigation support."""

import sys
import os
from typing import List, Optional, Tuple, Any, Dict
from workflow_tools.common import printer
from workflow_tools.core.questionary_utils import text

# Check if we can use arrow keys (requires terminal that supports it)
try:
    import termios
    import tty
    ARROW_KEYS_AVAILABLE = True
except ImportError:
    ARROW_KEYS_AVAILABLE = False

# Windows support
if os.name == 'nt':
    try:
        import msvcrt
        ARROW_KEYS_AVAILABLE = True
    except ImportError:
        pass


class InteractiveMenu:
    """Interactive menu with arrow key navigation for better UX."""
    
    def __init__(self, title: str = "", show_instructions: bool = True, page_size: int = 15, header_content: str = ""):
        """Initialize the interactive menu.
        
        Args:
            title: Optional title to display above the menu
            show_instructions: Whether to show navigation instructions
            page_size: Number of items to show per page (default 15)
            header_content: Optional header content to display above the menu (preserved on updates)
        """
        self.title = title
        self.show_instructions = show_instructions
        self.current_index = 0
        self.first_display = True
        self.page_size = page_size
        self.current_page = 0
        self.header_content = header_content
    
    @classmethod
    def clear_terminal(cls):
        """Clear the terminal screen."""
        if os.name == 'posix':
            os.system('clear')
        elif os.name == 'nt':
            os.system('cls')
    
    def display_menu(self, options: List[str], selected_index: int = 0, clear_screen: bool = False, 
                     total_items: int = None, current_page: int = 0, total_pages: int = 1) -> None:
        """Display the menu with the current selection highlighted.
        
        Args:
            options: List of menu options to display (current page only)
            selected_index: Currently selected index within the current page
            clear_screen: Whether to clear screen before displaying
            total_items: Total number of items across all pages
            current_page: Current page number (0-indexed)
            total_pages: Total number of pages
        """
        # Always clear screen when updating menu to avoid jumping issues
        if not self.first_display or clear_screen:
            self.clear_terminal()
        
        # Mark that we've displayed at least once
        self.first_display = False
        
        # Display header content if provided (this will be preserved on every redraw)
        if self.header_content:
            printer.print(self.header_content)
        
        # Display title if provided
        if self.title:
            printer.print(f"\n{self.title}")
            printer.print("-" * len(self.title))
        
        # Display pagination info if there are multiple pages
        if total_pages > 1:
            printer.print(f"Page {current_page + 1} of {total_pages} (showing items {current_page * self.page_size + 1}-{min((current_page + 1) * self.page_size, total_items)} of {total_items})")
            printer.print("-" * 40)
        
        # Display options with selection indicator
        for i, option in enumerate(options):
            if i == selected_index:
                # Highlight selected option with arrow and bold (if terminal supports it)
                printer.print(f"  ▶ {option}")
            else:
                printer.print(f"    {option}")
        
        # Show instructions if enabled
        if self.show_instructions:
            printer.print("\n" + "-" * 40)
            if ARROW_KEYS_AVAILABLE:
                printer.print("Use ↑/↓ arrow keys to navigate, Enter to select")
                if total_pages > 1:
                    printer.print("Use ←/→ arrow keys to change pages")
                printer.print("Or type the number and press Enter")
            else:
                printer.print("Type the number and press Enter to select")
                if total_pages > 1:
                    printer.print("Type 'n' for next page, 'p' for previous page")
            printer.print("Press 'q' to quit")
    
    def get_key_press(self) -> str:
        """Get a single key press from the user.
        
        Returns:
            The pressed key as a string
        """
        if os.name == 'nt':  # Windows
            if ARROW_KEYS_AVAILABLE:
                key = msvcrt.getch()
                if key in [b'\xe0', b'\x00']:  # Special keys (arrows, function keys, etc.)
                    key = msvcrt.getch()
                    if key == b'H':  # Up arrow
                        return 'UP'
                    elif key == b'P':  # Down arrow
                        return 'DOWN'
                    elif key == b'K':  # Left arrow
                        return 'LEFT'
                    elif key == b'M':  # Right arrow
                        return 'RIGHT'
                return key.decode('utf-8', errors='ignore')
            else:
                # Fallback to questionary when arrow keys unavailable
                return text("Enter selection: ").strip()
        else:  # Unix/Linux/Mac
            if ARROW_KEYS_AVAILABLE:
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setraw(sys.stdin.fileno())
                    key = sys.stdin.read(1)
                    if key == '\x1b':  # ESC sequence
                        key = sys.stdin.read(2)
                        if key == '[A':  # Up arrow
                            return 'UP'
                        elif key == '[B':  # Down arrow
                            return 'DOWN'
                        elif key == '[C':  # Right arrow
                            return 'RIGHT'
                        elif key == '[D':  # Left arrow
                            return 'LEFT'
                    return key
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            else:
                # Fallback to questionary when arrow keys unavailable
                return text("Enter selection: ").strip()
    
    def select_option(
        self, 
        options: List[Any], 
        display_formatter: Optional[callable] = None,
        allow_back: bool = True,
        back_text: str = "⬅️ Go back",
        clear_screen: bool = False
    ) -> Tuple[Optional[Any], int]:
        """Show interactive menu and get user selection.
        
        Args:
            options: List of options (can be strings, dicts, or any objects)
            display_formatter: Optional function to format option for display
            allow_back: Whether to show a "Go back" option
            back_text: Text for the back option
            clear_screen: Whether to clear screen on each update
            
        Returns:
            Tuple of (selected_option, selected_index) or (None, -1) for back/quit
        """
        if not options:
            printer.print("❌ No options available.")
            return None, -1
        
        # Format options for display
        if display_formatter:
            display_options = [display_formatter(opt) for opt in options]
        else:
            display_options = [str(opt) for opt in options]
        
        # Add back option if enabled
        if allow_back:
            display_options.append(back_text)
            
        # Calculate pagination
        total_items = len(display_options)
        total_pages = (total_items + self.page_size - 1) // self.page_size
        self.current_page = 0
        self.current_index = 0
        
        # Interactive mode with arrow keys and pagination
        while True:
            # Get current page items
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, total_items)
            page_options = display_options[start_idx:end_idx]
            
            # Add index numbers to current page options
            numbered_page_options = [f"{start_idx + i + 1}. {opt}" for i, opt in enumerate(page_options)]
            
            # Display the current page
            self.display_menu(
                numbered_page_options, 
                self.current_index, 
                clear_screen,
                total_items=total_items,
                current_page=self.current_page,
                total_pages=total_pages
            )
            
            key = self.get_key_press()
            
            if key == 'UP':
                if self.current_index > 0:
                    self.current_index -= 1
                else:
                    # Wrap to bottom of current page
                    self.current_index = len(page_options) - 1
            elif key == 'DOWN':
                if self.current_index < len(page_options) - 1:
                    self.current_index += 1
                else:
                    # Wrap to top of current page
                    self.current_index = 0
            elif key == 'LEFT':
                # Previous page
                if self.current_page > 0:
                    self.current_page -= 1
                    self.current_index = 0  # Reset to first item of new page
            elif key == 'RIGHT':
                # Next page
                if self.current_page < total_pages - 1:
                    self.current_page += 1
                    self.current_index = 0  # Reset to first item of new page
            elif key in ['\r', '\n']:  # Enter key
                # Calculate actual index in full list
                actual_index = start_idx + self.current_index
                if allow_back and actual_index == len(options):
                    return None, -1  # Back option selected
                if actual_index < len(options):
                    return options[actual_index], actual_index
            elif key.lower() == 'q':
                return None, -1
            elif key.lower() == 'n' and not ARROW_KEYS_AVAILABLE:
                # Next page for non-arrow key mode
                if self.current_page < total_pages - 1:
                    self.current_page += 1
                    self.current_index = 0
            elif key.lower() == 'p' and not ARROW_KEYS_AVAILABLE:
                # Previous page for non-arrow key mode
                if self.current_page > 0:
                    self.current_page -= 1
                    self.current_index = 0
            elif key.isdigit():
                # Allow direct number input (across all pages)
                full_index = int(key) - 1
                # Check if we need multi-digit input
                if len(key) == 1 and total_items >= 10:
                    # Try to read more digits
                    extra_key = self.get_key_press()
                    if extra_key.isdigit():
                        full_index = int(key + extra_key) - 1
                        # Could read one more for 3-digit numbers if needed
                        if total_items >= 100:
                            extra_key2 = self.get_key_press()
                            if extra_key2.isdigit():
                                full_index = int(key + extra_key + extra_key2) - 1
                
                if 0 <= full_index < total_items:
                    # Jump to the page containing this item
                    self.current_page = full_index // self.page_size
                    self.current_index = full_index % self.page_size
                    # Select it immediately
                    if allow_back and full_index == len(options):
                        return None, -1
                    if full_index < len(options):
                        return options[full_index], full_index
    
    @staticmethod
    def select_from_dataframe(
        df,
        title: str = "",
        value_column: str = None,
        display_columns: List[str] = None,
        allow_back: bool = True,
        page_size: int = 15
    ) -> Tuple[Optional[Any], int]:
        """Select from a pandas DataFrame with interactive menu.
        
        Args:
            df: Pandas DataFrame with options
            title: Menu title
            value_column: Column to return as the selected value
            display_columns: Columns to show in the display
            allow_back: Whether to show a "Go back" option
            page_size: Number of items per page
            
        Returns:
            Tuple of (selected_value, selected_index) or (None, -1) for back/quit
        """
        if df.empty:
            printer.print("❌ No data available.")
            return None, -1
        
        # Create display formatter
        def format_row(row):
            if display_columns:
                parts = [str(row[col]) for col in display_columns if col in row]
            else:
                # Use all columns except Index if present
                cols = [c for c in df.columns if c != 'Index']
                parts = [f"{col}: {row[col]}" for col in cols]
            return " | ".join(parts)
        
        # Convert dataframe rows to list of dicts
        options = df.to_dict('records')
        
        menu = InteractiveMenu(title=title, page_size=page_size)
        selected, index = menu.select_option(
            options, 
            display_formatter=format_row,
            allow_back=allow_back
        )
        
        if selected and value_column:
            return selected.get(value_column), index
        return selected, index


def create_simple_menu(
    options: List[str],
    title: str = "",
    allow_back: bool = True,
    page_size: int = 15
) -> Tuple[Optional[str], int]:
    """Convenience function for simple string menus.
    
    Args:
        options: List of string options
        title: Menu title
        allow_back: Whether to show a "Go back" option
        page_size: Number of items per page
        
    Returns:
        Tuple of (selected_option, selected_index) or (None, -1) for back/quit
    """
    menu = InteractiveMenu(title=title, page_size=page_size)
    return menu.select_option(options, allow_back=allow_back)