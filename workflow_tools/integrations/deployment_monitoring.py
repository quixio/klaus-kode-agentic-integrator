# deployment_monitoring.py - Deployment status and log monitoring utilities

import os
import time
import asyncio
import requests
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from agents import Agent
from workflow_tools.common import WorkflowContext, printer, workflow_logger
from workflow_tools.services.model_utils import create_agent_with_model_config
from workflow_tools.services.runner_utils import run_agent_with_retry

class DeploymentStatus(Enum):
    """Deployment status enum based on Quix API documentation."""
    QUEUED_FOR_BUILD = "QueuedForBuild"
    BUILDING = "Building"
    BUILD_FAILED = "BuildFailed"
    BUILD_SUCCESSFUL = "BuildSuccessful"
    QUEUED_FOR_DEPLOYMENT = "QueuedForDeployment"
    DEPLOYING = "Deploying"
    DEPLOYMENT_FAILED = "DeploymentFailed"
    STARTING = "Starting"
    RUNNING = "Running"
    RUNTIME_ERROR = "RuntimeError"
    STOPPING = "Stopping"
    STOPPED = "Stopped"
    COMPLETED = "Completed"
    DELETING = "Deleting"

class DeploymentMonitor:
    """Handles deployment status monitoring and log analysis."""
    
    # Final statuses that indicate deployment process is complete
    FINAL_STATUSES = {
        DeploymentStatus.RUNNING,
        DeploymentStatus.BUILD_FAILED,
        DeploymentStatus.RUNTIME_ERROR,
        DeploymentStatus.STOPPED,
        DeploymentStatus.COMPLETED
    }
    
    def __init__(self, context: WorkflowContext, run_config, debug_mode: bool = False):
        self.context = context
        self.run_config = run_config
        self.debug_mode = debug_mode
        self.base_url = os.environ.get("QUIX_BASE_URL", "https://portal-api.platform.quix.io")
        self.token = os.environ.get("QUIX_TOKEN")
        
        # Create log analysis agent (using o3 model as specified)
        self.log_analysis_agent = None
    
    def _create_log_analysis_agent(self) -> Agent:
        """Create log analysis agent for analyzing deployment logs."""
        if self.log_analysis_agent is None:
            instructions = (
                "You are an expert DevOps engineer and log analyst. Your task is to analyze deployment logs "
                "and provide clear assessments of application health and issues. "
                "When analyzing logs: "
                "1. For healthy/running applications: Provide 10 sample log lines and confirm everything looks normal "
                "2. For error conditions: Identify the root cause and provide specific fix recommendations "
                "3. Focus on common deployment issues like: connection errors, missing dependencies, "
                "configuration problems, resource limits, authentication failures, and runtime exceptions "
                "4. Always provide actionable next steps for any issues found "
                "Structure your response clearly with sections for Assessment, Sample Logs (if healthy), "
                "or Error Analysis and Recommendations (if problematic)."
            )
            
            # Use centralized agent creation with model configuration from models.yaml
            self.log_analysis_agent = create_agent_with_model_config(
                agent_name="DeploymentLogAnalysisAgent",
                task_type="log_analysis",
                workflow_type=None,  # log_analysis doesn't have workflow-specific configs
                instructions=instructions,
                context_type=WorkflowContext
            )
        return self.log_analysis_agent
    
    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for Quix API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Version": "2.0",
            "Accept": "application/json"
        }
    
    def get_deployment_status(self, deployment_id: str) -> Optional[Tuple[str, Optional[str]]]:
        """
        Get current deployment status.
        
        Returns:
            Tuple of (status, status_reason) or None if error
        """
        url = f"{self.base_url}/deployments/{deployment_id}"
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                status_reason = data.get("statusReason")
                return status, status_reason
            elif response.status_code == 401:
                printer.print("❌ Error: Unauthorized. Check if your QUIX_TOKEN is correct.")
                return None
            elif response.status_code == 404:
                printer.print(f"❌ Error: Deployment with ID '{deployment_id}' not found.")
                return None
            else:
                printer.print(f"❌ API Error: Status {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            printer.print(f"❌ Network error: {e}")
            return None
    
    def get_runtime_logs(self, deployment_id: str, line_limit: int = 100) -> Optional[str]:
        """
        Get current runtime logs for a deployment.
        
        Returns:
            Log content as string or None if error
        """
        url = f"{self.base_url}/deployments/{deployment_id}/logs/current"
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                full_logs = response.text
                if not full_logs.strip():
                    return ""
                
                # For comprehensive analysis, return all logs if less than line_limit
                # or the most recent logs if more than line_limit
                lines = full_logs.splitlines()
                if len(lines) <= line_limit:
                    # Return all logs for comprehensive analysis
                    return "\n".join(lines)
                else:
                    # Return the most recent logs
                    latest_lines = lines[-line_limit:]
                    return "\n".join(latest_lines)
            elif response.status_code == 204:
                return ""  # No logs available
            elif response.status_code == 401:
                printer.print("❌ Error: Unauthorized. Check if your QUIX_TOKEN is correct.")
                return None
            elif response.status_code == 404:
                printer.print(f"❌ Error: Deployment with ID '{deployment_id}' not found.")
                return None
            else:
                printer.print(f"❌ API Error: Status {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            printer.print(f"❌ Network error: {e}")
            return None
    
    def get_build_logs(self, deployment_id: str) -> Optional[str]:
        """
        Get build logs for a deployment.
        
        Returns:
            Build log content as string or None if error
        """
        url = f"{self.base_url}/deployments/{deployment_id}/buildlogs"
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 204:
                return ""  # No build logs available
            elif response.status_code == 401:
                printer.print("❌ Error: Unauthorized. Check if your QUIX_TOKEN is correct.")
                return None
            elif response.status_code == 404:
                printer.print(f"❌ Error: Deployment with ID '{deployment_id}' not found.")
                return None
            else:
                printer.print(f"❌ API Error: Status {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            printer.print(f"❌ Network error: {e}")
            return None
    
    async def poll_deployment_status(self, deployment_id: str, poll_interval: int = 3, max_polls: int = 200) -> Optional[str]:
        """
        Poll deployment status until it reaches a final state.
        
        Args:
            deployment_id: The deployment ID to monitor
            poll_interval: Seconds between polls (default 3)
            max_polls: Maximum number of polls before giving up (default 200 = ~10 minutes)
        
        Returns:
            Final status string or None if error/timeout
        """
        printer.print(f"\n🔄 Monitoring deployment status (polling every {poll_interval} seconds).")
        printer.print(f"   Deployment ID: {deployment_id}")
        
        for poll_count in range(max_polls):
            status_result = self.get_deployment_status(deployment_id)
            
            if status_result is None:
                printer.print("❌ Failed to get deployment status")
                return None
            
            status, status_reason = status_result
            
            # Display current status
            reason_text = f" ({status_reason})" if status_reason else ""
            printer.print(f"   Status: {status}{reason_text}")
            
            try:
                # Check if we've reached a final status
                status_enum = DeploymentStatus(status)
                if status_enum in self.FINAL_STATUSES:
                    printer.print(f"✅ Final status reached: {status}")
                    return status
            except ValueError:
                # Unknown status, continue polling
                pass
            
            # Wait before next poll
            if poll_count < max_polls - 1:  # Don't sleep on the last iteration
                await asyncio.sleep(poll_interval)
        
        printer.print(f"⏰ Timeout: Status monitoring exceeded {max_polls} polls")
        return status if 'status' in locals() else None
    
    async def analyze_logs_with_ai(self, logs: str, log_type: str, status: str) -> str:
        """
        Analyze logs using AI agent.
        
        Args:
            logs: The log content to analyze
            log_type: Type of logs ("runtime" or "build")
            status: Current deployment status
        
        Returns:
            AI analysis result
        """
        if not logs.strip():
            return f"No {log_type} logs available for analysis."
        
        log_analysis_agent = self._create_log_analysis_agent()
        
        # Prepare context-specific prompt
        if status == "Running":
            analysis_prompt = (
                f"Please analyze these {log_type} logs from a deployment that is currently Running. "
                f"Even though the status is Running, please check for any potential issues or warnings. "
                f"If everything looks healthy, provide 10 sample lines and confirm the application appears to be working properly.\n\n"
                f"Logs to analyze:\n```\n{logs}\n```"
            )
        elif status == "RuntimeError":
            analysis_prompt = (
                f"Please analyze these {log_type} logs from a deployment that has a RuntimeError status. "
                f"Identify the root cause of the error and provide specific recommendations on how to fix it.\n\n"
                f"Logs to analyze:\n```\n{logs}\n```"
            )
        elif status == "BuildFailed":
            analysis_prompt = (
                f"Please analyze these build logs from a deployment that failed to build. "
                f"Identify what went wrong during the build process and provide specific recommendations on how to fix it.\n\n"
                f"Build logs to analyze:\n```\n{logs}\n```"
            )
        else:
            analysis_prompt = (
                f"Please analyze these {log_type} logs from a deployment with status '{status}'. "
                f"Provide insights into what might be happening and any recommendations.\n\n"
                f"Logs to analyze:\n```\n{logs}\n```"
            )
        
        try:
            result = await run_agent_with_retry(
                starting_agent=log_analysis_agent,
                input=analysis_prompt,
                context=self.context,
                operation_name=f"Deployment log analysis for {self.context.deployment.deployment_name}"
            )

            if result is None:
                # API overloaded, return a fallback message
                workflow_logger.error("Log analysis failed due to API overload after retries")
                return "⚠️ Unable to analyze logs due to API overload. Please review logs manually."

            return result.final_output
        except Exception as e:
            workflow_logger.error(f"Error during log analysis: {e}")
            return f"❌ Error analyzing logs: {e}"
    
    def save_analysis_to_file(self, analysis: str, filename: str = "deployment_analysis.md") -> str:
        """
        Save AI analysis to a markdown file.
        
        Returns:
            The filepath where the analysis was saved
        """
        from workflow_tools.core.working_directory import WorkingDirectory
        filepath = WorkingDirectory.get_temp_debug_path(filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# Deployment Log Analysis\n\n")
                f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(analysis)
            
            return filepath
        except Exception as e:
            workflow_logger.error(f"Error saving analysis to file: {e}")
            return ""