# phase_deployment.py - Deployment Management Phase

import random
import string
from workflow_tools.common import WorkflowContext, printer, get_user_approval
from workflow_tools.integrations import quix_tools
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.core.url_builder import QuixPortalURLBuilder

class DeploymentPhase(BasePhase):
    """Handles application deployment."""
    
    phase_name = "deployment"
    phase_description = "Deploy application to production"
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        super().__init__(context, debug_mode)
    
    
    async def execute(self) -> PhaseResult:
        """Deploy the application and start the deployment."""
        printer.print("\n--- Phase 3: Production Deployment ---")
        
        # Check required context fields with specific error messages
        missing_fields = []
        if not self.context.workspace.workspace_id:
            missing_fields.append("workspace_id")
        if not self.context.deployment.application_id:
            missing_fields.append("application_id")
        
        if missing_fields:
            printer.print(f"🛑 Critical context missing for deployment: {', '.join(missing_fields)}")
            printer.print("Expected context fields:")
            printer.print(f"  - workspace_id: '{self.context.workspace.workspace_id}'")
            printer.print(f"  - application_id: '{self.context.deployment.application_id}'")
            return PhaseResult(success=False, message=f"Missing required fields: {', '.join(missing_fields)}")
        
        # Ask user if they want to deploy
        if not get_user_approval("Would you like to deploy this application to production?"):
            printer.print("🔄 Deployment skipped by user choice.")
            return PhaseResult(success=True, message="Deployment skipped by user choice")
        
        # Generate deployment name based on application
        base_deployment_name = f"{self.context.technology.destination_technology or 'sink'}-deployment"
        # Add random suffix to ensure uniqueness
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        self.context.deployment.deployment_name = f"{base_deployment_name}-{random_suffix}"
        
        # Get deployment configuration from user
        from workflow_tools.common import clear_screen
        clear_screen()
        
        printer.print(f"\n--- Deployment Configuration ---")
        printer.print(f"Default deployment name: {self.context.deployment.deployment_name}")
        
        custom_name = printer.input("Enter custom deployment name (or press Enter to use default): ").strip()
        if custom_name:
            self.context.deployment.deployment_name = custom_name
        
        # Resource configuration with sensible defaults for a sink
        replicas = 1
        cpu_millicores = 200  # 0.2 CPU cores
        memory_in_mb = 500    # 500 MB RAM
        
        # Ask user if they want to customize resources
        if get_user_approval("Would you like to customize resource allocation (CPU/Memory)?"):
            try:
                cpu_input = printer.input(f"CPU millicores (current: {cpu_millicores}, e.g. 200 = 0.2 cores): ").strip()
                if cpu_input:
                    cpu_millicores = int(cpu_input)
                
                memory_input = printer.input(f"Memory in MB (current: {memory_in_mb}): ").strip()
                if memory_input:
                    memory_in_mb = int(memory_input)
                
                replicas_input = printer.input(f"Number of replicas (current: {replicas}): ").strip()
                if replicas_input:
                    replicas = int(replicas_input)
            except ValueError:
                printer.print("⚠️ Invalid input, using default values")
        
        try:
            # Sync workspace to latest commit before deployment
            printer.print("\n🔄 Syncing workspace to latest commit...")
            sync_success = await quix_tools.sync_workspace_before_deployment(self.context.workspace.workspace_id)
            if not sync_success:
                printer.print("⚠️ Warning: Workspace sync failed, but continuing with deployment")
            else:
                printer.print("✅ Workspace synced successfully")
            
            printer.print(f"\n🚀 Creating deployment '{self.context.deployment.deployment_name}'...")
            
            # Get application details to retrieve variables
            app_details = await quix_tools.get_application_details(self.context.workspace.workspace_id, self.context.deployment.application_id)
            
            # Convert application variables to deployment variables format
            deployment_variables = {}
            if app_details and app_details.get('variables'):
                if self.debug_mode:
                    printer.print_debug(f"  - Raw application variables: {app_details.get('variables')}")
                for var in app_details['variables']:
                    var_name = var.get('name')
                    if var_name and var_name.strip():  # Ensure name is not empty or whitespace
                        deployment_variables[var_name] = {
                            "name": var_name,  # DeploymentVariable requires name field
                            "inputType": var.get('inputType', 'FreeText'),
                            "required": var.get('required', False),
                            "value": var.get('defaultValue', '') or ''  # Ensure value is never None
                        }
                        # For secrets, the value should be the secret key name (not the secret value)
                        if var.get('inputType') == 'Secret':
                            deployment_variables[var_name]["value"] = var.get('defaultValue', '') or ''
                    else:
                        printer.print_debug(f"  - Warning: Skipping variable with empty name: {var}")
                
                printer.print_verbose(f"  - Configuring {len(deployment_variables)} variables")
                if self.debug_mode:
                    printer.print_debug(f"  - Variables: {list(deployment_variables.keys())}")
                    printer.print_debug(f"  - Deployment variables structure: {deployment_variables}")
            
            # Note: No need to commit files here - the sandbox phase has already updated
            # the session with production-ready code via update_session_file().
            # Deployments will use whatever is in the session (committed or uncommitted).
            # The previous commit attempt was failing with 500 errors because it was trying
            # to commit unchanged content.
            
            # Create the deployment
            deployment = await quix_tools.create_deployment(
                workspace_id=self.context.workspace.workspace_id,
                application_id=self.context.deployment.application_id,
                name=self.context.deployment.deployment_name,
                replicas=replicas,
                cpu_millicores=cpu_millicores,
                memory_in_mb=memory_in_mb,
                use_latest=True,
                variables=deployment_variables if deployment_variables else None
            )
            
            if not deployment or not deployment.get('deploymentId'):
                printer.print("🛑 Failed to create deployment. Aborting.")
                return PhaseResult(success=False, message="Failed to create deployment")
            
            self.context.deployment.deployment_id = deployment.get('deploymentId')
            printer.print(f"✅ Deployment created: {deployment.get('name')}")
            
            # Sync the deployment to ensure it uses the latest code
            printer.print(f"🔄 Syncing deployment to use latest code...")
            try:
                sync_result = await quix_tools.sync_deployment(self.context.deployment.deployment_id)
                if sync_result:
                    printer.print(f"✅ Deployment synced successfully")
                    if self.debug_mode and sync_result.get('updateStatus'):
                        printer.print_debug(f"   Update status: {sync_result.get('updateStatus')}")
                else:
                    printer.print("⚠️ Warning: Deployment sync returned no result, but continuing")
            except Exception as e:
                printer.print(f"⚠️ Warning: Failed to sync deployment: {e}")
                printer.print("   Continuing with deployment start...")
            
            # Log the deployment URL
            url_builder = QuixPortalURLBuilder()
            deployment_url = url_builder.get_deployment_url(
                workspace=self.context.workspace.workspace_id,
                deployment_id=self.context.deployment.deployment_id
            )
            printer.print(f"🔗 Deployment URL: {deployment_url}")
            
            # Get deployment details
            details = await quix_tools.get_deployment_details(self.context.workspace.workspace_id, self.context.deployment.deployment_id)
            if details and self.debug_mode:
                printer.print_debug(f"   Application: {details.get('applicationName')} (ID: {details.get('applicationId')})")
                printer.print_debug(f"   Resources: {details.get('cpuMillicores')}m CPU, {details.get('memoryInMb')}MB RAM, {details.get('replicas')} replica(s)")
            
            # Start the deployment
            await quix_tools.start_deployment(self.context.workspace.workspace_id, self.context.deployment.deployment_id)
            printer.print(f"✅ Deployment started")
            
            # Check final status
            final_details = await quix_tools.get_deployment_details(self.context.workspace.workspace_id, self.context.deployment.deployment_id)
            if final_details:
                status = final_details.get('status', 'Unknown')
                if status != 'Running':
                    printer.print(f"   Status: {status}")
                if final_details.get('statusReason'):
                    printer.print(f"   Reason: {final_details.get('statusReason')}")
            
            printer.print(f"\n🎉 Deployment ready!")
            printer.print(f"   Monitor in Quix Portal: Deployments section")
            
            return PhaseResult(success=True, message=f"Deployment '{self.context.deployment.deployment_name}' created successfully")
            
        except quix_tools.QuixApiError as e:
            error_msg = str(e)
            if "WorkspaceOutOfSync" in error_msg:
                printer.print("⚠️ Workspace is out of sync. Performing workspace sync...")

                # Try to sync workspace and retry
                try:
                    sync_result = await quix_tools.sync_workspace_before_deployment(self.context.workspace.workspace_id)
                    if sync_result:
                        printer.print("✅ Workspace synced successfully")
                        printer.print("🔄 Retrying deployment start...")

                        # Retry starting the deployment
                        try:
                            await quix_tools.start_deployment(self.context.workspace.workspace_id, self.context.deployment.deployment_id)
                            printer.print(f"✅ Deployment started after sync")
                            return PhaseResult(success=True, message=f"Deployment '{self.context.deployment.deployment_name}' created successfully (after sync)")
                        except Exception as retry_error:
                            printer.print(f"🛑 Failed to start deployment after sync: {retry_error}")
                            return PhaseResult(success=False, message=f"Failed after sync: {retry_error}")
                    else:
                        printer.print("🛑 Workspace sync failed")
                        return PhaseResult(success=False, message="Workspace sync failed")
                except Exception as sync_error:
                    printer.print(f"🛑 Could not sync workspace: {sync_error}")
                    return PhaseResult(success=False, message=f"Workspace sync error: {sync_error}")
            else:
                printer.print(f"🛑 Failed to deploy application: {e}")
                return PhaseResult(success=False, message=f"API error: {e}")
        except Exception as e:
            printer.print(f"🛑 Unexpected error during deployment: {e}")
            return PhaseResult(success=False, message=f"Unexpected error: {e}")