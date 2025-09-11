"""Unified input system using questionary for all user interactions.

This module provides a consistent interface for all user prompts using questionary,
ensuring arrow key navigation, beautiful styling, and proper async support throughout
the application.
"""

import asyncio
from typing import Optional, List, Dict, Any, Union
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import questionary
from questionary import Style
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Initialize console for rich formatting
console = Console()

# Define a consistent style for all questionary prompts
QUESTIONARY_STYLE = Style([
    ('qmark', 'fg:#00aa00 bold'),       # Question mark
    ('question', 'fg:#00aaaa bold'),    # Question text
    ('answer', 'fg:#ffffff bold'),      # User input
    ('pointer', 'fg:#00aa00 bold'),     # Pointer for selections (►)
    ('highlighted', 'fg:#00aaaa bold'), # Highlighted selection
    ('selected', 'fg:#00aa00'),         # Selected item
    ('separator', 'fg:#666666'),        # Separator
    ('instruction', 'fg:#888888'),      # Instructions
    ('text', 'fg:#ffffff'),             # General text
])

# Rich styles for borders
PROMPT_STYLE = "bold cyan"
BORDER_STYLE = "bright_blue"


def show_bordered_prompt(prompt_text: str) -> None:
    """Display a prompt in a beautiful bordered panel.
    
    Args:
        prompt_text: The prompt text to display
    """
    if prompt_text:
        prompt_panel = Panel(
            Text(prompt_text, style=PROMPT_STYLE),
            border_style=BORDER_STYLE,
            expand=False,
            padding=(0, 1)
        )
        console.print(prompt_panel)

def show_menu_border_top():
    """Display the top part of a menu border."""
    console.print("╭" + "─" * 78 + "╮", style="cyan")

def show_menu_border_bottom():
    """Display the bottom part of a menu border."""
    console.print("╰" + "─" * 78 + "╯", style="cyan")


# === ASYNC VERSIONS (for use in async contexts) ===

async def select_async(
    message: str,
    choices: List[Union[str, Dict[str, Any]]],
    default: Optional[str] = None,
    show_border: bool = True
) -> str:
    """Async: Select from a list of options with arrow key navigation.
    
    Args:
        message: The prompt message
        choices: List of choices (can be strings or dicts with 'name' and 'value')
        default: Default selection
        show_border: Whether to show a bordered prompt
        
    Returns:
        The selected value
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    question = questionary.select(
        prompt,
        choices=choices,
        default=default,
        style=QUESTIONARY_STYLE
    )
    
    return await question.ask_async()


async def text_async(
    message: str,
    default: str = "",
    validate: Optional[callable] = None,
    multiline: bool = False,
    show_border: bool = True
) -> str:
    """Async: Get text input with arrow key navigation.
    
    Args:
        message: The prompt message
        default: Default value
        validate: Validation function
        multiline: Allow multiline input
        show_border: Whether to show a bordered prompt
        
    Returns:
        The user's text input
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    question = questionary.text(
        prompt,
        default=default,
        validate=validate,
        multiline=multiline,
        style=QUESTIONARY_STYLE
    )
    
    return await question.ask_async()


async def confirm_async(
    message: str,
    default: bool = False,
    show_border: bool = True
) -> bool:
    """Async: Get yes/no confirmation.
    
    Args:
        message: The prompt message
        default: Default value (True for yes, False for no)
        show_border: Whether to show a bordered prompt
        
    Returns:
        True for yes, False for no
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    question = questionary.confirm(
        prompt,
        default=default,
        style=QUESTIONARY_STYLE
    )
    
    return await question.ask_async()


async def checkbox_async(
    message: str,
    choices: List[Union[str, Dict[str, Any]]],
    default: Optional[List[str]] = None,
    show_border: bool = True
) -> List[str]:
    """Async: Select multiple options with checkboxes.
    
    Args:
        message: The prompt message
        choices: List of choices
        default: Default selections
        show_border: Whether to show a bordered prompt
        
    Returns:
        List of selected values
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    question = questionary.checkbox(
        prompt,
        choices=choices,
        default=default or [],
        style=QUESTIONARY_STYLE
    )
    
    return await question.ask_async()


