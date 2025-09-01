"""
URL builder utility for constructing Quix Portal resource URLs.

This module provides functions to construct clickable URLs for various Quix resources
(topics, applications, deployments) that can be opened directly in a browser.
"""

import os
from typing import Optional
from urllib.parse import urlencode


class QuixPortalURLBuilder:
    """Builds URLs for Quix Portal resources."""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize URL builder with base URL.
        
        Args:
            base_url: Base URL for Quix Portal (e.g., https://portal.demo.quix.io)
                     If not provided, uses QUIX_BASE_URL environment variable
        """
        self.base_url = base_url or os.getenv("QUIX_BASE_URL", "https://portal-api.platform.quix.io")
        # Convert API URL to portal URL if needed
        self.portal_url = self._get_portal_url()
    
    def _get_portal_url(self) -> str:
        """Convert API URL to portal URL."""
        # If it's already a portal URL, return as is
        if "portal.demo" in self.base_url or "portal.platform" in self.base_url:
            return self.base_url.rstrip("/")
        
        # Convert API URL to portal URL
        if "portal-api.platform.quix.io" in self.base_url:
            return "https://portal.platform.quix.io"
        elif "portal-api.demo.quix.io" in self.base_url:
            return "https://portal.demo.quix.io"
        else:
            # For custom URLs, try to convert portal-api to portal
            return self.base_url.replace("portal-api", "portal").rstrip("/")
    
    def get_topic_url(self, workspace: str, topic_name: str) -> str:
        """
        Build URL for a topic in Quix Portal.
        
        Args:
            workspace: Workspace ID (e.g., "demo-solarfarmdatageneratordemo-ai")
            topic_name: Name of the topic (e.g., "bucket-output")
        
        Returns:
            Full URL to the topic in Quix Portal
        
        Example:
            https://portal.demo.quix.io/topics/explore/bucket-output/data?workspace=demo-solarfarmdatageneratordemo-ai
        """
        params = {"workspace": workspace}
        query_string = urlencode(params)
        return f"{self.portal_url}/topics/explore/{topic_name}/data?{query_string}"
    
    def get_application_url(self, workspace: str, application_name: str, branch: str = "main") -> str:
        """
        Build URL for an application IDE in Quix Portal.
        
        Args:
            workspace: Workspace ID
            application_name: Name of the application (e.g., "google-storage-bucket-source")
            branch: Git branch (default: "main")
        
        Returns:
            Full URL to the application IDE in Quix Portal
        
        Example:
            https://portal.demo.quix.io/applications/ide/google-storage-bucket-source?workspace=demo-solarfarmdatageneratordemo-ai&branch=ai-testing
        """
        params = {
            "workspace": workspace,
            "branch": branch
        }
        query_string = urlencode(params)
        return f"{self.portal_url}/applications/ide/{application_name}?{query_string}"
    
    def get_deployment_url(self, workspace: str, deployment_id: str) -> str:
        """
        Build URL for a deployment in Quix Portal.
        
        Args:
            workspace: Workspace ID
            deployment_id: Deployment UUID (e.g., "f9a76a93-1466-4a54-873a-251a8fb126dc")
        
        Returns:
            Full URL to the deployment in Quix Portal
        
        Example:
            https://portal.demo.quix.io/pipeline/deployments/f9a76a93-1466-4a54-873a-251a8fb126dc?workspace=demo-solarfarmdatageneratordemo-ai
        """
        params = {"workspace": workspace}
        query_string = urlencode(params)
        return f"{self.portal_url}/pipeline/deployments/{deployment_id}?{query_string}"
    
    def get_pipeline_url(self, workspace: str) -> str:
        """
        Build URL for the pipeline view in Quix Portal.
        
        Args:
            workspace: Workspace ID
        
        Returns:
            Full URL to the pipeline view in Quix Portal
        """
        params = {"workspace": workspace}
        query_string = urlencode(params)
        return f"{self.portal_url}/pipeline?{query_string}"
    
    def get_workspace_url(self, workspace: str) -> str:
        """
        Build URL for a workspace in Quix Portal.
        
        Args:
            workspace: Workspace ID
        
        Returns:
            Full URL to the workspace in Quix Portal
        """
        params = {"workspace": workspace}
        query_string = urlencode(params)
        return f"{self.portal_url}/workspaces?{query_string}"


# Convenience functions for quick URL generation
def get_topic_url(workspace: str, topic_name: str) -> str:
    """Quick function to get a topic URL."""
    builder = QuixPortalURLBuilder()
    return builder.get_topic_url(workspace, topic_name)


def get_application_url(workspace: str, application_name: str, branch: str = "main") -> str:
    """Quick function to get an application URL."""
    builder = QuixPortalURLBuilder()
    return builder.get_application_url(workspace, application_name, branch)


def get_deployment_url(workspace: str, deployment_id: str) -> str:
    """Quick function to get a deployment URL."""
    builder = QuixPortalURLBuilder()
    return builder.get_deployment_url(workspace, deployment_id)