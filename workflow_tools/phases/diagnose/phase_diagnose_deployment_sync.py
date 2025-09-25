# phase_diagnose_deployment_sync.py - Deployment Sync Phase for Diagnose Workflow

import asyncio
from typing import Optional, List, Dict, Any
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.integrations.quix_tools import (
    list_deployments,
    sync_deployment,
    get_deployment_details,
    start_deployment,
    QuixApiError
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
            result = await self.standard_deployment.run()
            # Convert bool result to PhaseResult if needed
            if isinstance(result, bool):
                if result:
                    return PhaseResult(success=True, message="New deployment created successfully")
                else:
                    return PhaseResult(success=False, message="Failed to create new deployment")
            return result
            
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
        from workflow_tools.core.questionary_utils import select
        from workflow_tools.common import clear_screen, get_user_approval

        # Clear screen for menu
        clear_screen()
        
        # Build menu choices for questionary
        choices = []
        deployment_map = {}

        # Add existing deployments
        for i, dep in enumerate(deployments):
            name = dep.get('name', 'Unnamed')
            status = dep.get('status', 'Unknown')
            dep_id = dep.get('deploymentId', f'dep_{i}')

            status_emoji = {
                'Running': '🟢',
                'Stopped': '🔴',
                'Starting': '🟡',
                'Error': '❌'
            }.get(status, '⚪')

            display_text = f"{status_emoji} {name} ({status})"
            choices.append({'name': display_text, 'value': dep_id})
            deployment_map[dep_id] = dep

        # Add action options
        choices.append({'name': '🆕 Create new deployment', 'value': 'NEW'})
        choices.append({'name': '⏭️ Skip deployment', 'value': 'SKIP'})
        choices.append({'name': '⬅️ Go back', 'value': 'BACK'})
        
        # Display title and get selection
        printer.print(f"Found {len(deployments)} existing deployment(s) based on this application.")
        printer.print("Select deployment to sync or choose an action:")
        printer.print("")

        selected_value = select("", choices, show_border=False)

        # Handle selections
        if selected_value == 'BACK':
            return None
        elif selected_value == 'NEW':
            return 'new'
        elif selected_value == 'SKIP':
            return 'skip'
        else:
            # Return the selected deployment
            return deployment_map[selected_value]
    
    async def _sync_deployment(self, deployment: Dict[str, Any]) -> bool:
        """Sync a specific deployment with the latest code."""
        try:
            dep_name = deployment.get('name', 'Unnamed')
            dep_id = deployment.get('deploymentId')
            
            printer.print(f"\n🔄 Syncing deployment '{dep_name}'...")

            # Perform the sync with error handling
            try:
                result = await sync_deployment(dep_id)

                if result:
                    printer.print(f"✅ Deployment synced successfully!")
            except (QuixApiError, Exception) as sync_error:
                # Handle WorkspaceOutOfSync and other sync errors gracefully
                error_msg = str(sync_error)
                if "WorkspaceOutOfSync" in error_msg:
                    printer.print("⚠️ Workspace is out of sync. Performing workspace sync first...")

                    # Perform workspace sync via API
                    try:
                        from workflow_tools.integrations.quix_tools import sync_workspace_before_deployment
                        sync_result = await sync_workspace_before_deployment(self.context.workspace.workspace_id)
                        if sync_result:
                            printer.print("✅ Workspace synced successfully")

                            # Now retry the deployment sync
                            printer.print(f"🔄 Retrying deployment sync for '{dep_name}'...")
                            result = await sync_deployment(dep_id)
                            if result:
                                printer.print(f"✅ Deployment synced successfully!")
                        else:
                            printer.print("⚠️ Workspace sync failed, continuing anyway...")
                            result = False
                    except Exception as ws_error:
                        printer.print(f"⚠️ Could not sync workspace: {ws_error}")
                        printer.print("   Continuing anyway...")
                        result = False
                else:
                    printer.print(f"⚠️ Warning: Failed to sync deployment: {sync_error}")
                    printer.print("   Continuing anyway...")
                    result = False
                
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
                    if get_user_approval("Start it now?"):
                        try:
                            if await start_deployment(self.context.workspace.workspace_id, dep_id):
                                printer.print("✅ Deployment started")
                            else:
                                printer.print("❌ Failed to start deployment")
                        except (QuixApiError, Exception) as start_error:
                            error_msg = str(start_error)
                            if "WorkspaceOutOfSync" in error_msg:
                                printer.print("⚠️ Workspace is out of sync. Performing workspace sync first...")

                                # Perform workspace sync and retry
                                try:
                                    from workflow_tools.integrations.quix_tools import sync_workspace_before_deployment
                                    sync_result = await sync_workspace_before_deployment(self.context.workspace.workspace_id)
                                    if sync_result:
                                        printer.print("✅ Workspace synced successfully")
                                        printer.print("🔄 Retrying deployment start...")

                                        if await start_deployment(self.context.workspace.workspace_id, dep_id):
                                            printer.print("✅ Deployment started")
                                        else:
                                            printer.print("❌ Failed to start deployment")
                                    else:
                                        printer.print("❌ Workspace sync failed, cannot start deployment")
                                except Exception as ws_error:
                                    printer.print(f"❌ Could not sync workspace: {ws_error}")
                            else:
                                printer.print(f"❌ Failed to start deployment: {start_error}")

            return True
                
        except Exception as e:
            printer.print(f"❌ Error syncing: {e}")
            return False