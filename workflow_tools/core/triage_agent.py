# triage_agent.py - Triage agent for workflow selection

import os
from typing import Optional
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.workflow_types import WorkflowType, WorkflowInfo
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.rule import Rule

class TriageAgent:
    """Agent for selecting the appropriate workflow based on user choice."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        self.context = context
        self.debug_mode = debug_mode
    
    def get_user_choice(self):
        """Get user's workflow choice using interactive menu."""
        # Set a fixed width for consistent display
        panel_width = 74
        console = Console(width=panel_width)

        # Build workflow options list
        workflow_options = []
        workflows = list(WorkflowInfo.WORKFLOW_DETAILS.keys())

        for workflow_type in workflows:
            # Skip Transform workflow for now (hidden as per requirements)
            if workflow_type == WorkflowType.TRANSFORM:
                continue

            info = WorkflowInfo.WORKFLOW_DETAILS[workflow_type]
            status_suffix = f" !{info['status']}" if info['status'] == "TBD" else ""
            option_text = f"{info['name']} ({info['description']}){status_suffix}"
            workflow_options.append({
                'workflow_type': workflow_type,
                'display': option_text,
                'implemented': info['implemented']
            })
        
        # Build Klaus Kode banner
        banner_lines = []
        banner_lines.append("\n")  # Add extra spacing at top
        banner_lines.append(" ██╗  ██╗██╗      █████╗ ██╗   ██╗███████╗    ██╗  ██╗ ██████╗ ██████╗ ███████╗")
        banner_lines.append(" ██║ ██╔╝██║     ██╔══██╗██║   ██║██╔════╝    ██║ ██╔╝██╔═══██╗██╔══██╗██╔════╝")
        banner_lines.append(" █████╔╝ ██║     ███████║██║   ██║███████╗    █████╔╝ ██║   ██║██║  ██║█████╗  ")
        banner_lines.append(" ██╔═██╗ ██║     ██╔══██║██║   ██║╚════██║    ██╔═██╗ ██║   ██║██║  ██║██╔══╝  ")
        banner_lines.append(" ██║  ██╗███████╗██║  ██║╚██████╔╝███████║    ██║  ██╗╚██████╔╝██████╔╝███████╗")
        banner_lines.append(" ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝    ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝")
        banner_lines.append("")
        banner_lines.append("                    Klaus Kode—agentic data integrator")
        banner_content = "\n".join(banner_lines)
        
        # Print the banner first (using regular printer for full width)
        printer.print(banner_content)
        printer.print("\n" + "=" * 80 + "\n")
        
        # Build the info content
        info_lines = []
        info_lines.append("Choose the type of workflow you'd like to run:")
        info_lines.append("")
        info_lines.append("You need a Quix Cloud account to run these workflows.")
        info_lines.append("If you don't have one yet, sign up for a free account here:")
        info_lines.append("[bold cyan][link=https://portal.cloud.quix.io/signup?utm_campaign=klaus-kode]https://portal.cloud.quix.io/signup?utm_campaign=klaus-kode[/link][/bold cyan]")
        info_content = "\n".join(info_lines)

        # Create a Rich panel for the information
        # Use Text.from_markup to process the markup in the string
        info_panel = Panel(
            Text.from_markup(info_content, justify="center"),
            border_style="cyan",
            padding=(1, 2),
            expand=False
        )
        
        # Print the info panel using the width-constrained console
        console.print(info_panel)
        console.print("")  # Add spacing
        
        # Print a horizontal divider with the same width as the panel
        console.rule("[bold cyan]Workflow Selection[/bold cyan]", style="cyan")
        console.print("")
        console.print("[dim cyan]Use ↑↓ arrow keys to navigate, Enter to select[/dim cyan]", justify="center")
        console.print("")
        
        from workflow_tools.core.questionary_utils import select
        
        # Create choices for questionary with newlines for spacing
        choices = []
        workflow_map = {}
        for option in workflow_options:
            # Add newline at the end of each option for vertical spacing
            display_with_spacing = option['display'] + '\n'
            choices.append({'name': display_with_spacing, 'value': option['workflow_type']})
            workflow_map[option['workflow_type']] = option

        # Add option to change default workspace
        current_workspace = os.environ.get('QUIX_WORKSPACE_ID')
        if current_workspace:
            # Extract just the project-env part for display
            parts = current_workspace.split('-')
            if len(parts) >= 3:
                project_env = f"{parts[-2]}-{parts[-1]}"  # e.g., "myproject-production"
            else:
                project_env = current_workspace
            workspace_option = f'⚙️  Change default project/environment (currently: {project_env})\n'
        else:
            workspace_option = '⚙️  Set default project/environment\n'
        choices.append({'name': workspace_option, 'value': 'WORKSPACE_CONFIG'})

        # Add quit option with newline spacing
        choices.append({'name': '❌ Quit\n', 'value': 'QUIT'})
        
        # Show the menu without any prompt text
        selected_type = select("", choices, show_border=False)
        
        if selected_type == 'QUIT':
            # Clear any questionary artifacts and print goodbye
            import sys
            sys.stdout.write('\r\033[K')  # Clear the current line
            printer.print("\n👋 Goodbye!\n")
            return None

        if selected_type == 'WORKSPACE_CONFIG':
            # Handle workspace configuration
            return 'WORKSPACE_CONFIG'

        workflow_type = selected_type
        selected = workflow_map[workflow_type]
        
        # Check if workflow is implemented
        if not selected['implemented']:
            printer.print(f"❌ The {WorkflowInfo.get_name(workflow_type)} workflow is not yet implemented.")
            printer.print("Please choose another option.")
            return self.get_user_choice()  # Recursively ask again
        
        # Store the selected workflow in context
        self.context.selected_workflow = workflow_type
        
        return workflow_type
    
    def run_triage(self):
        """Run the triage process and return selected workflow or special action."""
        # Clear screen at the start of the workflow
        from workflow_tools.common import clear_screen
        clear_screen()

        # Don't print header here anymore - it's handled by the menu
        selected_workflow = self.get_user_choice()

        if selected_workflow and selected_workflow != 'WORKSPACE_CONFIG':
            # Clear screen after selection to start fresh
            clear_screen()
            workflow_name = WorkflowInfo.get_name(selected_workflow)
            printer.print(f"✅ Selected: {workflow_name}")
            printer.print("")

        return selected_workflow