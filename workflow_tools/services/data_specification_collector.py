"""Service for collecting user data specifications for source and sink workflows."""

from typing import Optional, Dict, Any
from workflow_tools.common import printer
from workflow_tools.contexts import WorkflowContext
from workflow_tools.exceptions import NavigationBackRequest


class DataSpecificationCollector:
    """Collects user specifications for data filtering/selection in workflows."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        """Initialize the data specification collector.
        
        Args:
            context: Workflow context
            debug_mode: Whether to enable debug mode
        """
        self.context = context
        self.debug_mode = debug_mode
    
    async def collect_data_specification(self, workflow_type: str) -> Optional[str]:
        """Collect data specification from user for either source or sink workflow.
        
        Args:
            workflow_type: Either "source" or "sink"
        
        Returns:
            User's data specification text or None if skipped
        """
        from workflow_tools.common import clear_screen
        clear_screen()
        
        printer.print("\n" + "="*60)
        
        if workflow_type == "source":
            printer.print("📊 DATA SOURCE SPECIFICATION")
            printer.print("="*60)
            printer.print("\nWould you like to specify what data to retrieve from the API?")
            printer.print("This helps the AI generate more targeted code for your needs.")
            printer.print("\nYou can specify:")
            printer.print("  • Specific API endpoints to use")
            printer.print("  • Particular data fields or datasets")
            printer.print("  • Filtering criteria or parameters")
            printer.print("  • Time ranges or data freshness requirements")
            
        else:  # sink
            printer.print("📊 DATA SINK SPECIFICATION")
            printer.print("="*60)
            printer.print("\nWould you like to specify which data to sink from the Kafka messages?")
            printer.print("This helps the AI generate more efficient sink code.")
            printer.print("\nYou can specify:")
            printer.print("  • Specific fields to extract and sink")
            printer.print("  • Data transformations or mappings")
            printer.print("  • Filtering conditions")
            printer.print("  • Aggregation or batching requirements")
        
        from workflow_tools.core.questionary_utils import select
        
        printer.print("\n" + "-"*60)
        
        choices = [
            {'name': '✅ Yes, I want to specify data requirements', 'value': '1'},
            {'name': '⏭️ No, use all available data (default behavior)', 'value': '2'},
            {'name': '← Go back to previous phase', 'value': 'back'}
        ]
        
        choice = select("Select an option:", choices, default='2', show_border=True)
        
        if choice == 'back':
            raise NavigationBackRequest("User requested to go back")
        elif choice == '1':
            return self._collect_specification_details(workflow_type)
        else:  # choice == '2'
            printer.print("✅ Proceeding with default behavior (all available data)")
            return None
    
    def _collect_specification_details(self, workflow_type: str) -> str:
        """Collect detailed specification from user.
        
        Args:
            workflow_type: Either "source" or "sink"
        
        Returns:
            User's specification text
        """
        from workflow_tools.common import clear_screen
        clear_screen()
        
        printer.print("\n" + "-"*60)
        
        if workflow_type == "source":
            printer.print("📝 Describe what data you want to retrieve:")
            printer.print("(Examples: 'Only get stock prices for AAPL and GOOGL',")
            printer.print(" 'Use the /api/v2/weather endpoint with temperature and humidity fields',")
            printer.print(" 'Get the last 24 hours of data', 'Only retrieve active user records')")
        else:
            printer.print("📝 Describe what data you want to sink:")
            printer.print("(Examples: 'Only sink the price and timestamp fields',")
            printer.print(" 'Filter out records where status is inactive',")
            printer.print(" 'Aggregate data by minute before sinking',")
            printer.print(" 'Transform temperature from Fahrenheit to Celsius')")
        
        from workflow_tools.core.questionary_utils import text
        
        printer.print("\nEnter your data specification (or press Enter to skip):")
        printer.print("(You can enter multiple lines, press Esc then Enter when done)")
        
        specification = text(
            "",
            multiline=True,
            allow_empty=True,
            show_border=False
        )
        
        if not specification or not specification.strip():
            printer.print("ℹ️ No specification provided. Using default behavior.")
            return None
        
        if self.debug_mode:
            printer.print_debug(f"Collected data specification ({len(specification)} chars):")
            printer.print_debug(specification[:500] + "..." if len(specification) > 500 else specification)
        
        printer.print(f"✅ Data specification collected ({len(specification.splitlines())} lines)")
        
        # Store in context for later use
        if workflow_type == "source":
            self.context.technology.source_data_specification = specification
        else:
            self.context.technology.sink_data_specification = specification
        
        return specification
    
    def get_specification_for_prompt(self, workflow_type: str) -> str:
        """Get the data specification formatted for inclusion in AI prompts.
        
        Args:
            workflow_type: Either "source" or "sink"
        
        Returns:
            Formatted specification text for AI prompt, or empty string if none
        """
        # Try to get from context first
        if workflow_type == "source":
            spec = getattr(self.context.technology, 'source_data_specification', None)
        else:
            spec = getattr(self.context.technology, 'sink_data_specification', None)
        
        if not spec:
            return ""
        
        # Format for inclusion in prompt
        if workflow_type == "source":
            return f"""
USER DATA REQUIREMENTS:
The user has specified the following requirements for data retrieval:
{spec}

Please ensure the generated code specifically addresses these requirements and only retrieves the requested data.
"""
        else:
            return f"""
USER DATA REQUIREMENTS:
The user has specified the following requirements for data sinking:
{spec}

Please ensure the generated code filters, transforms, or processes the data according to these specifications before sinking.
"""