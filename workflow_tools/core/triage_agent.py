# triage_agent.py - Triage agent for workflow selection

from typing import Optional
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.workflow_types import WorkflowType, WorkflowInfo
from workflow_tools.core.interactive_menu import InteractiveMenu

class TriageAgent:
    """Agent for selecting the appropriate workflow based on user choice."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        self.context = context
        self.debug_mode = debug_mode
    
    def get_user_choice(self) -> Optional[WorkflowType]:
        """Get user's workflow choice using interactive menu."""
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
        
        # Build header content that should be preserved on menu updates
        header_lines = []
        header_lines.append("")
        header_lines.append(" ██╗  ██╗██╗      █████╗ ██╗   ██╗███████╗    ██╗  ██╗ ██████╗ ██████╗ ███████╗")
        header_lines.append(" ██║ ██╔╝██║     ██╔══██╗██║   ██║██╔════╝    ██║ ██╔╝██╔═══██╗██╔══██╗██╔════╝")
        header_lines.append(" █████╔╝ ██║     ███████║██║   ██║███████╗    █████╔╝ ██║   ██║██║  ██║█████╗  ")
        header_lines.append(" ██╔═██╗ ██║     ██╔══██║██║   ██║╚════██║    ██╔═██╗ ██║   ██║██║  ██║██╔══╝  ")
        header_lines.append(" ██║  ██╗███████╗██║  ██║╚██████╔╝███████║    ██║  ██╗╚██████╔╝██████╔╝███████╗")
        header_lines.append(" ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝    ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝")
        header_lines.append("")
        header_lines.append("                    Klaus Kode—agentic data integrator")
        header_lines.append("")
        header_lines.append("=" * 80)
        header_lines.append("")
        header_lines.append("Please choose the type of workflow you'd like to create:")
        header_lines.append("")
        header_lines.append("")
        header_lines.append("You need a Quix Cloud account to use this workflow.")
        header_lines.append("If you don't have one yet, sign up for a free account here:")
        header_lines.append("https://portal.cloud.quix.io/signup?utm_campaign=ai-data-integrator")
        header_lines.append("")
        header_content = "\n".join(header_lines)
        
        # Create menu and get selection with the header content
        menu = InteractiveMenu(title="Select Workflow Type", show_instructions=True, header_content=header_content)
        
        # Format function for display
        def format_workflow(option):
            return option['display']
        
        selected, index = menu.select_option(
            workflow_options,
            display_formatter=format_workflow,
            allow_back=False  # No back option at top level
        )
        
        if selected is None:
            printer.print("👋 Goodbye!")
            return None
        
        workflow_type = selected['workflow_type']
        
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