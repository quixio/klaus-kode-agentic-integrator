"""Enhanced text input with arrow key navigation and visual borders.

Uses questionary for input (with arrow key support) and rich for borders.
Properly handles both sync and async contexts.
"""

import asyncio
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import questionary
from questionary import Style


class EnhancedInput:
    """Enhanced text input with arrow keys and rich borders."""
    
    def __init__(self):
        """Initialize the enhanced input handler."""
        self.console = Console()
        
        # Define rich styles for borders
        self.prompt_style = "bold cyan"
        self.border_style = "bright_blue"
        
        # Define questionary style for input
        self.questionary_style = Style([
            ('qmark', 'fg:#00aa00 bold'),       # Question mark
            ('question', 'fg:#00aaaa bold'),    # Question text
            ('answer', 'fg:#ffffff bold'),      # User input
            ('pointer', 'fg:#00aa00 bold'),     # Pointer for selections
            ('highlighted', 'fg:#00aaaa bold'), # Highlighted selection
            ('selected', 'fg:#00aa00'),         # Selected item
            ('separator', 'fg:#666666'),        # Separator
            ('instruction', 'fg:#888888'),      # Instructions
            ('text', 'fg:#ffffff'),              # General text
        ])
    
    async def get_text_async(
        self,
        prompt_text: str = "",
        default: str = "",
        multiline: bool = False,
        suggestions: Optional[List[str]] = None,
        validator: Optional[callable] = None,
        allow_empty: bool = True,
        show_border: bool = True
    ) -> str:
        """Async version: Get text input with arrow key navigation and borders.
        
        Args:
            prompt_text: The prompt to display
            default: Default value to pre-fill
            multiline: Whether to allow multiline input
            suggestions: List of suggestions for autocomplete
            validator: Optional validation function
            allow_empty: Whether to allow empty input
            show_border: Whether to show a border around the prompt
            
        Returns:
            The user's input as a string
        """
        # Format the prompt
        if prompt_text and not prompt_text.endswith((' ', ':', '>', '?')):
            prompt_text += ":"
        
        try:
            if show_border and prompt_text:
                # Display the prompt in a nice bordered panel using rich
                prompt_panel = Panel(
                    Text(prompt_text, style=self.prompt_style),
                    border_style=self.border_style,
                    expand=False,
                    padding=(0, 1)
                )
                self.console.print(prompt_panel)
                
                # Use minimal prompt for questionary since we already showed the prompt
                prompt_for_input = "› "
            else:
                prompt_for_input = prompt_text if prompt_text else "› "
            
            # Create the questionary prompt
            if suggestions:
                question = questionary.autocomplete(
                    prompt_for_input,
                    choices=suggestions,
                    default=default if default else "",
                    style=self.questionary_style,
                    validate=lambda x: allow_empty or bool(x.strip())
                )
            else:
                question = questionary.text(
                    prompt_for_input,
                    default=default if default else "",
                    style=self.questionary_style,
                    validate=lambda x: allow_empty or bool(x.strip()),
                    multiline=multiline
                )
            
            # Use async ask
            result = await question.ask_async()
            
            # Apply custom validator if provided
            if result and validator and not validator(result):
                self.console.print("[red]Invalid input. Please try again.[/red]")
                return await self.get_text_async(
                    prompt_text=prompt_text,
                    default=default,
                    suggestions=suggestions,
                    validator=validator,
                    allow_empty=allow_empty,
                    show_border=show_border
                )
            
            return result if result is not None else (default if default else "")
            
        except (KeyboardInterrupt, EOFError):
            return default if default else ""
        
    def get_text(
        self,
        prompt_text: str = "",
        default: str = "",
        multiline: bool = False,
        suggestions: Optional[List[str]] = None,
        validator: Optional[callable] = None,
        allow_empty: bool = True,
        show_border: bool = True
    ) -> str:
        """Sync version: Get text input with arrow key navigation and borders.
        
        Automatically detects if in async context and handles appropriately.
        
        Args:
            prompt_text: The prompt to display
            default: Default value to pre-fill
            multiline: Whether to allow multiline input
            suggestions: List of suggestions for autocomplete
            validator: Optional validation function
            allow_empty: Whether to allow empty input
            show_border: Whether to show a border around the prompt
            
        Returns:
            The user's input as a string
        """
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, but being called synchronously
            # This is the problematic case - we need to use asyncio.create_task or similar
            # For now, we'll use the sync version which should work in most cases
            import nest_asyncio
            nest_asyncio.apply()  # Allow nested event loops
        except RuntimeError:
            # No async context, we're good to go
            pass
        
        # Format the prompt
        if prompt_text and not prompt_text.endswith((' ', ':', '>', '?')):
            prompt_text += ":"
        
        try:
            if show_border and prompt_text:
                # Display the prompt in a nice bordered panel using rich
                prompt_panel = Panel(
                    Text(prompt_text, style=self.prompt_style),
                    border_style=self.border_style,
                    expand=False,
                    padding=(0, 1)
                )
                self.console.print(prompt_panel)
                
                # Use minimal prompt for questionary since we already showed the prompt
                prompt_for_input = "› "
            else:
                prompt_for_input = prompt_text if prompt_text else "› "
            
            # Create the questionary prompt
            if suggestions:
                question = questionary.autocomplete(
                    prompt_for_input,
                    choices=suggestions,
                    default=default if default else "",
                    style=self.questionary_style,
                    validate=lambda x: allow_empty or bool(x.strip())
                )
            else:
                question = questionary.text(
                    prompt_for_input,
                    default=default if default else "",
                    style=self.questionary_style,
                    validate=lambda x: allow_empty or bool(x.strip()),
                    multiline=multiline
                )
            
            # Use sync ask
            result = question.ask()
            
            # Apply custom validator if provided
            if result and validator and not validator(result):
                self.console.print("[red]Invalid input. Please try again.[/red]")
                return self.get_text(
                    prompt_text=prompt_text,
                    default=default,
                    suggestions=suggestions,
                    validator=validator,
                    allow_empty=allow_empty,
                    show_border=show_border
                )
            
            return result if result is not None else (default if default else "")
            
        except (KeyboardInterrupt, EOFError):
            return default if default else ""
    
    async def get_multiline_text_async(
        self,
        prompt_text: str = "Enter text (Press Esc then Enter to finish):",
        default: str = ""
    ) -> str:
        """Async version: Get multiline text input with arrow key navigation.
        
        Args:
            prompt_text: The prompt to display
            default: Default value to pre-fill
            
        Returns:
            The user's multiline input as a string
        """
        # Display the prompt in a bordered panel
        if prompt_text:
            prompt_panel = Panel(
                Text(prompt_text, style=self.prompt_style),
                border_style=self.border_style,
                expand=False,
                padding=(0, 1)
            )
            self.console.print(prompt_panel)
        
        # Use questionary for multiline input with arrow key support
        try:
            question = questionary.text(
                "› ",
                default=default if default else "",
                style=self.questionary_style,
                multiline=True
            )
            result = await question.ask_async()
            return result if result is not None else default
            
        except (KeyboardInterrupt, EOFError):
            return default
    
    def get_multiline_text(
        self,
        prompt_text: str = "Enter text (Press Esc then Enter to finish):",
        default: str = ""
    ) -> str:
        """Sync version: Get multiline text input with arrow key navigation.
        
        Args:
            prompt_text: The prompt to display
            default: Default value to pre-fill
            
        Returns:
            The user's multiline input as a string
        """
        # Display the prompt in a bordered panel
        if prompt_text:
            prompt_panel = Panel(
                Text(prompt_text, style=self.prompt_style),
                border_style=self.border_style,
                expand=False,
                padding=(0, 1)
            )
            self.console.print(prompt_panel)
        
        # Use questionary for multiline input with arrow key support
        try:
            question = questionary.text(
                "› ",
                default=default if default else "",
                style=self.questionary_style,
                multiline=True
            )
            result = question.ask()
            return result if result is not None else default
            
        except (KeyboardInterrupt, EOFError):
            return default
    
    async def get_yes_no_async(
        self,
        prompt_text: str,
        default: Optional[bool] = None,
        show_border: bool = True
    ) -> bool:
        """Async version: Get yes/no input from user.
        
        Args:
            prompt_text: The prompt to display
            default: Default value (True for yes, False for no, None for no default)
            show_border: Whether to show a border around the prompt
            
        Returns:
            True for yes, False for no
        """
        try:
            if show_border and prompt_text:
                # Display the prompt in a bordered panel
                prompt_panel = Panel(
                    Text(prompt_text, style=self.prompt_style),
                    border_style=self.border_style,
                    expand=False,
                    padding=(0, 1)
                )
                self.console.print(prompt_panel)
                prompt_for_input = "› "
            else:
                prompt_for_input = prompt_text
            
            # Use questionary for yes/no with nice formatting
            question = questionary.confirm(
                prompt_for_input,
                default=default if default is not None else False,
                style=self.questionary_style
            )
            result = await question.ask_async()
            
            return result if result is not None else (default if default is not None else False)
            
        except (KeyboardInterrupt, EOFError):
            return default if default is not None else False
    
    def get_yes_no(
        self,
        prompt_text: str,
        default: Optional[bool] = None,
        show_border: bool = True
    ) -> bool:
        """Sync version: Get yes/no input from user.
        
        Args:
            prompt_text: The prompt to display
            default: Default value (True for yes, False for no, None for no default)
            show_border: Whether to show a border around the prompt
            
        Returns:
            True for yes, False for no
        """
        try:
            if show_border and prompt_text:
                # Display the prompt in a bordered panel
                prompt_panel = Panel(
                    Text(prompt_text, style=self.prompt_style),
                    border_style=self.border_style,
                    expand=False,
                    padding=(0, 1)
                )
                self.console.print(prompt_panel)
                prompt_for_input = "› "
            else:
                prompt_for_input = prompt_text
            
            # Use questionary for yes/no with nice formatting
            question = questionary.confirm(
                prompt_for_input,
                default=default if default is not None else False,
                style=self.questionary_style
            )
            result = question.ask()
            
            return result if result is not None else (default if default is not None else False)
            
        except (KeyboardInterrupt, EOFError):
            return default if default is not None else False


