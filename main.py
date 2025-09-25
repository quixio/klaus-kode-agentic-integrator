# main.py - Refactored with dependency injection

import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from agents import RunConfig
import argparse
from typing import Optional

# Suppress LiteLLM's verbose logging about missing proxy dependencies
# This must happen before any imports that might load LiteLLM
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("litellm").setLevel(logging.CRITICAL)
logging.getLogger("LiteLLM.litellm_logging").setLevel(logging.CRITICAL)
logging.getLogger("litellm.litellm_logging").setLevel(logging.CRITICAL)

# Suppress asyncio errors on exit
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# Import refactored components
from workflow_tools import (
    WorkflowContext,
    ServiceContainer,
    WorkflowFactory,
    printer,
    workflow_logger,
    WorkflowType,
    WorkflowInfo,
    TriageAgent,
    PlaceholderWorkflowFactory,
)
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.services.claude_code_service import ClaudeCodeService

# Configure the agents SDK to not require OpenAI key
# Since we're using Anthropic exclusively, we disable OpenAI tracing and provide a dummy key
from agents import set_default_openai_key, set_tracing_disabled

# Disable tracing completely so nothing tries to talk to OpenAI
set_tracing_disabled(True)

# Feed it a dummy key to silence any "missing key" checks inside the library
set_default_openai_key("dummy-key-not-used", use_for_tracing=False)

load_dotenv()

