# quix_tools.py

import os
import json
import httpx
import logging
import asyncio
import random
import pandas as pd
from typing import Any, Optional, Dict, List
from enum import Enum

class TopicAction(Enum):
    """Actions that can be performed on topics."""
    create = "create"
    update = "update"
    delete = "delete"
    clean = "clean"

# --- Basic Setup ---
# Get the workflow logger from main.py if available, otherwise create a default logger
def get_workflow_logger():
    try:
        # Try to get the workflow logger from main module
        import sys
        if 'main' in sys.modules:
            main_module = sys.modules['main']
            if hasattr(main_module, 'workflow_logger'):
                return main_module.workflow_logger
    except:
        pass
    # Fallback to module-specific logger
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logger

logger = get_workflow_logger()

# --- Base API Logic & Error Handling ---

def pretty_json(data: Any, max_length: int = 5000) -> str:
    """Pretty-print JSON data for logging, with truncation for very large payloads."""
    if data is None:
        return "null"
    try:
        pretty = json.dumps(data, indent=2, sort_keys=True)
        if len(pretty) > max_length:
            return pretty[:max_length] + f"\n... (truncated, total length: {len(pretty)} chars)"
        return pretty
    except (TypeError, ValueError):
        return str(data)

class QuixApiError(Exception):
    """Custom exception for Quix API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

async def make_quix_request(
    method: str,
    path: str,
    workspace_id: Optional[str] = None,
    json_payload: Optional[Dict[str, Any]] = None,
    content_payload: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    accept_header: str = "application/json",
    timeout: float = 120.0,
    max_retries: int = 3,
    base_delay: float = 2.0
) -> Any:
    """Makes an authenticated request to the Quix Portal API with retry logic.

    Args:
        method: HTTP method
        path: API path
        workspace_id: Optional workspace ID
        json_payload: Optional JSON payload
        content_payload: Optional text content payload
        params: Optional query parameters
        accept_header: Accept header value
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts for network errors
        base_delay: Base delay for exponential backoff
    """
    token = os.environ.get("QUIX_TOKEN")
    base_url = os.environ.get("QUIX_BASE_URL")

    if not token or not base_url:
        error_msg = "QUIX_TOKEN and QUIX_BASE_URL environment variables must be set."
        if not token:
            error_msg += "\n\nNo Quix PAT token detected."
            error_msg += "\nTo get one, sign up for a free Quix account here:"
            error_msg += "\nhttps://portal.cloud.quix.io/signup?utm_campaign=ai-data-integrator"
        raise QuixApiError(error_msg)

    if workspace_id:
        path = path.replace("{workspaceId}", workspace_id)

    full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {token}", "Accept": accept_header, "X-Version": "2.0"}

    if json_payload is not None:
        headers["Content-Type"] = "application/json"
    elif content_payload is not None:
        # According to the swagger spec, the body for file updates is plain text
        headers["Content-Type"] = "text/plain"

    # Get verbose mode setting
    verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'

    # Log request info based on verbosity
    if verbose_mode:
        logger.info(f"Requesting: {method} {full_url}")

    # Log request payload with pretty formatting (only in verbose mode)
    if verbose_mode:
        if json_payload is not None:
            logger.info(f"Request payload:\n{pretty_json(json_payload)}")
        elif content_payload is not None and len(content_payload) < 1000:
            logger.info(f"Request content: {content_payload[:500]}...")
        elif params:
            logger.info(f"Request params: {params}")

    # Retry loop for network errors
    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                request_args = {
                    "method": method,
                    "url": full_url,
                    "headers": headers,
                    "timeout": timeout  # Use the configurable timeout parameter
                }
                if json_payload is not None:
                    request_args["json"] = json_payload
                if content_payload is not None:
                    request_args["content"] = content_payload
                if params:
                    request_args["params"] = params

                response = await client.request(**request_args)

                response.raise_for_status()

                if not response.content:
                    if verbose_mode:
                        logger.info("Response: Empty/No content")
                    return None

                if "application/json" in response.headers.get("content-type", ""):
                    json_response = response.json()
                    # Only log detailed response in verbose mode
                    if verbose_mode:
                        logger.info(f"Response JSON:\n{pretty_json(json_response)}")
                    # In non-verbose mode, don't log success messages
                    return json_response

                text_response = response.text
                if verbose_mode:
                    if len(text_response) < 1000:
                        logger.info(f"Response text: {text_response}")
                    else:
                        logger.info(f"Response text (truncated): {text_response[:500]}...")
                # In non-verbose mode, don't log success messages
                return text_response

        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError, httpx.NetworkError) as e:
            # Network-related errors that should be retried
            last_error = e
            if attempt < max_retries - 1:
                # Calculate delay with exponential backoff and jitter
                delay = base_delay * (2 ** attempt)
                jitter = random.uniform(0, delay * 0.1)
                total_delay = delay + jitter

                logger.warning(f"⚠️ Network error ({type(e).__name__}). Retrying in {total_delay:.1f} seconds... (attempt {attempt + 1}/{max_retries})")
                logger.info(f"   Operation: {method} {path}")

                await asyncio.sleep(total_delay)
                continue
            else:
                # Max retries exhausted
                logger.error(f"❌ Network error after {max_retries} attempts: {type(e).__name__}")
                logger.error(f"   Operation failed: {method} {path}")
                logger.error(f"   Error details: {repr(e)}")
                raise QuixApiError(f"Network error after {max_retries} attempts: {type(e).__name__}('')")

        except httpx.HTTPStatusError as e:
            # More detailed logging for HTTP errors
            if verbose_mode:
                logger.error(f"HTTP Status Error: {e.response.status_code} calling {e.request.method} {e.request.url}")
                # Try to parse and pretty-print error response
                try:
                    error_json = e.response.json()
                    logger.error(f"Error response:\n{pretty_json(error_json)}")
                except:
                    logger.error(f"Error response text: {e.response.text}")
            else:
                # In non-verbose mode, just log a simple error
                logger.error(f"API Error {e.response.status_code}: {e.request.method} {e.request.url.path}")
            raise QuixApiError(f"API request failed with status {e.response.status_code}: {e.response.text}", e.response.status_code)

        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error from {full_url}. Response: {e.response.text if hasattr(e, 'response') else 'No response text.'}")
            # Return the raw text if it's not valid JSON, it might contain a readable error message
            return e.response.text if hasattr(e, 'response') else ""

        except Exception as e:
            logger.error(f"An unexpected error of type {type(e).__name__} occurred: {repr(e)}")
            raise QuixApiError(f"An unexpected error occurred: {repr(e)}")

    # Should never reach here, but just in case
    if last_error:
        raise QuixApiError(f"Request failed after {max_retries} attempts: {repr(last_error)}")

# --- Tool Functions that are regular async functions (No AI involved) ---

async def find_workspaces() -> pd.DataFrame:
    try:
        workspaces = await make_quix_request("GET", "workspaces")
        if not workspaces: 
            return pd.DataFrame(columns=["Index", "Workspace Name", "Workspace ID", "Branch"])
        
        # Validate that workspaces is a list
        if not isinstance(workspaces, list):
            logger.error(f"Unexpected response type from workspaces API: {type(workspaces)}")
            logger.error(f"Response content: {workspaces}")
            
            # Check if the URL might be incorrect
            base_url = os.environ.get("QUIX_BASE_URL", "")
            error_msg = "❌ Failed to fetch workspaces. The API returned an unexpected response."
            error_msg += "\n\n📍 Please check your QUIX_BASE_URL configuration:"
            error_msg += f"\n   Current URL: {base_url}"
            error_msg += "\n\n✅ To find your correct Portal API URL:"
            error_msg += "\n   1. Go to your workspace settings: https://<platform-base-url>.quix.io/settings/tokens?workspace=<workspace-id>"
            error_msg += "\n   2. Copy the 'Portal API URL' value"
            error_msg += "\n   3. Set it as QUIX_BASE_URL in your .env file"
            error_msg += "\n\n   Example: QUIX_BASE_URL=https://portal-api.platform.quix.io"
            
            raise QuixApiError(error_msg)
        
        # Process valid workspace list
        df = pd.DataFrame([{
            "Workspace Name": ws.get("name"), 
            "Workspace ID": ws.get("workspaceId"),
            "Branch": ws.get("branch", "main")  # Default to "main" if not provided
        } for ws in workspaces])
        df.index += 1
        return df.reset_index().rename(columns={'index': 'Index'})
    except QuixApiError as e:
        # Re-raise QuixApiError with its message intact
        raise
    except Exception as e:
        logger.error(f"Error finding workspaces: {e}")
        return pd.DataFrame()

async def find_topics(workspace_id: str) -> pd.DataFrame:
    try:
        topics = await make_quix_request("GET", f"/{workspace_id}/topics")
        if not topics: return pd.DataFrame(columns=["Index", "Topic Name", "Topic ID"])
        
        # Filter out internal topics (changelog__ for stateful processing, source__ for internal sources)
        filtered_topics = [
            t for t in topics 
            if not (t.get("name", "").startswith("changelog__") or 
                   t.get("name", "").startswith("source__"))
        ]
        
        df = pd.DataFrame([{"Topic Name": t.get("name"), "Topic ID": t.get("id")} for t in filtered_topics])
        df.index += 1
        return df.reset_index().rename(columns={'index': 'Index'})
    except QuixApiError as e:
        logger.error(f"Error finding topics: {e}")
        return pd.DataFrame()

async def get_topic_sample(workspace_id: str, topic_id: str) -> Optional[dict]:
    try:
        base_url = os.environ.get("QUIX_BASE_URL", "")
        portal_domain = base_url.split("https://portal-api.")[1].rstrip('/')
        reader_api_url = f'https://reader-{workspace_id}.{portal_domain}/query-messages'
        headers = {'Authorization': f'Bearer {os.environ.get("QUIX_TOKEN")}'}
        payload = {"topicId": topic_id, "offset": "Newest", "maxResults": 100}
        async with httpx.AsyncClient() as client:
            response = await client.post(reader_api_url, headers=headers, json=payload, timeout=45)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"API Error fetching topic sample: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching topic sample: {e}")
        return None

async def manage_topic(
    action: TopicAction,
    workspace_id: str,
    name: str,
    partitions: Optional[int] = None,
    retention_in_minutes: Optional[int] = None,
    retention_in_bytes: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Manage topics in a workspace (create, update, delete, clean).
    
    Args:
        action: The action to perform (TopicAction enum)
        workspace_id: The workspace ID
        name: The topic name
        partitions: Number of partitions (for create/update)
        retention_in_minutes: Retention time in minutes (for create/update)
        retention_in_bytes: Retention size in bytes (for create/update)
        
    Returns:
        Response from the API or None on error
    """
    try:
        if action == TopicAction.create:
            # Create a new topic
            payload = {
                "name": name
            }
            
            # Add configuration if provided
            config = {}
            if partitions is not None:
                config["partitions"] = partitions
            if retention_in_minutes is not None:
                config["retentionInMinutes"] = retention_in_minutes
            if retention_in_bytes is not None:
                config["retentionInBytes"] = retention_in_bytes
                
            if config:
                payload["configuration"] = config
            
            logger.info(f"Creating topic '{name}' in workspace '{workspace_id}'")
            return await make_quix_request(
                "POST",
                f"/{workspace_id}/topics",
                json_payload=payload
            )
            
        elif action == TopicAction.update:
            # Update an existing topic
            payload = {}
            
            # Add configuration if provided
            config = {}
            if partitions is not None:
                config["partitions"] = partitions
            if retention_in_minutes is not None:
                config["retentionInMinutes"] = retention_in_minutes
            if retention_in_bytes is not None:
                config["retentionInBytes"] = retention_in_bytes
                
            if config:
                payload["configuration"] = config
            
            logger.info(f"Updating topic '{name}' in workspace '{workspace_id}'")
            return await make_quix_request(
                "PATCH",
                f"/{workspace_id}/topics/{name}",
                json_payload=payload
            )
            
        elif action == TopicAction.delete:
            # Delete a topic
            logger.info(f"Deleting topic '{name}' in workspace '{workspace_id}'")
            return await make_quix_request(
                "DELETE",
                f"/{workspace_id}/topics/{name}"
            )
            
        elif action == TopicAction.clean:
            # Clean a topic (remove all messages)
            logger.info(f"Cleaning topic '{name}' in workspace '{workspace_id}'")
            return await make_quix_request(
                "POST",
                f"/{workspace_id}/topics/{name}/clean"
            )
            
        else:
            raise ValueError(f"Unsupported action: {action}")
            
    except QuixApiError as e:
        logger.error(f"Error managing topic: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error managing topic: {e}")
        return None