# Global instance for convenience
enhanced_input = EnhancedInput()


def get_enhanced_input(
    prompt: str = "",
    default: str = "",
    multiline: bool = False,
    suggestions: Optional[List[str]] = None,
    validator: Optional[callable] = None,
    allow_empty: bool = True,
    show_border: bool = True
) -> str:
    """Convenience function for getting enhanced input with arrow keys and borders.
    
    This is the sync version that should be called from sync contexts.
    It will handle async contexts by using nest_asyncio if needed.
    
    For async contexts, use get_enhanced_input_async instead.
    
    Args:
        prompt: The prompt to display
        default: Default value to pre-fill
        multiline: Whether to allow multiline input
        suggestions: List of suggestions for autocomplete
        validator: Optional validation function
        allow_empty: Whether to allow empty input
        show_border: Whether to show a border around the prompt
        
    Returns:
        The user's input as a string
    """
    return enhanced_input.get_text(
        prompt_text=prompt,
        default=default,
        multiline=multiline,
        suggestions=suggestions,
        validator=validator,
        allow_empty=allow_empty,
        show_border=show_border
    )


async def get_enhanced_input_async(
    prompt: str = "",
    default: str = "",
    multiline: bool = False,
    suggestions: Optional[List[str]] = None,
    validator: Optional[callable] = None,
    allow_empty: bool = True,
    show_border: bool = True
) -> str:
    """Async convenience function for getting enhanced input with arrow keys and borders.
    
    This should be called from async contexts (async def functions).
    
    Args:
        prompt: The prompt to display
        default: Default value to pre-fill
        multiline: Whether to allow multiline input
        suggestions: List of suggestions for autocomplete
        validator: Optional validation function
        allow_empty: Whether to allow empty input
        show_border: Whether to show a border around the prompt
        
    Returns:
        The user's input as a string
    """
    return await enhanced_input.get_text_async(
        prompt_text=prompt,
        default=default,
        multiline=multiline,
        suggestions=suggestions,
        validator=validator,
        allow_empty=allow_empty,
        show_border=show_border
    )