class WorkflowOrchestrator:
    """Main workflow orchestrator using dependency injection and factory pattern."""
    
    def __init__(self, debug_mode: bool = False):
        """Initialize the orchestrator with dependency injection."""
        # Create service container
        self.container = ServiceContainer()
        
        # Create and register core services
        self.context = WorkflowContext()
        self.run_config = RunConfig(workflow_name="Klaus Kode")
        self.debug_mode = debug_mode
        
        # Register all services in the container
        WorkflowFactory.register_services(
            self.container, 
            self.context, 
            self.run_config, 
            self.debug_mode
        )
        
        # Initialize triage agent
        self.triage_agent = TriageAgent(self.context, debug_mode)
    
    async def run_sink_workflow(self):
        """Execute the sink workflow using factory-created phases."""
        # Start sink workflow directly
        
        # Execute phases in sequence with back navigation support
        phase_index = 0
        total_phases = 7  # Total number of phases in sink workflow
        while phase_index < total_phases - 1:  # All phases except monitoring
            try:
                # Create fresh phase instances for each run (important for navigation)
                phases = WorkflowFactory.create_sink_workflow(self.container)
                phase = phases[phase_index]
                if not await phase.run():
                    return False
                phase_index += 1  # Move to next phase on success
            except NavigationBackRequest:
                # User requested to go back
                if phase_index > 0:
                    phase_index -= 1  # Go back to previous phase
                    printer.print("\n⬅️ Going back to previous phase...\n")
                else:
                    # At first phase - go back to workflow selection
                    printer.print("\n⬅️ Going back to workflow selection...\n")
                    return 'back_to_triage'  # Special return value to signal going back to triage
        
        # Handle deployment monitoring separately (it's optional)
        # Create fresh instances for the final phases
        final_phases = WorkflowFactory.create_sink_workflow(self.container)
        deployment_phase = final_phases[-2]  # Deployment is second to last
        monitoring_phase = final_phases[-1]  # Monitoring is last
        
        if self.context.deployment.deployment_id:
            printer.print(f"\n🔍 Deployment initiated successfully!")
            printer.print(f"   Deployment ID: {self.context.deployment.deployment_id}")
            printer.print(f"   Deployment Name: {self.context.deployment.deployment_name}")
            printer.print("")
            
            # Ask user if they want to monitor the deployment
            from workflow_tools.common import get_user_approval
            monitor_deployment = get_user_approval("Would you like to monitor the deployment status and logs?")
            
            if monitor_deployment:
                if not await monitoring_phase.run():
                    printer.print("⚠️  Deployment monitoring encountered issues, but the deployment may still be functional.")
                    printer.print("   Check the Quix Portal for more details.")
            else:
                printer.print("✅ Deployment monitoring skipped.")
                printer.print("   You can monitor the deployment manually in the Quix Portal under Deployments.")
        
        # Workflow completion
        deployment_status = getattr(self.context.deployment, 'deployment_status', None)
        
        if deployment_status in ["BuildFailed", "RuntimeError"]:
            printer.print("\n⚠️  Workflow completed with deployment issues.")
            printer.print(f"   Deployment '{self.context.deployment.deployment_name}' encountered problems.")
            printer.print(f"   Status: {deployment_status}")
            printer.print("   Please review the error analysis and fix the issues before redeploying.")
        elif self.context.deployment.deployment_id:
            printer.print("\n🎉 Complete workflow finished successfully!")
            printer.print(f"   Your sink deployment: {self.context.deployment.deployment_name}")
            if deployment_status == "Running":
                printer.print("   Status: Running ✅")
            printer.print(f"   Monitor it in the Quix Portal under Deployments.")
        else:
            printer.print("\n✅ Workflow completed.")
            printer.print("   Sandbox testing completed successfully. Deployment was skipped.")
        
        # Ask if user wants to run another workflow
        printer.print_divider()
        from workflow_tools.common import get_user_approval
        run_another = get_user_approval("Would you like to run another workflow?")
        if run_another:
            # Reset context for new workflow
            self.context = WorkflowContext()
            # Re-register services with fresh context
            WorkflowFactory.register_services(
                self.container, 
                self.context, 
                self.run_config, 
                self.debug_mode
            )
            return 'back_to_triage'
        
        return True
    
    async def run_source_workflow(self):
        """Execute the source workflow using factory-created phases."""
        # Start source workflow directly
        
        # Execute phases in sequence with back navigation support
        phase_index = 0
        total_phases = 8  # Total number of phases in source workflow
        while phase_index < total_phases - 1:  # All phases except monitoring
            try:
                # Create fresh phase instances for each run (important for navigation)
                phases = WorkflowFactory.create_source_workflow(self.container)
                phase = phases[phase_index]
                
                # Skip connection testing and schema phases if flag is set (for cached schema analysis)
                if (hasattr(self.context, 'skip_connection_testing') and 
                    self.context.skip_connection_testing and 
                    phase.phase_name in ["source_connection_testing", "source_schema"]):
                    printer.print(f"⏭️ Skipping {phase.phase_description} phase (using cached schema analysis)")
                    phase_index += 1  # Move to next phase
                    continue
                
                if not await phase.run():
                    return False
                phase_index += 1  # Move to next phase on success
            except NavigationBackRequest:
                # User requested to go back
                if phase_index > 0:
                    phase_index -= 1  # Go back to previous phase
                    printer.print("\n⬅️ Going back to previous phase...\n")
                else:
                    # At first phase - go back to workflow selection
                    printer.print("\n⬅️ Going back to workflow selection...\n")
                    return 'back_to_triage'  # Special return value to signal going back to triage
        
        # Handle deployment monitoring separately (it's optional)
        # Create fresh instance for the monitoring phase
        final_phases = WorkflowFactory.create_source_workflow(self.container)
        monitoring_phase = final_phases[-1]
        
        if self.context.deployment.deployment_id:
            printer.print(f"\n🔍 Deployment initiated successfully!")
            printer.print(f"   Deployment ID: {self.context.deployment.deployment_id}")
            printer.print(f"   Deployment Name: {self.context.deployment.deployment_name}")
            printer.print("")
            
            # Ask user if they want to monitor the deployment
            from workflow_tools.common import get_user_approval
            monitor_deployment = get_user_approval("Would you like to monitor the deployment status and logs?")
            
            if monitor_deployment:
                if not await monitoring_phase.run():
                    printer.print("⚠️  Deployment monitoring encountered issues, but the deployment may still be functional.")
                    printer.print("   Check the Quix Portal for more details.")
            else:
                printer.print("✅ Deployment monitoring skipped.")
                printer.print("   You can monitor the deployment manually in the Quix Portal under Deployments.")
        
        # Workflow completion
        printer.print("\n🎉 Complete source workflow finished successfully!")
        if self.context.deployment.deployment_id:
            printer.print(f"   Your source deployment: {self.context.deployment.deployment_name}")
            printer.print(f"   Monitor it in the Quix Portal under Deployments.")
        else:
            printer.print("   Sandbox testing completed successfully. Deployment was skipped.")
        
        # Ask if user wants to run another workflow
        printer.print_divider()
        from workflow_tools.common import get_user_approval
        run_another = get_user_approval("Would you like to run another workflow?")
        if run_another:
            # Reset context for new workflow
            self.context = WorkflowContext()
            # Re-register services with fresh context
            WorkflowFactory.register_services(
                self.container, 
                self.context, 
                self.run_config, 
                self.debug_mode
            )
            return 'back_to_triage'
        
        return True

    async def run_diagnose_workflow(self):
        """Execute the diagnose workflow using factory-created phases."""
        from workflow_tools.core.navigation import NavigationManager, DiagnoseWorkflowSteps

        # Initialize navigation manager for fine-grained control
        nav_manager = NavigationManager('diagnose')

        # Map steps to phase indices for navigation
        step_to_phase = {
            DiagnoseWorkflowSteps.APP_SELECTION_START: 0,
            DiagnoseWorkflowSteps.SELECT_WORKSPACE: 0,
            DiagnoseWorkflowSteps.SELECT_APPLICATION: 0,
            DiagnoseWorkflowSteps.APP_DOWNLOAD_START: 1,
            DiagnoseWorkflowSteps.DOWNLOAD_APP: 1,
            DiagnoseWorkflowSteps.ANALYZE_APP: 1,
            DiagnoseWorkflowSteps.CHOOSE_ACTION: 1,
            DiagnoseWorkflowSteps.EDIT_START: 2,
            DiagnoseWorkflowSteps.PROVIDE_CONTEXT: 2,
            DiagnoseWorkflowSteps.CHOOSE_EDIT_OR_RUN: 2,
            DiagnoseWorkflowSteps.EDIT_CODE: 2,
            DiagnoseWorkflowSteps.SANDBOX_START: 3,
            DiagnoseWorkflowSteps.TEST_IN_SANDBOX: 3,
            DiagnoseWorkflowSteps.DEBUG_ISSUES: 3,
            DiagnoseWorkflowSteps.FOLLOW_UP_IMPROVEMENTS: 3,
            DiagnoseWorkflowSteps.DEPLOYMENT_START: 4,
            DiagnoseWorkflowSteps.SELECT_DEPLOYMENT: 4,
            DiagnoseWorkflowSteps.SYNC_DEPLOYMENT: 4,
        }

        # Execute phases in sequence with fine-grained navigation support
        phase_index = 0
        total_phases = 6  # Total number of phases in diagnose workflow
        while phase_index < total_phases - 1:  # All phases except monitoring
            try:
                # Create fresh phase instances for each run (important for navigation)
                phases = WorkflowFactory.create_diagnose_workflow(self.container)
                phase = phases[phase_index]
                if not await phase.run():
                    return False
                phase_index += 1  # Move to next phase on success
            except NavigationBackRequest:
                # Check if there's a specific navigation request
                if hasattr(self.context, 'navigation_request') and self.context.navigation_request:
                    nav_request = self.context.navigation_request
                    target_step = nav_request.target_step

                    # Find the phase index for the target step
                    if target_step in step_to_phase:
                        target_phase = step_to_phase[target_step]
                        if target_phase != phase_index:
                            phase_index = target_phase
                            printer.print(f"\n⬅️ {nav_request.message or 'Going back to requested step...'}\n")
                        # Clear the navigation request
                        self.context.navigation_request = None
                        continue

                    # Clear navigation request if we can't handle it
                    self.context.navigation_request = None

                # Fall back to simple phase-by-phase navigation
                if phase_index > 0:
                    phase_index -= 1  # Go back to previous phase
                    printer.print("\n⬅️ Going back to previous phase...\n")
                else:
                    # At first phase - go back to workflow selection
                    printer.print("\n⬅️ Going back to workflow selection...\n")
                    return 'back_to_triage'  # Special return value to signal going back to triage

        # Handle deployment monitoring separately (it's optional)
        # Create fresh instance for the monitoring phase
        final_phases = WorkflowFactory.create_diagnose_workflow(self.container)
        monitoring_phase = final_phases[-1]

        if self.context.deployment.deployment_id:
            printer.print(f"\n🔍 Deployment initiated successfully!")
            printer.print(f"   Deployment ID: {self.context.deployment.deployment_id}")
            printer.print(f"   Deployment Name: {self.context.deployment.deployment_name}")
            printer.print("")

            # Ask user if they want to monitor the deployment
            from workflow_tools.common import get_user_approval
            monitor_deployment = get_user_approval("Would you like to monitor the deployment status and logs?")

            if monitor_deployment:
                if not await monitoring_phase.run():
                    printer.print("⚠️  Deployment monitoring encountered issues, but the deployment may still be functional.")
                    printer.print("   Check the Quix Portal for more details.")
            else:
                printer.print("✅ Deployment monitoring skipped.")
                printer.print("   You can monitor the deployment manually in the Quix Portal under Deployments.")

        # Workflow completion
        deployment_status = getattr(self.context.deployment, 'deployment_status', None)

        if deployment_status in ["BuildFailed", "RuntimeError"]:
            printer.print("\n⚠️  Workflow completed with deployment issues.")
            printer.print(f"   Deployment '{self.context.deployment.deployment_name}' encountered problems.")
            printer.print(f"   Status: {deployment_status}")
            printer.print("   Please review the error analysis and fix the issues before redeploying.")
        elif self.context.deployment.deployment_id:
            printer.print("\n🎉 Complete diagnose workflow finished successfully!")
            printer.print(f"   Your updated deployment: {self.context.deployment.deployment_name}")
            if deployment_status == "Running":
                printer.print("   Status: Running ✅")
            printer.print(f"   Monitor it in the Quix Portal under Deployments.")
        else:
            printer.print("\n✅ Diagnose workflow completed.")
            printer.print("   Application was fixed and tested successfully. Deployment was skipped.")

        # Ask if user wants to run another workflow
        printer.print_divider()
        from workflow_tools.common import get_user_approval
        run_another = get_user_approval("Would you like to run another workflow?")
        if run_another:
            # Reset context for new workflow
            self.context = WorkflowContext()
            # Re-register services with fresh context
            WorkflowFactory.register_services(
                self.container,
                self.context,
                self.run_config,
                self.debug_mode
            )
            return 'back_to_triage'

        return True

    async def handle_workspace_configuration(self):
        """Handle workspace configuration from main menu."""
        from workflow_tools.services.prerequisites_collector import PrerequisitesCollector
        from workflow_tools.core.questionary_utils import select, clear_screen

        # Clear screen before showing workspace menu
        clear_screen()

        printer.print_section_header("Default Project/Environment Configuration", icon="⚙️", style="cyan")
        printer.print("")

        # Get current workspace if set
        current_workspace = os.environ.get('QUIX_WORKSPACE_ID')
        if current_workspace:
            printer.print(f"Current default workspace: {current_workspace}")
            printer.print("")

        # Get list of workspaces
        printer.print("Fetching available workspaces...")
        from workflow_tools.integrations import quix_tools
        workspaces_df = await quix_tools.find_workspaces()

        if workspaces_df.empty:
            printer.print("❌ No workspaces found.")
            printer.input("\nPress Enter to continue...")
            return

        # Convert dataframe to choices for questionary
        choices = []
        workspace_map = {}
        for _, row in workspaces_df.iterrows():
            workspace_id = row['Workspace ID']
            display_name = f"{row['Workspace Name']}\n      {workspace_id}"
            if workspace_id == current_workspace:
                display_name += " (current)"
            choices.append({'name': display_name, 'value': workspace_id})
            workspace_map[workspace_id] = row.to_dict()

        # Add option to clear default
        if current_workspace:
            choices.append({'name': '❌ Clear default workspace', 'value': 'CLEAR'})

        # Add back option
        choices.append({'name': '← Go back', 'value': 'back'})

        selected_id = select("📋 Select Default Workspace", choices, show_border=True)

        # Check if user wants to go back
        if selected_id == 'back':
            return

        # Check if user wants to clear
        if selected_id == 'CLEAR':
            # Remove from .env file
            self._update_env_file('QUIX_WORKSPACE_ID', '')
            if 'QUIX_WORKSPACE_ID' in os.environ:
                del os.environ['QUIX_WORKSPACE_ID']
            printer.print("✅ Default workspace cleared. You'll be prompted to select one for each workflow.")
            printer.input("\nPress Enter to continue...")
            return

        # Update the default workspace
        if self._update_env_file('QUIX_WORKSPACE_ID', selected_id):
            selected_workspace = workspace_map[selected_id]
            printer.print(f"✅ Default workspace updated to: {selected_workspace['Workspace Name']}")
            printer.print(f"   Workspace ID: {selected_id}")
        else:
            printer.print("❌ Failed to update default workspace")

        printer.input("\nPress Enter to continue...")

    def _update_env_file(self, key: str, value: str) -> bool:
        """Update or add an environment variable in the .env file."""
        try:
            env_path = '.env'

            # Read existing content
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []

            # Check if key already exists
            key_found = False
            for i, line in enumerate(lines):
                # Skip comments
                if line.strip().startswith('#'):
                    continue

                # Check if this line contains our key
                if line.strip().startswith(f'{key}='):
                    if value:
                        lines[i] = f'{key}={value}\n'
                    else:
                        # Remove the line if value is empty
                        lines.pop(i)
                    key_found = True
                    break

            # If key not found and value is not empty, append it
            if not key_found and value:
                # Ensure there's a newline at the end
                if lines and not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
                lines.append(f'{key}={value}\n')

            # Write back to file
            with open(env_path, 'w') as f:
                f.writelines(lines)

            # Also update the current environment
            if value:
                os.environ[key] = value

            return True

        except Exception as e:
            printer.print(f"⚠️ Error updating .env file: {e}")
            return False

    async def run(self):
        """Execute the workflow with triage agent for workflow selection."""
        while True:
            # Run triage to select workflow
            selected_workflow = self.triage_agent.run_triage()
            if selected_workflow is None:
                # User chose to quit - exit cleanly
                return None

            # Handle workspace configuration
            if selected_workflow == 'WORKSPACE_CONFIG':
                await self.handle_workspace_configuration()
                continue  # Go back to main menu

            # Store selected workflow in context
            self.context.selected_workflow = selected_workflow

            # Route to appropriate workflow
            if selected_workflow == WorkflowType.SINK:
                # Run the implemented sink workflow
                result = await self.run_sink_workflow()
                if result == 'back_to_triage':
                    continue  # Go back to workflow selection
                return result
            
            elif selected_workflow == WorkflowType.SOURCE:
                # Run the implemented source workflow
                result = await self.run_source_workflow()
                if result == 'back_to_triage':
                    continue  # Go back to workflow selection
                return result
            
            elif selected_workflow == WorkflowType.DIAGNOSE:
                # Run the implemented diagnose workflow
                result = await self.run_diagnose_workflow()
                if result == 'back_to_triage':
                    continue  # Go back to workflow selection
                return result
            
            elif WorkflowInfo.is_implemented(selected_workflow):
                # Future: Add other implemented workflows here
                printer.print(f"🛑 Error: {WorkflowInfo.get_name(selected_workflow)} is marked as implemented but no handler found.")
                return
            
            else:
                # Run placeholder workflow
                placeholder = PlaceholderWorkflowFactory.create_placeholder(selected_workflow, self.context, self.debug_mode)
                result = placeholder.run()
                
                if result == 'quit':
                    printer.print("👋 Goodbye!")
                    return
                elif result == 'back':
                    # Continue the loop to show triage again
                    continue
                else:
                    # Unexpected result
                    printer.print("🛑 Unexpected response from workflow.")
                    return

