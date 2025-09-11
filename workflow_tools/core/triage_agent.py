# triage_agent.py - Triage agent for workflow selection

from typing import Optional
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.workflow_types import WorkflowType, WorkflowInfo
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

class TriageAgent:
    """Agent for selecting the appropriate workflow based on user choice."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        self.context = context
        self.debug_mode = debug_mode
    
    def get_user_choice(self) -> Optional[WorkflowType]:
        """Get user's workflow choice using interactive menu."""
        console = Console()
        
        # Build workflow options list
        workflow_options = []
        workflows = list(WorkflowInfo.WORKFLOW_DETAILS.keys())
        
        for workflow_type in workflows:
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
        
        # Print the banner first
        printer.print(banner_content)
        printer.print("\n" + "=" * 80 + "\n")
        
        # Build the info content
        info_lines = []
        info_lines.append("Please choose the type of workflow you'd like to create:")
        info_lines.append("")
        info_lines.append("You need a Quix Cloud account to use this workflow.")
        info_lines.append("If you don't have one yet, sign up for a free account here:")
        info_lines.append("https://portal.cloud.quix.io/signup?utm_campaign=ai-data-integrator")
        info_content = "\n".join(info_lines)
        
        # Create a Rich panel for the information
        info_panel = Panel(
            Text(info_content, justify="center"),
            border_style="cyan",
            padding=(1, 2),
            expand=False
        )
        
        # Print the info panel
        console.print(info_panel)
        console.print("")  # Add spacing
        
        # Print a horizontal divider before the menu
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
        
        # Add quit option with newline spacing
        choices.append({'name': '❌ Quit\n', 'value': 'QUIT'})
        
        # Show the menu without any prompt text
        selected_type = select("", choices, show_border=False)
        
        if selected_type == 'QUIT':
            printer.print("👋 Goodbye!")
            return None
        
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
    
    def run_triage(self) -> Optional[WorkflowType]:
        """Run the triage process and return selected workflow."""
        # Clear screen at the start of the workflow
        from workflow_tools.common import clear_screen
        clear_screen()
        
        # Don't print header here anymore - it's handled by the menu
        selected_workflow = self.get_user_choice()
        
        if selected_workflow:
            # Clear screen after selection to start fresh
            clear_screen()
            workflow_name = WorkflowInfo.get_name(selected_workflow)
            printer.print(f"✅ Selected: {workflow_name}")
            printer.print("")
        
        return selected_workflow