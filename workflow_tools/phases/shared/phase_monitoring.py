# phase_monitoring.py - Deployment Monitoring Phase

import os
import asyncio
from typing import Optional
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.integrations.deployment_monitoring import DeploymentMonitor, DeploymentStatus

class MonitoringPhase(BasePhase):
    """Handles deployment monitoring and log analysis after deployment."""
    
    phase_name = "monitoring"
    phase_description = "Monitor deployment"
    
    def __init__(self, context: WorkflowContext, run_config=None, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.run_config = run_config
        self.monitor = DeploymentMonitor(context, run_config, debug_mode)
    
    async def execute(self) -> PhaseResult:
        """
        Monitor deployment status and analyze logs based on final status.
        
        Returns:
            True if monitoring completed successfully, False if error
        """
        if not self.context.deployment.deployment_id:
            printer.print("❌ No deployment ID found in context. Cannot monitor deployment.")
            return PhaseResult(success=False, message="No deployment ID found")
        
        printer.print("\n--- Deployment Monitoring Phase ---")
        printer.print("Now monitoring the deployment to ensure it's working properly.")
        
        # Poll deployment status until final state
        final_status = await self.monitor.poll_deployment_status(self.context.deployment.deployment_id)
        
        if final_status is None:
            printer.print("❌ Failed to get final deployment status.")
            return PhaseResult(success=False, message="Failed to get deployment status")
        
        # Handle different final statuses
        if final_status == DeploymentStatus.RUNNING.value:
            return await self._handle_running_status()
        elif final_status == DeploymentStatus.RUNTIME_ERROR.value:
            return await self._handle_runtime_error_status()
        elif final_status == DeploymentStatus.BUILD_FAILED.value:
            return await self._handle_build_failed_status()
        elif final_status in [DeploymentStatus.STOPPED.value, DeploymentStatus.COMPLETED.value]:
            return await self._handle_stopped_or_completed_status(final_status)
        else:
            # Store deployment status in context for other statuses
            self.context.deployment.deployment_status = final_status
            printer.print(f"🔍 Deployment reached status: {final_status}")
            printer.print("   Please check the Quix Portal for more details.")
            return PhaseResult(success=True, message=f"Deployment status: {final_status}")
    
    async def _handle_running_status(self) -> PhaseResult:
        """Handle Running status - check logs to ensure everything is working properly."""
        printer.print("\n✅ Deployment is running! Now monitoring logs to ensure everything is working properly.")
        printer.print("   This may take up to 60 seconds to capture startup errors.")
        
        # Store deployment status in context
        self.context.deployment.deployment_status = "Running"
        
        # Extended monitoring for comprehensive error detection - max 10 retries with 5 second intervals
        logs = await self._get_runtime_logs_with_retry(self.context.deployment.deployment_id, line_limit=200)
        
        if logs is None:
            printer.print("❌ Failed to retrieve runtime logs after retries.")
            return PhaseResult(success=False, message="Failed to retrieve runtime logs")
        
        if not logs.strip():
            printer.print("📝 No runtime logs available after waiting. The application may still be starting up.")
            printer.print("   Monitor the deployment in the Quix Portal for further updates.")
            return PhaseResult(success=True, message="No logs available yet")
        
        # Analyze logs with AI
        printer.print("🤖 Analyzing runtime logs with AI.")
        analysis = await self.monitor.analyze_logs_with_ai(logs, "runtime", "Running")
        
        # Display log analysis with Rich markdown formatting
        printer.print_markdown(
            analysis,
            title="📋 Log Analysis Results"
        )
        
        return PhaseResult(success=True, message="Deployment running successfully")
    
    async def _handle_runtime_error_status(self) -> PhaseResult:
        """Handle RuntimeError status - analyze logs and provide fix recommendations."""
        printer.print("\n❌ Deployment has a Runtime Error! Analyzing logs to determine the cause.")
        
        # Store deployment status in context
        self.context.deployment.deployment_status = "RuntimeError"
        
        # Get runtime logs with retry logic (shorter retry for errors - 3 retries)
        logs = await self._get_runtime_logs_with_retry(self.context.deployment.deployment_id, line_limit=100, max_retries=3)
        
        if logs is None:
            printer.print("❌ Failed to retrieve runtime logs after retries.")
            return PhaseResult(success=False, message="Failed to retrieve runtime logs")
        
        if not logs.strip():
            printer.print("📝 No runtime logs available after waiting. This might indicate the container failed to start.")
            printer.print("   Check the deployment configuration in the Quix Portal.")
            return PhaseResult(success=True, message="No runtime logs available")
        
        # Analyze logs with AI
        printer.print("🤖 Analyzing runtime logs to identify the error.")
        analysis = await self.monitor.analyze_logs_with_ai(logs, "runtime", "RuntimeError")
        
        # Save detailed analysis to file
        filename = f"runtime_error_analysis_{self.context.deployment.deployment_id}.md"
        filepath = self.monitor.save_analysis_to_file(analysis, filename)
        
        # Display runtime error analysis with Rich markdown formatting
        printer.print_markdown(
            analysis,
            title="⚠️ Runtime Error Analysis"
        )
        
        if filepath:
            printer.print(f"\n📄 Detailed analysis saved to: {filepath}")
            printer.print("   Please review the recommendations and fix the issues before redeploying.")
        
        return PhaseResult(success=True, message="Runtime error analyzed")
    
    async def _handle_build_failed_status(self) -> PhaseResult:
        """Handle BuildFailed status - analyze build logs and provide fix recommendations."""
        printer.print("\n❌ Deployment build failed! Analyzing build logs to determine the cause.")
        
        # Store deployment status in context
        self.context.deployment.deployment_status = "BuildFailed"
        
        # Get build logs
        build_logs = self.monitor.get_build_logs(self.context.deployment.deployment_id)
        
        if build_logs is None:
            printer.print("❌ Failed to retrieve build logs.")
            return PhaseResult(success=False, message="Failed to retrieve build logs")
        
        if not build_logs.strip():
            printer.print("📝 No build logs available.")
            printer.print("   Check the deployment configuration in the Quix Portal.")
            return PhaseResult(success=True, message="No build logs available")
        
        # Analyze logs with AI
        printer.print("🤖 Analyzing build logs to identify the build failure.")
        analysis = await self.monitor.analyze_logs_with_ai(build_logs, "build", "BuildFailed")
        
        # Save detailed analysis to file
        filename = f"build_failure_analysis_{self.context.deployment.deployment_id}.md"
        filepath = self.monitor.save_analysis_to_file(analysis, filename)
        
        # Display build failure analysis with Rich markdown formatting
        printer.print_markdown(
            analysis,
            title="🔨 Build Failure Analysis"
        )
        
        if filepath:
            printer.print(f"\n📄 Detailed analysis saved to: {filepath}")
            printer.print("   Please review the recommendations and fix the issues before redeploying.")
        
        return PhaseResult(success=True, message="Build failure analyzed")
    
    async def _handle_stopped_or_completed_status(self, status: str) -> PhaseResult:
        """Handle Stopped or Completed status."""
        # Store deployment status in context
        self.context.deployment.deployment_status = status
        
        if status == DeploymentStatus.COMPLETED.value:
            printer.print("\n✅ Deployment completed successfully!")
            printer.print("   This was likely a Job-type deployment that finished its task.")
            printer.print("   Check the Quix Portal for results and logs.")
        elif status == DeploymentStatus.STOPPED.value:
            printer.print("\n⏹️  Deployment has been stopped.")
            printer.print("   Someone may have manually stopped it, or it was a one-time job.")
            printer.print("   Check the Quix Portal for more details.")
        
        return PhaseResult(success=True, message=f"Deployment {status.lower()}")
    
    async def _get_runtime_logs_with_retry(self, deployment_id: str, line_limit: int = 100, max_retries: int = 10, retry_interval: int = 5) -> Optional[str]:
        """
        Get runtime logs with retry logic for empty logs and comprehensive error detection.
        
        Args:
            deployment_id: The deployment ID to get logs for
            line_limit: Maximum number of log lines to retrieve
            max_retries: Maximum number of retries for empty logs (default 10)
            retry_interval: Seconds to wait between retries (default 5)
        
        Returns:
            Log content as string or None if error
        """
        initial_logs = ""
        
        for attempt in range(max_retries + 1):  # +1 to include initial attempt
            logs = self.monitor.get_runtime_logs(deployment_id, line_limit)
            
            if logs is None:
                # API error, no point retrying
                return None
            
            if logs.strip():
                # Found logs - check if we should wait for more comprehensive logs
                if attempt == 0:
                    # First attempt - save initial logs but continue monitoring
                    initial_logs = logs
                    printer.print(f"📝 Found initial logs ({len(logs.splitlines())} lines), continuing to monitor for errors.")
                else:
                    # Subsequent attempts - return latest logs
                    return logs
            
            # Empty logs or first attempt - check if we should retry
            if attempt < max_retries:
                if attempt == 0 and initial_logs:
                    printer.print(f"📝 Waiting {retry_interval} seconds to capture any startup errors.")
                else:
                    printer.print(f"📝 No logs yet, waiting {retry_interval} seconds before retry {attempt + 1}/{max_retries}.")
                await asyncio.sleep(retry_interval)
            else:
                # Final attempt, return what we have
                return logs if logs.strip() else initial_logs
        
        return logs if logs.strip() else initial_logs