async def auto_detect_myproject_workspace():
    """Auto-detect and configure MyProject workspace for first-time users."""
    import re
    from workflow_tools.integrations import quix_tools

    try:
        workspaces_df = await quix_tools.find_workspaces()
        if not workspaces_df.empty:
            # Look for MyProject workspace (case-insensitive)
            # Pattern: <prefix>-myproject-production
            myproject_pattern = re.compile(r'.*-myproject-production$', re.IGNORECASE)

            for _, row in workspaces_df.iterrows():
                workspace_id = row['Workspace ID']
                if myproject_pattern.match(workspace_id):
                    return workspace_id
    except Exception:
        pass  # Silently fail
    return None

async def main():
    """Main entry point for the application."""
    # Check verbose mode
    verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'

    # Log the workflow start
    workflow_logger.info("=" * 60)
    workflow_logger.info("KLAUS KODE STARTED")
    workflow_logger.info(f"Start time: {datetime.now()}")
    workflow_logger.info(f"Debug mode: {os.environ.get('DEBUG_MODE', 'true').lower() == 'true'}")
    workflow_logger.info(f"Verbose mode: {verbose_mode}")
    workflow_logger.info("=" * 60)
    
    # Print startup message to console (only essential info in non-verbose mode)
    if not verbose_mode:
        printer.print("")
        printer.print(" ██╗  ██╗██╗      █████╗ ██╗   ██╗███████╗    ██╗  ██╗ ██████╗ ██████╗ ███████╗")
        printer.print(" ██║ ██╔╝██║     ██╔══██╗██║   ██║██╔════╝    ██║ ██╔╝██╔═══██╗██╔══██╗██╔════╝")
        printer.print(" █████╔╝ ██║     ███████║██║   ██║███████╗    █████╔╝ ██║   ██║██║  ██║█████╗  ")
        printer.print(" ██╔═██╗ ██║     ██╔══██║██║   ██║╚════██║    ██╔═██╗ ██║   ██║██║  ██║██╔══╝  ")
        printer.print(" ██║  ██╗███████╗██║  ██║╚██████╔╝███████║    ██║  ██╗╚██████╔╝██████╔╝███████╗")
        printer.print(" ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝    ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝")
        printer.print("")
        printer.print("                    Klaus Kode—agentic data integrator")
        printer.print("                    (Press Ctrl+C twice to force quit)")
        printer.print("=" * 80)
    
    # Check required environment variables
    required_vars = ["ANTHROPIC_API_KEY", "QUIX_TOKEN", "QUIX_BASE_URL"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        printer.print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")

        # Special message for missing QUIX_TOKEN
        if "QUIX_TOKEN" in missing_vars:
            printer.print("")
            printer.print("No Quix PAT token detected.")
            printer.print("To get one, sign up for a free Quix account here:")
            printer.print_markup("[bold cyan][link=https://portal.cloud.quix.io/signup?utm_campaign=klaus-kode]https://portal.cloud.quix.io/signup?utm_campaign=klaus-kode[/link][/bold cyan]")

        return

    # Auto-detect MyProject workspace if QUIX_WORKSPACE_ID is not set
    if not os.environ.get('QUIX_WORKSPACE_ID'):
        printer.print("🔍 Checking for default MyProject workspace...")
        myproject_id = await auto_detect_myproject_workspace()
        if myproject_id:
            printer.print(f"✅ Found MyProject workspace: {myproject_id}")
            # Create a temporary orchestrator just to use its _update_env_file method
            temp_orchestrator = WorkflowOrchestrator(debug_mode=False)
            if temp_orchestrator._update_env_file('QUIX_WORKSPACE_ID', myproject_id):
                printer.print(f"✅ Default workspace configured: {myproject_id}")
                printer.print("   (You can change this later from the main menu)")
            else:
                # If .env update fails, at least set it in current session
                os.environ['QUIX_WORKSPACE_ID'] = myproject_id
                printer.print(f"⚠️ Could not write to .env file, but workspace set for this session: {myproject_id}")
                printer.print("   💡 To make this permanent, add this line to your .env file:")
                printer.print(f"      QUIX_WORKSPACE_ID={myproject_id}")
        else:
            printer.print("ℹ️ No default MyProject workspace found. You'll select one during workflow setup.")

    # Early check for Claude Code CLI availability
    printer.print("🔍 Checking Claude Code CLI installation...")
    
    # Create a minimal context just for CLI detection
    temp_context = WorkflowContext()
    try:
        # This will trigger the CLI detection during initialization
        claude_service = ClaudeCodeService(temp_context, debug_mode=False)
        if claude_service.claude_cli_path:
            printer.print(f"✅ Claude CLI configured at: {claude_service.claude_cli_path}")
        else:
            printer.print("✅ Claude CLI found in system PATH")
    except Exception as e:
        printer.print(f"⚠️ Warning: Claude Code CLI check failed: {e}")
        printer.print("   You may need to install or configure Claude CLI later.")
        from workflow_tools.common import get_user_approval
        if not get_user_approval("Continue anyway?"):
            printer.print("👋 Exiting. Please install Claude Code CLI and try again.")
            return
    
    # Enable debug mode via environment variable or always on for development
    debug_mode = os.environ.get('DEBUG_MODE', 'true').lower() == 'true'
    
    # Create and run workflow orchestrator - with loop for retrying
    while True:
        workflow = WorkflowOrchestrator(debug_mode=debug_mode)
        
        try:
            success = await workflow.run()

            # Only log completion if not quitting
            if success is not None:
                workflow_logger.info("=" * 60)
                if success:
                    workflow_logger.info("KLAUS KODE COMPLETED")
                else:
                    workflow_logger.info("KLAUS KODE STOPPED")
                workflow_logger.info(f"End time: {datetime.now()}")
                workflow_logger.info("=" * 60)

            # If user chose to quit, exit the loop cleanly
            if success is None:
                break
            elif not success:
                # Workflow failed, ask if they want to continue
                break
                
        except KeyboardInterrupt:
            printer.print("\n\n⚠️ Workflow interrupted by user.")
            workflow_logger.info("=" * 60)
            workflow_logger.info("KLAUS KODE INTERRUPTED BY USER")
            workflow_logger.info(f"End time: {datetime.now()}")
            workflow_logger.info("=" * 60)
            
            printer.print_divider()
            from workflow_tools.common import get_user_approval
            if not get_user_approval("Would you like to run another workflow?"):
                break
            # Otherwise, continue the loop to start fresh
            continue
            
        except Exception as e:
            workflow_logger.error("=" * 60)
            workflow_logger.error("KLAUS KODE FAILED")
            workflow_logger.error(f"Error: {e}")
            workflow_logger.error(f"End time: {datetime.now()}")
            workflow_logger.error("=" * 60)
            
            printer.print(f"\n❌ An error occurred: {e}")
            printer.print_divider()
            from workflow_tools.common import get_user_approval
            if not get_user_approval("Would you like to run another workflow?"):
                break
            # Otherwise, continue the loop to start fresh
            continue
        
        # If we get here without an exception, break the loop
        break

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Klaus Kode—agentic data integrator')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging (shows detailed API calls and debug info)')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug mode (saves intermediate files and shows additional info)')
    parser.add_argument('--workflow', '-w', type=int, choices=[1, 2, 3, 4],
                        help='Select workflow directly: 1=Source, 2=Sink, 3=Transform, 4=Diagnose')
    args = parser.parse_args()

    # Set environment variables based on arguments
    if args.verbose:
        os.environ['VERBOSE_MODE'] = 'true'
    if args.debug:
        os.environ['DEBUG_MODE'] = 'true'

    # Suppress asyncio error messages on exit
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    # Run the main async function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Silently exit on Ctrl+C
        pass
