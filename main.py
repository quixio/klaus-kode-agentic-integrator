# main.py - Refactored with dependency injection

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from agents import RunConfig
import argparse

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
            monitor_choice = printer.input("Would you like to monitor the deployment status and logs? (y/n): ").strip().lower()
            
            if monitor_choice in ['y', 'yes']:
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
        printer.print("\n" + "="*50)
        response = printer.input("Would you like to run another workflow? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
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
            monitor_choice = printer.input("Would you like to monitor the deployment status and logs? (y/n): ").strip().lower()
            
            if monitor_choice in ['y', 'yes']:
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
        printer.print("\n" + "="*50)
        response = printer.input("Would you like to run another workflow? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
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
    
    async def run(self):
        """Execute the workflow with triage agent for workflow selection."""
        while True:
            # Run triage to select workflow
            selected_workflow = self.triage_agent.run_triage()
            
            if selected_workflow is None:
                # User chose to quit
                return
            
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
            printer.print("https://portal.cloud.quix.io/signup?utm_campaign=ai-data-integrator")
        
        return
    
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
        response = input("   Continue anyway? (y/n): ").strip().lower()
        if response not in ['y', 'yes']:
            printer.print("👋 Exiting. Please install Claude Code CLI and try again.")
            return
    
    # Enable debug mode via environment variable or always on for development
    debug_mode = os.environ.get('DEBUG_MODE', 'true').lower() == 'true'
    
    # Create and run workflow orchestrator - with loop for retrying
    while True:
        workflow = WorkflowOrchestrator(debug_mode=debug_mode)
        
        try:
            success = await workflow.run()
            workflow_logger.info("=" * 60)
            if success:
                workflow_logger.info("KLAUS KODE COMPLETED")
            else:
                workflow_logger.info("KLAUS KODE STOPPED")
            workflow_logger.info(f"End time: {datetime.now()}")
            workflow_logger.info("=" * 60)
            
            # If user chose to quit, exit the loop
            if success is None or not success:
                break
                
        except KeyboardInterrupt:
            printer.print("\n\n⚠️ Workflow interrupted by user.")
            workflow_logger.info("=" * 60)
            workflow_logger.info("KLAUS KODE INTERRUPTED BY USER")
            workflow_logger.info(f"End time: {datetime.now()}")
            workflow_logger.info("=" * 60)
            
            printer.print("\n" + "="*50)
            response = printer.input("Would you like to run another workflow? (y/n): ").strip().lower()
            if response not in ['y', 'yes']:
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
            printer.print("\n" + "="*50)
            response = printer.input("Would you like to run another workflow? (y/n): ").strip().lower()
            if response not in ['y', 'yes']:
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
    args = parser.parse_args()
    
    # Set environment variables based on arguments
    if args.verbose:
        os.environ['VERBOSE_MODE'] = 'true'
    if args.debug:
        os.environ['DEBUG_MODE'] = 'true'
    
    # Run the main async function
    asyncio.run(main())