async def autocomplete_async(
    message: str,
    choices: List[str],
    default: str = "",
    validate: Optional[callable] = None,
    show_border: bool = True
) -> str:
    """Async: Text input with autocomplete suggestions.
    
    Args:
        message: The prompt message
        choices: List of autocomplete suggestions
        default: Default value
        validate: Validation function
        show_border: Whether to show a bordered prompt
        
    Returns:
        The user's input
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    question = questionary.autocomplete(
        prompt,
        choices=choices,
        default=default,
        validate=validate,
        style=QUESTIONARY_STYLE
    )
    
    return await question.ask_async()


# === SYNC VERSIONS (for use in sync contexts) ===

def select(
    message: str,
    choices: List[Union[str, Dict[str, Any]]],
    default: Optional[str] = None,
    show_border: bool = True
) -> str:
    """Select from a list of options with arrow key navigation.
    
    Note: Press Ctrl+C twice quickly to force quit the application.
    
    Args:
        message: The prompt message
        choices: List of choices (can be strings or dicts with 'name' and 'value')
        default: Default selection
        show_border: Whether to show a bordered prompt
        
    Returns:
        The selected value
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    result = questionary.select(
        prompt,
        choices=choices,
        default=default,
        style=QUESTIONARY_STYLE
    ).ask()
    
    # Handle Ctrl+C (returns None)
    if result is None:
        import sys
        console.print("\n[yellow]⚠️ Interrupted. Press Ctrl+C again to force quit.[/yellow]")
        sys.exit(0)
    
    return result


def text(
    message: str,
    default: str = "",
    validate: Optional[callable] = None,
    multiline: bool = False,
    show_border: bool = True
) -> str:
    """Get text input with arrow key navigation.
    
    Args:
        message: The prompt message
        default: Default value
        validate: Validation function
        multiline: Allow multiline input
        show_border: Whether to show a bordered prompt
        
    Returns:
        The user's text input
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    result = questionary.text(
        prompt,
        default=default,
        validate=validate,
        multiline=multiline,
        style=QUESTIONARY_STYLE
    ).ask()
    
    # Handle Ctrl+C (returns None)
    if result is None:
        import sys
        console.print("\n[yellow]⚠️ Interrupted. Press Ctrl+C again to force quit.[/yellow]")
        sys.exit(0)
    
    return result


def confirm(
    message: str,
    default: bool = False,
    show_border: bool = True
) -> bool:
    """Get yes/no confirmation.
    
    Args:
        message: The prompt message
        default: Default value (True for yes, False for no)
        show_border: Whether to show a bordered prompt
        
    Returns:
        True for yes, False for no
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    return questionary.confirm(
        prompt,
        default=default,
        style=QUESTIONARY_STYLE
    ).ask()


def checkbox(
    message: str,
    choices: List[Union[str, Dict[str, Any]]],
    default: Optional[List[str]] = None,
    show_border: bool = True
) -> List[str]:
    """Select multiple options with checkboxes.
    
    Args:
        message: The prompt message
        choices: List of choices
        default: Default selections
        show_border: Whether to show a bordered prompt
        
    Returns:
        List of selected values
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    result = questionary.checkbox(
        prompt,
        choices=choices,
        default=default or [],
        style=QUESTIONARY_STYLE
    ).ask()
    
    # Handle Ctrl+C (returns None)
    if result is None:
        import sys
        console.print("\n[yellow]⚠️ Interrupted. Press Ctrl+C again to force quit.[/yellow]")
        sys.exit(0)
    
    return result


def autocomplete(
    message: str,
    choices: List[str],
    default: str = "",
    validate: Optional[callable] = None,
    show_border: bool = True
) -> str:
    """Text input with autocomplete suggestions.
    
    Args:
        message: The prompt message
        choices: List of autocomplete suggestions
        default: Default value
        validate: Validation function
        show_border: Whether to show a bordered prompt
        
    Returns:
        The user's input
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    result = questionary.autocomplete(
        prompt,
        choices=choices,
        default=default,
        validate=validate,
        style=QUESTIONARY_STYLE
    ).ask()
    
    # Handle Ctrl+C (returns None)
    if result is None:
        import sys
        console.print("\n[yellow]⚠️ Interrupted. Press Ctrl+C again to force quit.[/yellow]")
        sys.exit(0)
    
    return result


