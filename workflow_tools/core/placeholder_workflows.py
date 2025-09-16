# placeholder_workflows.py - Placeholder workflows for unimplemented features

from typing import Optional
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.workflow_types import WorkflowType, WorkflowInfo

class PlaceholderWorkflowBase:
    """Base class for placeholder workflows."""
    
    def __init__(self, context: WorkflowContext, workflow_type: WorkflowType, debug_mode: bool = False):
        self.context = context
        self.workflow_type = workflow_type
        self.debug_mode = debug_mode
        self.workflow_name = WorkflowInfo.get_name(workflow_type)
    
    def show_placeholder_message(self) -> str:
        """Show placeholder message and get user choice."""
        printer.print(f"The {self.workflow_name} workflow hasn't been implemented yet, but its coming soon.")
        printer.print("")
        from workflow_tools.core.questionary_utils import select
        
        choices = [
            {'name': '← Back to the triage agent', 'value': 'back'},
            {'name': '❌ Quit', 'value': 'quit'}
        ]
        
        choice = select("What would you like to do?", choices, show_border=True)
        return choice
    
    def run(self) -> Optional[str]:
        """Run the placeholder workflow."""
        printer.print(f"\n--- {self.workflow_name} ---")
        return self.show_placeholder_message()

class SourceWorkflowPlaceholder(PlaceholderWorkflowBase):
    """Placeholder for Source workflow."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        super().__init__(context, WorkflowType.SOURCE, debug_mode)
    
    def run(self) -> Optional[str]:
        """Run the source workflow placeholder."""
        printer.print(f"\n--- {self.workflow_name} ---")
        printer.print("This workflow will help you bring data from external systems into Quix.")
        printer.print("")
        return self.show_placeholder_message()

class TransformWorkflowPlaceholder(PlaceholderWorkflowBase):
    """Placeholder for Transform workflow."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        super().__init__(context, WorkflowType.TRANSFORM, debug_mode)
    
    def run(self) -> Optional[str]:
        """Run the transform workflow placeholder."""
        printer.print(f"\n--- {self.workflow_name} ---")
        printer.print("This workflow will help you process and transform data already in Quix.")
        printer.print("")
        return self.show_placeholder_message()

class DiagnoseWorkflowPlaceholder(PlaceholderWorkflowBase):
    """Placeholder for Diagnose workflow."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        super().__init__(context, WorkflowType.DIAGNOSE, debug_mode)
    
    def run(self) -> Optional[str]:
        """Run the diagnose workflow placeholder."""
        printer.print(f"\n--- {self.workflow_name} ---")
        printer.print("This workflow will help you diagnose and update existing Quix applications.")
        printer.print("")
        return self.show_placeholder_message()

class PlaceholderWorkflowFactory:
    """Factory for creating placeholder workflows."""
    
    @staticmethod
    def create_placeholder(workflow_type: WorkflowType, context: WorkflowContext, debug_mode: bool = False) -> PlaceholderWorkflowBase:
        """Create appropriate placeholder workflow."""
        if workflow_type == WorkflowType.SOURCE:
            return SourceWorkflowPlaceholder(context, debug_mode)
        elif workflow_type == WorkflowType.TRANSFORM:
            return TransformWorkflowPlaceholder(context, debug_mode)
        elif workflow_type == WorkflowType.DIAGNOSE:
            return DiagnoseWorkflowPlaceholder(context, debug_mode)
        else:
            raise ValueError(f"No placeholder available for workflow type: {workflow_type}")