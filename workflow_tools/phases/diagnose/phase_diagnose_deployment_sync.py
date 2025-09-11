# phase_diagnose_deployment_sync.py - Deployment Sync Phase for Diagnose Workflow

import asyncio
from typing import Optional, List, Dict, Any
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.integrations.quix_tools import (
    list_deployments,
    sync_deployment,
    get_deployment_details,
    start_deployment
)
from workflow_tools.phases.shared.phase_deployment import DeploymentPhase
from workflow_tools.exceptions import NavigationBackRequest


class DiagnoseDeploymentSyncPhase(BasePhase):
    """Handles deployment sync or creation for the diagnose workflow."""
    
    phase_name = "diagnose_deployment_sync"
    phase_description = "Sync or create deployment"
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        # Reuse the standard deployment phase for new deployments
        self.standard_deployment = DeploymentPhase(context, debug_mode)
    
    async def execute(self) -> PhaseResult:
        """Execute the deployment sync phase."""
        try:
            printer.print("\n" + "="*50)
            printer.print("DEPLOYMENT")
            printer.print("="*50)
            
            # Check for existing deployments
            existing_deployments = await self._find_existing_deployments()
            
            if existing_deployments:
                # Handle existing deployments
                deployment_choice = await self._select_deployment_action(existing_deployments)
                
                if deployment_choice == 'skip':
                    return PhaseResult(success=True, message="Deployment skipped")
                elif deployment_choice == 'new':
                    # Fall through to create new deployment
                    pass
                elif deployment_choice:
                    # User selected a deployment to sync
                    if await self._sync_deployment(deployment_choice):
                        return PhaseResult(success=True, message="Deployment synced successfully")
                    else:
                        return PhaseResult(success=False, message="Failed to sync deployment")
                else:
                    raise NavigationBackRequest()
            
            # Use standard deployment phase for creating new deployment
            # The standard phase handles all the deployment creation logic
            return await self.standard_deployment.run()
            
        except NavigationBackRequest:
            raise
        except Exception as e:
            printer.print(f"❌ Error during deployment: {e}")
            return PhaseResult(success=False, message=f"Failed: {e}")
    
    async def _find_existing_deployments(self) -> List[Dict[str, Any]]:
        """Find existing deployments for the current application."""
        try:
            printer.print(f"\n🔍 Checking for existing deployments...")
            
            deployments = await list_deployments(
                workspace_id=self.context.workspace.workspace_id,
                application_id=self.context.workspace.app_id
            )
            
            if deployments:
                printer.print(f"✅ Found {len(deployments)} deployment(s)")
            
            return deployments
            
        except Exception as e:
            printer.print(f"⚠️ Error checking deployments: {e}")
            return []
    
    async def _select_deployment_action(self, deployments: List[Dict[str, Any]]) -> Optional[Any]:
        """Let user select what to do with existing deployments.
        
        Returns:
            - Deployment dict if user wants to sync
            - 'new' if user wants new deployment
            - 'skip' if user wants to skip
            - None if user wants to go back
        """
        from workflow_tools.core.interactive_menu import InteractiveMenu
        
        # Clear screen for interactive menu
        InteractiveMenu.clear_terminal()
        
        # Build menu options
        options = []
        
        # Add existing deployments
        for dep in deployments:
            name = dep.get('name', 'Unnamed')
            status = dep.get('status', 'Unknown')
            
            status_emoji = {
                'Running': '🟢',
                'Stopped': '🔴',
                'Starting': '🟡',
                'Error': '❌'
            }.get(status, '⚪')
            
            options.append({
                'deployment': dep,
                'text': f"{status_emoji} {name} ({status})"
            })
        
        # Add action options
        options.append({'action': 'new', 'text': '🆕 Create new deployment'})
        options.append({'action': 'skip', 'text': '⏭️ Skip deployment'})
        options.append({'action': 'back', 'text': '⬅️ Go back'})
        
        # Create title
        title = f"Found {len(deployments)} existing deployment(s) based on this application.\nSelect deployment to sync or choose an action:"
        
        # Use interactive menu
        menu = InteractiveMenu(title=title)
        
        # Format function for display
        def format_option(opt):
            return opt['text']
        
        # Get user selection with arrow keys
        selected, index = menu.select_option(
            options,
            display_formatter=format_option,
            allow_back=False  # We handle back option manually
        )
        
        if selected is None:
            return None
        
        # Handle deployment selection
        if 'deployment' in selected:
            return selected['deployment']
        
        # Handle action selections using dictionary dispatch
        action_map = {
            'new': 'new',
            'skip': 'skip',
            'back': None
        }
        
        return action_map.get(selected.get('action'))
    
    async def _sync_deployment(self, deployment: Dict[str, Any]) -> bool:
        """Sync a specific deployment with the latest code."""
        try:
            dep_name = deployment.get('name', 'Unnamed')
            dep_id = deployment.get('deploymentId')
            
            printer.print(f"\n🔄 Syncing deployment '{dep_name}'...")
            
            # Perform the sync
            result = await sync_deployment(dep_id)
            
            if result:
                printer.print(f"✅ Deployment synced successfully!")
                
                # Store deployment info for potential monitoring
                self.context.deployment.deployment_id = dep_id
                self.context.deployment.deployment_name = dep_name
                
                # Check if stopped and offer to start
                details = await get_deployment_details(
                    self.context.workspace.workspace_id,
                    dep_id
                )
                
                if details and details.get('status') == 'Stopped':
                    printer.print("\n⚠️ Deployment is stopped.")
                    start = input("Start it now? (y/n): ").strip().lower()
                    if start in ['y', 'yes']:
                        if await start_deployment(self.context.workspace.workspace_id, dep_id):
                            printer.print("✅ Deployment started")
                        else:
                            printer.print("❌ Failed to start deployment")
                
                return True
            else:
                printer.print("❌ Failed to sync deployment")
                return False
                
        except Exception as e:
            printer.print(f"❌ Error syncing: {e}")
            return False