def password(
    message: str,
    validate: Optional[callable] = None,
    show_border: bool = True
) -> str:
    """Get password input (hidden characters).
    
    Args:
        message: The prompt message
        validate: Validation function
        show_border: Whether to show a bordered prompt
        
    Returns:
        The password
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    return questionary.password(
        prompt,
        validate=validate,
        style=QUESTIONARY_STYLE
    ).ask()


def path(
    message: str,
    default: str = "",
    validate: Optional[callable] = None,
    only_directories: bool = False,
    file_filter: Optional[callable] = None,
    show_border: bool = True
) -> str:
    """Get file or directory path with completion.
    
    Args:
        message: The prompt message
        default: Default path
        validate: Validation function
        only_directories: Only show directories
        file_filter: Filter function for files
        show_border: Whether to show a bordered prompt
        
    Returns:
        The selected path
    """
    if show_border:
        show_bordered_prompt(message)
        prompt = "› "
    else:
        prompt = message
    
    return questionary.path(
        prompt,
        default=default,
        validate=validate,
        only_directories=only_directories,
        file_filter=file_filter,
        style=QUESTIONARY_STYLE
    ).ask()


# === COMMON PATTERNS ===

def select_yes_no_back(
    message: str,
    show_border: bool = True
) -> str:
    """Select yes/no/back with arrow navigation.
    
    Common pattern for approval prompts with back option.
    
    Args:
        message: The prompt message
        show_border: Whether to show a bordered prompt
        
    Returns:
        'yes', 'no', or 'back'
    """
    choices = [
        {'name': '✓ Yes', 'value': 'yes'},
        {'name': '✗ No', 'value': 'no'},
        {'name': '← Go back', 'value': 'back'}
    ]
    return select(message, choices, show_border=show_border)


async def select_yes_no_back_async(
    message: str,
    show_border: bool = True
) -> str:
    """Async: Select yes/no/back with arrow navigation.
    
    Common pattern for approval prompts with back option.
    
    Args:
        message: The prompt message
        show_border: Whether to show a bordered prompt
        
    Returns:
        'yes', 'no', or 'back'
    """
    choices = [
        {'name': '✓ Yes', 'value': 'yes'},
        {'name': '✗ No', 'value': 'no'},
        {'name': '← Go back', 'value': 'back'}
    ]
    return await select_async(message, choices, show_border=show_border)


def select_yes_no(
    message: str,
    default: str = 'yes',
    show_border: bool = True
) -> str:
    """Select yes/no with arrow navigation.
    
    Better than confirm() when you want arrow key selection.
    
    Args:
        message: The prompt message
        default: Default selection ('yes' or 'no')
        show_border: Whether to show a bordered prompt
        
    Returns:
        'yes' or 'no'
    """
    choices = [
        {'name': '✓ Yes', 'value': 'yes'},
        {'name': '✗ No', 'value': 'no'}
    ]
    
    # Find the choice dict that matches the default value
    default_choice = None
    for choice in choices:
        if choice['value'] == default:
            default_choice = choice
            break
    
    # If no matching choice found, use the first one
    if default_choice is None:
        default_choice = choices[0]
    
    return select(message, choices, default=default_choice, show_border=show_border)


async def select_yes_no_async(
    message: str,
    default: str = 'yes',
    show_border: bool = True
) -> str:
    """Async: Select yes/no with arrow navigation.
    
    Better than confirm() when you want arrow key selection.
    
    Args:
        message: The prompt message
        default: Default selection ('yes' or 'no')
        show_border: Whether to show a bordered prompt
        
    Returns:
        'yes' or 'no'
    """
    choices = [
        {'name': '✓ Yes', 'value': 'yes'},
        {'name': '✗ No', 'value': 'no'}
    ]
    
    # Find the choice dict that matches the default value
    default_choice = None
    for choice in choices:
        if choice['value'] == default:
            default_choice = choice
            break
    
    # If no matching choice found, use the first one
    if default_choice is None:
        default_choice = choices[0]
    
    return await select_async(message, choices, default=default_choice, show_border=show_border)


def select_action(
    message: str,
    actions: List[Dict[str, str]],
    show_border: bool = True
) -> str:
    """Select from a list of actions with descriptions.
    
    Common pattern for action menus.
    
    Args:
        message: The prompt message
        actions: List of dicts with 'name', 'value', and optionally 'description'
        show_border: Whether to show a bordered prompt
        
    Returns:
        The selected action value
    """
    choices = []
    for action in actions:
        if 'description' in action:
            name = f"{action['name']} - {action['description']}"
        else:
            name = action['name']
        choices.append({'name': name, 'value': action['value']})
    
    return select(message, choices, show_border=show_border)


async def select_action_async(
    message: str,
    actions: List[Dict[str, str]],
    show_border: bool = True
) -> str:
    """Async: Select from a list of actions with descriptions.
    
    Common pattern for action menus.
    
    Args:
        message: The prompt message
        actions: List of dicts with 'name', 'value', and optionally 'description'
        show_border: Whether to show a bordered prompt
        
    Returns:
        The selected action value
    """
    choices = []
    for action in actions:
        if 'description' in action:
            name = f"{action['name']} - {action['description']}"
        else:
            name = action['name']
        choices.append({'name': name, 'value': action['value']})
    
    return await select_async(message, choices, show_border=show_border)


# === UTILITY FUNCTIONS ===

def clear_screen():
    """Clear the terminal screen."""
    import os
    os.system('clear' if os.name == 'posix' else 'cls')


def select_from_dataframe(
    df,
    message: str,
    value_column: Optional[str] = None,
    display_columns: Optional[List[str]] = None,
    show_border: bool = True
) -> Any:
    """Select from a pandas DataFrame using questionary.
    
    Args:
        df: Pandas DataFrame with options
        message: The prompt message
        value_column: Column to return as the selected value
        display_columns: Columns to show in the display
        show_border: Whether to show a bordered prompt
        
    Returns:
        Selected value from the DataFrame
    """
    if df.empty:
        console.print("[red]No data available to select from.[/red]")
        return None
    
    # Create display choices
    choices = []
    for _, row in df.iterrows():
        if display_columns:
            display_text = " | ".join(str(row[col]) for col in display_columns if col in row)
        else:
            display_text = " | ".join(f"{col}: {row[col]}" for col in df.columns)
        
        if value_column:
            choices.append({
                'name': display_text,
                'value': row[value_column]
            })
        else:
            choices.append({
                'name': display_text,
                'value': row.to_dict()
            })
    
    return select(message, choices, show_border=show_border)


async def select_from_dataframe_async(
    df,
    message: str,
    value_column: Optional[str] = None,
    display_columns: Optional[List[str]] = None,
    show_border: bool = True
) -> Any:
    """Async: Select from a pandas DataFrame using questionary.
    
    Args:
        df: Pandas DataFrame with options
        message: The prompt message
        value_column: Column to return as the selected value
        display_columns: Columns to show in the display
        show_border: Whether to show a bordered prompt
        
    Returns:
        Selected value from the DataFrame
    """
    if df.empty:
        console.print("[red]No data available to select from.[/red]")
        return None
    
    # Create display choices
    choices = []
    for _, row in df.iterrows():
        if display_columns:
            display_text = " | ".join(str(row[col]) for col in display_columns if col in row)
        else:
            display_text = " | ".join(f"{col}: {row[col]}" for col in df.columns)
        
        if value_column:
            choices.append({
                'name': display_text,
                'value': row[value_column]
            })
        else:
            choices.append({
                'name': display_text,
                'value': row.to_dict()
            })
    
    return await select_async(message, choices, show_border=show_border)