async def find_in_library(workspace_id: str, search_term: Optional[str], item_type: Optional[str] = "Destination") -> List[Dict[str, Any]]:
    try:
        payload = {}
        tags = []
        if search_term: tags.append(search_term)
        if item_type: tags.append(item_type)
        if tags: payload["tags"] = tags
        logger.info(f"Library search payload:\n{pretty_json(payload)}")
        items = await make_quix_request("POST", "library/query", workspace_id=workspace_id, json_payload=payload)
        return items or []
    except QuixApiError as e:
        logger.error(f"Error searching library: {e}")
        return []

async def create_app_from_template(workspace_id: str, library_item_id: str, application_name: str, path: str) -> Optional[Dict[str, Any]]:
    try:
        payload = {"workspaceId": workspace_id, "libraryItemId": library_item_id, "applicationName": application_name, "path": path}
        # Debug logging to see what we're sending
        from workflow_tools.common import printer
        printer.print_debug(f"Creating app from template with payload: {payload}")
        result = await make_quix_request("POST", "library/application", workspace_id=workspace_id, json_payload=payload)
        # Debug logging to see what we got back
        if result:
            printer.print_debug(f"API returned app with name: {result.get('name', 'UNKNOWN')}, path: {result.get('path', 'UNKNOWN')}")
        return result
    except QuixApiError as e:
        raise e

