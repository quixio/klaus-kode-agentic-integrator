# phase_diagnose_app_selection.py - Application Selection Phase for Diagnose Workflow

import asyncio
from typing import List, Dict, Any, Optional
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.integrations.quix_tools import find_applications
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.services.prerequisites_collector import PrerequisitesCollector
from workflow_tools.core.questionary_utils import select
from workflow_tools.common import clear_screen, get_user_approval
from workflow_tools.core.navigation import NavigationRequest, DiagnoseWorkflowSteps


class DiagnoseAppSelectionPhase(BasePhase):
    """Handles workspace selection and application listing/selection for diagnose workflow."""
    
    phase_name = "diagnose_app_selection"
    phase_description = "Select workspace and application"
    
    def __init__(self, context: WorkflowContext, run_config=None, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.run_config = run_config
        self.prerequisites_collector = PrerequisitesCollector(context, debug_mode, run_config)
    
    async def execute(self) -> PhaseResult:
        """Execute the app selection phase."""
        try:
            # Step 1: Select workspace (reuse existing logic)
            printer.print_section_header("Workspace Selection", icon="🌐", style="cyan")
            
            workspace_selected = await self.prerequisites_collector.collect_workspace_info()
            if not workspace_selected:
                return PhaseResult(success=False, message="Workspace selection cancelled")
            
            # Step 2: List and select application
            printer.print_section_header("Application Selection", icon="📋", style="cyan")
            
            app_selected = await self._select_application()
            if not app_selected:
                return PhaseResult(success=False, message="Application selection cancelled")
            
            return PhaseResult(success=True, message="Application selected successfully")
            
        except NavigationBackRequest:
            raise  # Let the orchestrator handle navigation
        except Exception as e:
            printer.print(f"❌ Error during app selection: {e}")
            return PhaseResult(success=False, message=f"Failed to select application: {e}")
    
    async def _select_application(self) -> bool:
        """List applications in the workspace and let user select one."""
        try:
            printer.print(f"\n📋 Fetching applications from workspace '{self.context.workspace.workspace_name}'...")
            
            # Get list of applications
            apps = await find_applications(self.context.workspace.workspace_id)
            
            if not apps:
                printer.print("❌ No applications found in this workspace.")
                printer.print("   Please create an application first or select a different workspace.")
                choices = [
                    {'name': '⬅️ Go back to workspace selection', 'value': 'back'},
                    {'name': '❌ Quit', 'value': 'quit'}
                ]
                response = select("What would you like to do?", choices, show_border=True)
                if response == 'quit':
                    return False
                # Navigate back to workspace selection
                self.context.navigation_request = NavigationRequest(
                    target_step=DiagnoseWorkflowSteps.SELECT_WORKSPACE,
                    message="No apps found, going back to workspace selection"
                )
                raise NavigationBackRequest()
            
            printer.print(f"\n✅ Found {len(apps)} application(s)")
            
            # Clear screen for menu
            clear_screen()

            # Create selection choices for questionary
            choices = []
            app_map = {}

            for app in apps:
                app_name = app.get('name', 'Unnamed')
                app_id = app.get('applicationId', 'Unknown')  # Note: API returns 'applicationId' not 'id'
                app_language = app.get('language', 'Unknown')

                # Try to get more details if available
                created_on = app.get('createdOn', '')
                updated_on = app.get('updatedOn', '')

                # Format display text
                display_text = f"{app_name} ({app_language})"
                if updated_on:
                    display_text += f" - Updated: {updated_on[:10]}"
                elif created_on:
                    display_text += f" - Created: {created_on[:10]}"

                choices.append({'name': display_text, 'value': app_id})
                app_map[app_id] = {
                    'name': app_name,
                    'id': app_id,
                    'language': app_language,
                    'data': app,
                    'created_on': created_on,
                    'updated_on': updated_on
                }

            # Add back option
            choices.append({'name': '⬅️ Go back to workspace selection', 'value': 'BACK'})

            # Get user selection
            printer.print_section_header("Select Application", icon="📋", style="cyan")
            selected_id = select("", choices, show_border=False)

            if selected_id == 'BACK':
                # Navigate back to workspace selection within this phase
                self.context.navigation_request = NavigationRequest(
                    target_step=DiagnoseWorkflowSteps.SELECT_WORKSPACE,
                    message="User requested to go back to workspace selection"
                )
                raise NavigationBackRequest()

            selected_app = app_map[selected_id]
            
            # Store in context
            self.context.workspace.app_name = selected_app['name']
            self.context.workspace.app_id = selected_app['id']
            self.context.workspace.app_language = selected_app['language']
            self.context.workspace.app_data = selected_app['data']
            
            printer.print(f"\n✅ Selected application: {selected_app['name']}")
            printer.print(f"   ID: {selected_app['id']}")
            printer.print(f"   Language: {selected_app['language']}")
            
            return True
                    
        except Exception as e:
            printer.print(f"❌ Error fetching applications: {e}")
            return False