async def create_application(workspace_id: str, name: str, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Creates a new, empty application in a Quix workspace."""
    try:
        # The API requires both 'applicationName' and 'language'.
        # 'path' is optional but highly recommended for organization.
        payload = {
            "applicationName": name,
            "language": "python"
        }
        if path:
            payload["path"] = path
        
        app = await make_quix_request("POST", "{workspaceId}/applications", workspace_id=workspace_id, json_payload=payload)
        return app
    except QuixApiError as e:
        raise e

async def delete_application(workspace_id: str, application_id: str) -> bool:
    """Delete an application from a Quix workspace.
    
    Args:
        workspace_id: The workspace ID
        application_id: The application ID to delete
        
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        # The delete endpoint returns 200 OK or 204 No Content on success
        # The 'deleteFiles' parameter defaults to true, which is what we want
        result = await make_quix_request(
            "DELETE", 
            f"/{workspace_id}/applications/{application_id}",
            workspace_id=workspace_id
        )
        logger.info(f"✅ Successfully deleted application '{application_id}'")
        return True
    except QuixApiError as e:
        if e.status_code == 404:
            logger.info(f"Application '{application_id}' not found (may have been already deleted)")
            return True  # Consider it successful if already deleted
        else:
            logger.error(f"Failed to delete application '{application_id}': {e}")
            return False
    except Exception as e:
        logger.error(f"Unexpected error deleting application '{application_id}': {e}")
        return False

async def find_applications(workspace_id: str, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Find applications in a workspace, optionally filtered by search term.
    
    Args:
        workspace_id: The workspace ID
        search: Optional search term to filter applications by name or path
        
    Returns:
        List of applications matching the search criteria
    """
    try:
        # Construct the API endpoint
        path = f"/{workspace_id}/applications"
        params = {}
        if search:
            params["search"] = search
            
        apps = await make_quix_request("GET", path, workspace_id=workspace_id, params=params)
        return apps or []
    except QuixApiError as e:
        logger.error(f"Error finding applications: {e}")
        return []

class SessionAction(str, Enum):
    start = "start"
    stop = "stop"

async def manage_session(
    action: SessionAction,
    workspace_id: str,
    application_id: Optional[str] = None,
    session_id: Optional[str] = None,
    branch_name: Optional[str] = None,  # No default - must be provided from workspace context
    cpu_millicores: int = 200,
    memory_in_mb: int = 500,
    environment_variables: Optional[Dict[str, str]] = None,
    secrets: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    try:
        if action == SessionAction.start:
            if not application_id:
                raise ValueError("application_id is required for starting a session")
            if not branch_name:
                raise ValueError("branch_name is required for starting a session")
            
            payload = {
                "workspaceId": workspace_id, 
                "applicationId": application_id, 
                "branchName": branch_name, 
                "cpuMillicores": cpu_millicores, 
                "memoryInMb": memory_in_mb
            }
            
            # Add environment variables if provided
            if environment_variables:
                payload["environmentVariables"] = environment_variables
            
            # Add secrets if provided  
            if secrets:
                payload["secretKeys"] = secrets
            
            verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
            if verbose_mode:
                logger.info(f"Starting session with payload:\n{pretty_json(payload)}")
            return await make_quix_request("POST", "sessions", json_payload=payload)
        
        elif action == SessionAction.stop:
            if not session_id:
                raise ValueError("session_id is required for stopping a session")
            
            logger.info(f"Stopping session: {session_id}")
            return await make_quix_request("DELETE", f"sessions/{session_id}")
        
        return None
    except QuixApiError as e:
        logger.error(f"Error managing session: {e}")
        return None

async def read_session_file(workspace_id: str, session_id: str, file_path: str) -> str:
    try:
        content = await make_quix_request("GET", f"sessions/{session_id}/files/{file_path}", workspace_id=workspace_id, accept_header="text/plain")
        return content or f"File '{file_path}' is empty or not found."
    except QuixApiError as e:
        logger.error(f"Error reading session file '{file_path}': {e}")
        raise e

async def update_session_file(workspace_id: str, session_id: str, file_path: str, content: str) -> Optional[Dict[str, Any]]:
    try:
        return await make_quix_request("POST", f"sessions/{session_id}/files/{file_path}", workspace_id=workspace_id, content_payload=content)
    except QuixApiError as e:
        raise e

async def commit_session_files(workspace_id: str, session_id: str, file_path: str, content: str, commit_message: str = None, action: str = "Update") -> Optional[Dict[str, Any]]:
    """Commit file changes to a session's git repository.
    
    Args:
        workspace_id: The workspace ID
        session_id: The session ID
        file_path: Path to the file (e.g., 'main.py')
        content: The file content to commit
        commit_message: Optional commit message
        action: 'Create' for new files or 'Update' for existing files
    
    Returns:
        Commit result or None if failed
    """
    try:
        payload = {
            "actions": [
                {
                    "action": action,
                    "path": file_path,
                    "content": content
                }
            ],
            "commitMessage": commit_message or f"{action} {file_path}"
        }
        return await make_quix_request("POST", f"sessions/{session_id}/commit", workspace_id=workspace_id, json_payload=payload)
    except QuixApiError as e:
        logger.error(f"Failed to commit file: {e}")


async def update_all_session_files_from_local(workspace_id: str, session_id: str, app_dir: str) -> bool:
    """Update all application files (main.py, requirements.txt, app.yaml) from local directory to session.
    
    This is a centralized function to ensure all files modified by Claude Code are properly
    uploaded to the session, including app.yaml which contains environment variables.
    
    Args:
        workspace_id: The workspace ID
        session_id: The session ID
        app_dir: Local directory containing the application files
    
    Returns:
        True if all files were successfully updated, False otherwise
    """
    from workflow_tools.common import printer
    import os
    
    files_to_update = [
        ("main.py", True),  # (filename, is_required)
        ("requirements.txt", True),
        ("app.yaml", True)
    ]
    
    all_success = True
    
    for filename, is_required in files_to_update:
        file_path = os.path.join(app_dir, filename)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                await update_session_file(workspace_id, session_id, filename, content)
                printer.print(f"  - Updated {filename}")
                
            except Exception as e:
                if is_required:
                    printer.print(f"  - ❌ Failed to update {filename}: {e}")
                    all_success = False
                else:
                    printer.print(f"  - ⚠️ Could not update {filename}: {e}")
        elif is_required:
            printer.print(f"  - ⚠️ {filename} not found in {app_dir}")
            all_success = False
    
    return all_success


async def update_application_environment(workspace_id: str, app_id: str, variables: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
    try:
        path = f"/{workspace_id}/applications/{app_id}"
        payload = {"variables": variables}
        if verbose_mode:
            logger.info(f"Updating application environment: workspace_id={workspace_id}, app_id={app_id}, path={path}")
        return await make_quix_request("PATCH", path, json_payload=payload)
    except QuixApiError as e:
        logger.error(f"Failed to update application environment: workspace_id={workspace_id}, app_id={app_id}")
        raise e

async def get_application_details(workspace_id: str, app_id: str) -> Optional[Dict[str, Any]]:
    """Get application details including variables."""
    verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
    try:
        path = f"/{workspace_id}/applications/{app_id}"
        if verbose_mode:
            logger.info(f"Getting application details: workspace_id={workspace_id}, app_id={app_id}")
        return await make_quix_request("GET", path, workspace_id=workspace_id)
    except QuixApiError as e:
        logger.error(f"Failed to get application details: workspace_id={workspace_id}, app_id={app_id}")
        raise e

async def setup_session(workspace_id: str, session_id: str, force: bool = False) -> str:
    """Setup session environment, including installing dependencies from requirements.txt."""
    verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
    try:
        params = {"force": str(force).lower()}
        if verbose_mode:
            logger.info(f"Setting up session with force={force}, params={params}")
        result = await make_quix_request("POST", f"sessions/{session_id}/setup", workspace_id=workspace_id, params=params)
        if verbose_mode:
            logger.info(f"Setup session result type: {type(result)}, length: {len(str(result)) if result else 0}")
            if result:
                logger.info(f"Setup session result preview: {repr(str(result)[:200])}")
        return result or "Session setup completed (no output returned)."
    except QuixApiError as e:
        logger.error(f"Error setting up session: {e}")
        return f"Error setting up session: {e}"

async def run_code_in_session(workspace_id: str, session_id: str, file_to_run: str, force_setup: bool = False) -> str:
    verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
    try:
        # Setup session first if force_setup is True (installs dependencies)
        if force_setup:
            if not verbose_mode:
                logger.info("Installing dependencies...")
            else:
                logger.info(f"Setting up session {session_id} to install dependencies.")
            setup_result = await setup_session(workspace_id, session_id, force=True)
            if verbose_mode:
                logger.info(f"Session setup result: {setup_result}")
        
        payload = {"file": file_to_run}
        # Use longer timeout (5 minutes) for running code, especially for source applications
        # that need time to connect to external systems and start producing data
        logs = await make_quix_request("POST", f"sessions/{session_id}/run", workspace_id=workspace_id, json_payload=payload, timeout=300.0)
        return logs or "Execution started, but no logs were returned."
    except QuixApiError as e:
        return f"Error running code in session: {e}"

async def run_code_in_session_with_timeout(workspace_id: str, session_id: str, file_to_run: str, 
                                          timeout_seconds: int = 30, force_setup: bool = False) -> str:
    """
    Run code in a session with streaming logs and a timeout.
    
    This is useful for applications that run continuously (like sources and sinks) where we want to
    collect logs for a limited time to verify the application is working correctly.
    
    Args:
        workspace_id: The workspace ID
        session_id: The session ID
        file_to_run: The file to run (e.g., "main.py")
        timeout_seconds: How long to collect logs before terminating (default: 30 seconds)
        force_setup: Whether to force setup before running
        
    Returns:
        The collected logs as a string
    """
    import asyncio
    import httpx
    
    verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
    
    # Setup session first if force_setup is True (installs dependencies)
    if force_setup:
        if not verbose_mode:
            logger.info("Installing dependencies...")
        else:
            logger.info(f"Setting up session {session_id} to install dependencies.")
        setup_result = await setup_session(workspace_id, session_id, force=True)
        if verbose_mode:
            logger.info(f"Session setup result: {setup_result}")
    
    # Start execution
    payload = {"file": file_to_run}
    url = f"{os.environ.get('QUIX_BASE_URL')}/sessions/{session_id}/run"
    headers = {
        "Authorization": f"Bearer {os.environ.get('QUIX_TOKEN')}",
        "Accept": "text/plain",  # Get plain text logs
        "Content-Type": "application/json",
        "X-Version": "2.0"
    }
    
    logs = ""
    if verbose_mode:
        logger.info(f"  Collecting logs for {timeout_seconds} seconds...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Start the execution with a streaming request
            # Add 5 seconds to the HTTP timeout to be slightly longer than our collection timeout
            async with client.stream("POST", url, headers=headers, json=payload,
                                    timeout=timeout_seconds + 5.0) as response:
                # Check status code without accessing the response body
                if response.status_code >= 400:
                    # For error responses, read the content first
                    try:
                        error_content = await response.aread()
                        error_text = error_content.decode('utf-8', errors='replace')
                    except Exception:
                        error_text = f"Status {response.status_code}"
                    return f"HTTP error during execution: {response.status_code} - {error_text}"

                # Check if the response is actually streaming
                content_type = response.headers.get('content-type', '')
                is_streaming = ('text/plain' in content_type or
                               'stream' in content_type or
                               'text/event-stream' in content_type)

                if is_streaming:
                    # Collect logs for the specified timeout
                    start_time = asyncio.get_event_loop().time()
                    async for chunk in response.aiter_text():
                        logs += chunk
                        # Stop collecting after timeout
                        if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                            if verbose_mode:
                                logger.info(f"  {timeout_seconds} seconds elapsed, terminating process")
                            # Explicitly close the response to signal the server to terminate the process
                            await response.aclose()
                            break
                else:
                    # Handle non-streaming response
                    # Read the entire response content
                    content = await response.aread()
                    logs = content.decode('utf-8', errors='replace')
                    if verbose_mode:
                        logger.info(f"  Received non-streaming response (content-type: {content_type})")
    except httpx.ReadTimeout:
        # This is expected for apps that run continuously
        if verbose_mode:
            logger.info(f"  Log collection timeout reached (normal for continuous applications)")
        if not logs:
            logs = f"Application started but no logs captured within {timeout_seconds} second timeout period"
    except httpx.HTTPStatusError as e:
        logs = f"HTTP error during execution: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        logs = f"Error starting execution: {e}"
    
    return logs

async def update_session_environment(workspace_id: str, session_id: str, environment_variables: Optional[Dict[str, str]] = None, secrets: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Update session with environment variables and secrets."""
    verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
    try:
        payload = {}
        
        # Add environment variables if provided
        if environment_variables:
            payload["environmentVariables"] = environment_variables
        
        # Add secrets if provided  
        if secrets:
            payload["secretKeys"] = secrets
            
        if not payload:
            return None  # Nothing to update
            
        if verbose_mode:
            logger.info(f"Updating session environment with payload:\n{pretty_json(payload)}")
        return await make_quix_request("PATCH", f"sessions/{session_id}", workspace_id=workspace_id, json_payload=payload)
    except QuixApiError as e:
        logger.error(f"Error updating session environment: {e}")
        return None

# --- Deployment Functions ---

async def create_deployment(
    workspace_id: str,
    application_id: str,
    name: str,
    replicas: int = 1,
    cpu_millicores: int = 200,
    memory_in_mb: int = 500,
    use_latest: bool = True,
    variables: Optional[Dict[str, Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """Create a new deployment from an application."""
    try:
        payload = {
            "workspaceId": workspace_id,
            "applicationId": application_id,
            "name": name,
            "replicas": replicas,
            "cpuMillicores": cpu_millicores,
            "memoryInMb": memory_in_mb,
            "useLatest": use_latest
        }
        
        # Add variables if provided - these should be DeploymentVariable objects
        if variables:
            payload["variables"] = variables
        
        verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
        if verbose_mode:
            logger.info(f"Creating deployment with payload:\n{pretty_json(payload)}")
        return await make_quix_request("POST", "deployments", workspace_id=workspace_id, json_payload=payload)
    except QuixApiError as e:
        logger.error(f"Error creating deployment: {e}")
        raise e

async def get_deployment_details(workspace_id: str, deployment_id: str) -> Optional[Dict[str, Any]]:
    """Get details of a specific deployment."""
    try:
        return await make_quix_request("GET", f"deployments/{deployment_id}", workspace_id=workspace_id)
    except QuixApiError as e:
        logger.error(f"Error getting deployment details: {e}")
        raise e

async def start_deployment(workspace_id: str, deployment_id: str) -> Optional[Dict[str, Any]]:
    """Start a deployment."""
    try:
        return await make_quix_request("PUT", f"deployments/{deployment_id}/start", workspace_id=workspace_id)
    except QuixApiError as e:
        logger.error(f"Error starting deployment: {e}")
        raise e

async def list_deployments(workspace_id: str, application_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all deployments in a workspace, optionally filtered by application.
    
    Args:
        workspace_id: The ID of the workspace
        application_id: Optional application ID to filter deployments
        
    Returns:
        List of deployment objects
    """
    try:
        params = {}
        if application_id:
            params['applicationId'] = application_id
            
        result = await make_quix_request(
            "GET", 
            f"workspaces/{workspace_id}/deployments",
            params=params if params else None
        )
        
        if result:
            logger.info(f"Found {len(result)} deployments in workspace {workspace_id}")
            if application_id:
                logger.info(f"  Filtered by application: {application_id}")
            return result
        return []
    except Exception as e:
        logger.error(f"Failed to list deployments: {e}")
        return []

async def sync_deployment(deployment_id: str) -> Optional[Dict[str, Any]]:
    """
    Sync a deployment to use the latest source code.
    
    This triggers an update for an existing deployment to use the latest version
    of its source code from the Git repository.
    
    Args:
        deployment_id: The ID of the deployment to sync
        
    Returns:
        Updated deployment object or None if sync failed
    """
    try:
        payload = {"useLatest": True}
        result = await make_quix_request("PATCH", f"deployments/{deployment_id}", json_payload=payload)
        if result:
            logger.info(f"Successfully triggered sync for deployment {deployment_id}")
            logger.debug(f"Sync response: {pretty_json(result)}")
        return result
    except QuixApiError as e:
        logger.error(f"Error syncing deployment: {e}")
        raise e

async def get_workspace_details(workspace_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a workspace, including repository ID."""
    try:
        return await make_quix_request("GET", f"workspaces/{workspace_id}")
    except QuixApiError as e:
        logger.error(f"Error getting workspace details: {e}")
        raise e

# --- SECRET MANAGEMENT API ---

async def get_repository_secrets(repository_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get all secrets for a repository.
    
    Args:
        repository_id: The repository ID
        
    Returns:
        List of secret configurations with 'name', 'workspaceId' (optional), etc.
    """
    try:
        # Use the base URL directly since this is a repository-level operation
        base_url = os.environ.get('QUIX_BASE_URL', 'https://portal-api.platform.quix.io')
        url = f"{base_url}/repositories/{repository_id}/secrets"
        
        headers = {
            "Authorization": f"Bearer {os.environ.get('QUIX_TOKEN')}",
            "Content-Type": "application/json",
            "X-Version": "2.0"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
            
    except Exception as e:
        logger.error(f"Error getting repository secrets: {e}")
        raise QuixApiError(f"Failed to get repository secrets: {str(e)}")

async def set_repository_secrets(repository_id: str, secrets: List[Dict[str, Any]]) -> bool:
    """
    Set all secrets for a repository (replaces existing secrets).
    
    Args:
        repository_id: The repository ID
        secrets: List of secret objects with 'name', 'value', and optional 'workspaceId'
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Use the base URL directly since this is a repository-level operation
        base_url = os.environ.get('QUIX_BASE_URL', 'https://portal-api.platform.quix.io')
        url = f"{base_url}/repositories/{repository_id}/secrets"
        
        headers = {
            "Authorization": f"Bearer {os.environ.get('QUIX_TOKEN')}",
            "Content-Type": "application/json",
            "X-Version": "2.0"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=headers, json=secrets)
            response.raise_for_status()
            return True
            
    except Exception as e:
        logger.error(f"Error setting repository secrets: {e}")
        raise QuixApiError(f"Failed to set repository secrets: {str(e)}")

async def get_workspace_secret_keys(repository_id: str, workspace_id: str) -> Optional[List[str]]:
    """
    Get list of secret key names available to a specific workspace.
    This includes both repository-scoped and workspace-scoped secrets.
    
    Args:
        repository_id: The repository ID
        workspace_id: The workspace ID
        
    Returns:
        List of secret key names
    """
    try:
        # Use the base URL directly since this is a repository-level operation
        base_url = os.environ.get('QUIX_BASE_URL', 'https://portal-api.platform.quix.io')
        url = f"{base_url}/repositories/{repository_id}/workspace/{workspace_id}/secrets"
        
        headers = {
            "Authorization": f"Bearer {os.environ.get('QUIX_TOKEN')}",
            "Content-Type": "application/json",
            "X-Version": "2.0"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                # The API returns a list of secret objects or strings
                secrets = response.json()
                
                # Debug logging to understand the response format
                verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
                if verbose_mode:
                    logger.info(f"Secrets API response type: {type(secrets)}")
                    if secrets and isinstance(secrets, list) and len(secrets) > 0:
                        logger.info(f"First secret item type: {type(secrets[0])}")
                        logger.info(f"First secret item: {secrets[0]}")
                
                if not secrets:
                    return []
                # Check if the response is a list of strings or objects
                if isinstance(secrets, list):
                    if len(secrets) == 0:
                        # Empty list - no secrets
                        return []
                    elif isinstance(secrets[0], str):
                        # It's already a list of secret names
                        return secrets
                    elif isinstance(secrets[0], dict):
                        # It's a list of secret objects, extract the names
                        secret_names = []
                        for secret in secrets:
                            if isinstance(secret, dict) and 'name' in secret:
                                secret_names.append(secret['name'])
                            elif isinstance(secret, str):
                                # Mixed format? Just add the string
                                secret_names.append(secret)
                        return secret_names
                    else:
                        logger.error(f"Unexpected secret item type: {type(secrets[0])}")
                        return []
                else:
                    logger.error(f"Unexpected response format for secrets: {type(secrets)}")
                    return []
            elif response.status_code == 404:
                # No secrets found
                return []
            else:
                response.raise_for_status()
                
    except Exception as e:
        logger.error(f"Error getting workspace secret keys: {e}")
        raise QuixApiError(f"Failed to get workspace secret keys: {str(e)}")

async def create_secret(repository_id: str, workspace_id: str, secret_name: str, secret_value: str, repository_scoped: bool = True) -> bool:
    """
    Create a new secret using the safe read-modify-write pattern.
    
    Args:
        repository_id: The repository ID
        workspace_id: The workspace ID (used for workspace-scoped secrets)
        secret_name: Name of the secret
        secret_value: Value of the secret
        repository_scoped: If True, create repository-scoped secret, otherwise workspace-scoped
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Step 1: Read existing secrets
        existing_secrets = await get_repository_secrets(repository_id)
        if existing_secrets is None:
            existing_secrets = []
        
        # Step 2: Add the new secret to the list
        new_secret = {
            "name": secret_name,
            "value": secret_value
        }
        
        # Add workspaceId for workspace-scoped secrets
        if not repository_scoped:
            new_secret["workspaceId"] = workspace_id
        
        # Check if secret already exists and update it
        secret_exists = False
        for i, secret in enumerate(existing_secrets):
            if (secret.get("name") == secret_name and 
                secret.get("workspaceId") == new_secret.get("workspaceId")):
                existing_secrets[i] = new_secret
                secret_exists = True
                break
        
        if not secret_exists:
            existing_secrets.append(new_secret)
        
        # Step 3: Write back the complete list
        return await set_repository_secrets(repository_id, existing_secrets)
        
    except Exception as e:
        logger.error(f"Error creating secret: {e}")
        raise QuixApiError(f"Failed to create secret: {str(e)}")

# --- WORKSPACE SYNC API ---

async def check_workspace_sync_status(workspace_id: str) -> Optional[Dict[str, Any]]:
    """
    Check the current synchronization status of the workspace.
    
    Args:
        workspace_id: The workspace ID
        
    Returns:
        Dictionary with sync status information including:
        - status: 'Synchronized', 'OutOfSync', 'Syncing', etc.
        - syncedCommitReference: Currently synced commit
        - lastRepoCommitReference: Latest commit in the repository
    """
    try:
        logger.info(f"Checking sync status for workspace '{workspace_id}'...")
        result = await make_quix_request("GET", f"workspaces/{workspace_id}/sync/status")
        
        if result:
            status = result.get('status', 'Unknown')
            logger.info(f"  - Current Status: {status}")
            logger.info(f"  - Synced Commit: {result.get('syncedCommitReference', 'N/A')}")
            logger.info(f"  - Latest Repo Commit: {result.get('lastRepoCommitReference', 'N/A')}")
            
            if status == 'OutOfSync':
                logger.info("  - ✅ Workspace is ready to be synced.")
            elif status == 'Synchronized':
                logger.info("  - ⚠️ Workspace is already synchronized with the latest known commit.")
        
        return result
    except QuixApiError as e:
        logger.error(f"Error checking sync status: {e}")
        return None

async def perform_workspace_sync_dry_run(workspace_id: str, commit_hash: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Perform a dry run to preview the changes of a sync operation.
    
    Args:
        workspace_id: The workspace ID
        commit_hash: Optional specific commit to sync to. If None, syncs to HEAD.
        
    Returns:
        Dictionary with preview of changes that would be applied
    """
    try:
        logger.info("Performing a dry run to preview sync changes...")
        
        params = {
            'appsReachableToNextReference': 'true'  # Use app versions reachable from the target reference
        }
        if commit_hash:
            params['reference'] = commit_hash
            logger.info(f"  - Previewing sync for commit: {commit_hash}")
        else:
            # When reference is not provided, API uses HEAD
            logger.info("  - Previewing sync for the latest commit on the branch (HEAD).")
        
        result = await make_quix_request("GET", f"workspaces/{workspace_id}/sync", params=params)
        
        if result:
            logger.info("  - Dry run successful. The following changes would be applied:")
            
            def log_changes(category: str, results: Optional[List[Dict[str, Any]]]):
                if results:
                    logger.info(f"    - {category}:")
                    for item in results:
                        change_type = item.get('changeDetails', {}).get('action', 'Unknown')
                        key = (item.get('changeDetails', {}).get('targetKey') or 
                              item.get('changeDetails', {}).get('currentKey'))
                        logger.info(f"      - {change_type}: {key}")
            
            log_changes("Applications", result.get("applicationsSyncResults"))
            log_changes("Deployments", result.get("deploymentsSyncResults"))
            log_changes("Topics", result.get("topicsSyncResults"))
        
        return result
    except QuixApiError as e:
        logger.error(f"Error performing dry run: {e}")
        return None

async def execute_workspace_sync(workspace_id: str, commit_hash: Optional[str] = None, create_deployments_as_stopped: bool = False) -> bool:
    """
    Execute the actual sync operation for the workspace.
    
    Args:
        workspace_id: The workspace ID
        commit_hash: Optional specific commit to sync to. If None, syncs to HEAD.
        create_deployments_as_stopped: If True, creates new deployments as stopped
        
    Returns:
        True if sync was successful, False otherwise
    """
    try:
        logger.info("Executing workspace sync operation...")
        
        params = {
            'appsReachableToNextReference': 'true',  # Use app versions reachable from the target reference
            'createDeploymentsAsStopped': str(create_deployments_as_stopped).lower()
        }
        if commit_hash:
            params['reference'] = commit_hash
            logger.info(f"  - Syncing to commit: {commit_hash}")
        else:
            # When reference is not provided, API uses HEAD
            logger.info("  - Syncing to the latest commit on the branch (HEAD).")
        
        result = await make_quix_request("POST", f"workspaces/{workspace_id}/sync", params=params)
        
        if result:
            logger.info("  - ✅ Sync command executed successfully!")
            logger.info("  - The environment is now being updated to match the repository state.")
            logger.info("  - You can monitor the progress in the Quix UI.")
            return True
        else:
            logger.warning("  - Sync command returned no result")
            return False
            
    except QuixApiError as e:
        logger.error(f"Error executing sync: {e}")
        return False

async def sync_workspace_before_deployment(workspace_id: str) -> bool:
    """
    Helper function to sync workspace to latest commit before deployment.
    This is the main function that should be called from the deployment phase.
    
    Args:
        workspace_id: The workspace ID
        
    Returns:
        True if sync was successful or workspace was already synced, False on error
    """
    try:
        # Step 1: Check current sync status
        status = await check_workspace_sync_status(workspace_id)
        if not status:
            logger.warning("Could not check sync status, proceeding with deployment anyway")
            return True  # Don't block deployment if we can't check status
        
        if status.get('status') == 'Synchronized':
            logger.info("Workspace is already synchronized with the latest commit")
            return True
        
        # Step 2: Perform a dry run (optional but recommended)
        dry_run = await perform_workspace_sync_dry_run(workspace_id)
        if not dry_run:
            logger.warning("Dry run failed, attempting sync anyway")
        
        # Step 3: Execute the actual sync
        sync_success = await execute_workspace_sync(workspace_id)
        if not sync_success:
            logger.error("Failed to sync workspace")
            return False
        
        # Step 4: Wait a moment for sync to complete
        import asyncio
        logger.info("Waiting for sync to complete...")
        await asyncio.sleep(5)
        
        # Step 5: Verify sync status
        final_status = await check_workspace_sync_status(workspace_id)
        if final_status and final_status.get('status') in ['Synchronized', 'Syncing']:
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error during workspace sync: {e}")
        # Don't block deployment on sync errors
        return True

