"""Centralized service for collecting prerequisites for both sink and source workflows.

This service provides unified functionality for workspace selection, topic selection,
and technology selection that was previously duplicated between sink and source phases.
"""

import os
import json
import glob
import httpx
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, Literal, List, Tuple
from agents import RunConfig
from workflow_tools.contexts import WorkflowContext
from workflow_tools.common import printer, sanitize_name, get_user_approval, get_user_approval_with_back, clear_screen
from workflow_tools.core.questionary_utils import QUESTIONARY_STYLE, select
from workflow_tools.core.navigation import NavigationRequest, SinkWorkflowSteps, SourceWorkflowSteps
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.integrations import quix_tools
from workflow_tools.integrations.quix_tools import QuixApiError
from workflow_tools.core.prompt_manager import load_task_prompt, load_agent_instructions
from workflow_tools.core.url_builder import QuixPortalURLBuilder
from workflow_tools.services.model_utils import create_agent_with_model_config
from agents import Runner


class PrerequisitesCollector:
    """Unified service for collecting prerequisites for sink and source workflows."""
    
    # Technology patterns for different workflow types
    TECHNOLOGY_PATTERNS = {
        "source": {
            "webhook": ["webhook", "http endpoint", "rest endpoint"],
            "rest api": ["rest", "api", "http", "restful"],
            "websocket": ["websocket", "ws", "real-time", "socket"],
            "mqtt": ["mqtt", "iot", "broker"],
            "database": ["database", "db", "sql", "nosql", "postgresql", "postgres", "mysql", "mongodb", "redis"],
            "file": ["file", "csv", "json", "xml", "parquet"],
            "streaming": ["kafka", "kinesis", "pubsub", "event hub"],
            "cloud storage": ["s3", "blob", "gcs", "cloud storage", "bucket"]
        },
        "sink": {
            "postgresql": ["postgresql", "postgres", "pg", "psql"],
            "mysql": ["mysql", "mariadb"],
            "mongodb": ["mongodb", "mongo", "nosql"],
            "redis": ["redis", "cache"],
            "influxdb": ["influxdb", "influx", "time series", "timeseries"],
            "elasticsearch": ["elasticsearch", "elastic", "search"],
            "rest api": ["rest", "api", "http", "webhook"],
            "cloud storage": ["s3", "blob", "gcs", "cloud storage", "bucket"],
            "file": ["file", "csv", "json", "parquet"],
            "analytics": ["bigquery", "snowflake", "redshift", "databricks"]
        }
    }
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False, run_config: Optional[RunConfig] = None):
        """Initialize the prerequisites collector.
        
        Args:
            context: Workflow context
            debug_mode: Whether to enable debug mode
            run_config: Optional run configuration for agents
        """
        self.context = context
        self.debug_mode = debug_mode
        self.run_config = run_config or RunConfig(workflow_name="Prerequisites Collection")
        
    
    async def collect_prerequisites(self, workflow_type: Literal["sink", "source"]) -> Dict[str, any]:
        """Collect all prerequisites for the specified workflow type.

        Args:
            workflow_type: Type of workflow ("sink" or "source")

        Returns:
            Dictionary containing collected prerequisites
        """
        # Don't print a phase header here - base_phase already does that
        # Just show what we're collecting
        printer.print("")  # Add spacing after phase header
        printer.print_section_header(f"{workflow_type.capitalize()} Prerequisites",
                                   subtitle="Collecting requirements and configuration",
                                   icon="🔧", style="cyan")
        printer.print("")  # Add spacing after section header

        # Initialize services
        from workflow_tools.phases.shared.cache_utils import CacheUtils
        from workflow_tools.phases.shared.app_management import AppManager

        cache_utils = CacheUtils(self.context, self.debug_mode)
        app_manager = AppManager(self.context, self.debug_mode)

        # Check if we have a navigation request to jump to a specific step
        if hasattr(self.context, 'navigation_request') and self.context.navigation_request:
            nav_req = self.context.navigation_request
            self.context.navigation_request = None  # Clear the request

            # Map navigation step to our internal step numbers
            if workflow_type == 'sink':
                if nav_req.target_step == SinkWorkflowSteps.COLLECT_TOPIC:
                    current_step = 3  # Jump to topic selection
                    printer.print("\n⬅️ Going back to topic selection...\n")
                elif nav_req.target_step == SinkWorkflowSteps.COLLECT_WORKSPACE:
                    current_step = 2  # Jump to workspace selection
                elif nav_req.target_step == SinkWorkflowSteps.COLLECT_APP_NAME:
                    current_step = 1  # Jump to app name
                else:
                    current_step = 0  # Default to requirements
            else:
                # Source workflow doesn't have topic selection
                if nav_req.target_step == SourceWorkflowSteps.COLLECT_WORKSPACE:
                    current_step = 2  # Jump to workspace selection
                elif nav_req.target_step == SourceWorkflowSteps.COLLECT_APP_NAME:
                    current_step = 1  # Jump to app name
                else:
                    current_step = 0  # Default to requirements
        else:
            # Track current step for navigation: 0=requirements, 1=app_name, 2=workspace, 3=topic
            current_step = 0

        app_name = None
        cached_app_name_handled = False

        while current_step <= 3:
            try:
                if current_step == 0:
                    # STEP 1: Collect technology/requirements
                    clear_screen()
                    if not await self.collect_technology_info(workflow_type):
                        raise NavigationBackRequest("User requested to go back from requirements")
                    current_step = 1

                elif current_step == 1:
                    # STEP 2: Collect app name (with AI suggestion)
                    clear_screen()

                    # Only check for cached app name once
                    if not cached_app_name_handled:
                        cached_app_name = cache_utils.check_cached_app_name()
                        cached_app_name_handled = True

                        if cached_app_name:
                            if cache_utils.use_cached_app_name(cached_app_name):
                                app_name = cached_app_name
                                printer.print(f"✅ Using cached application name: {app_name}")
                            else:
                                app_name = await self._get_app_name_with_suggestion(workflow_type)
                                if not app_name:
                                    raise NavigationBackRequest("User requested to go back from app name")
                                cache_utils.save_app_name_to_cache(app_name)
                        else:
                            app_name = await self._get_app_name_with_suggestion(workflow_type)
                            if not app_name:
                                raise NavigationBackRequest("User requested to go back from app name")
                            cache_utils.save_app_name_to_cache(app_name)
                    else:
                        # On subsequent visits to this step, just ask for app name
                        app_name = await self._get_app_name_with_suggestion(workflow_type)
                        if not app_name:
                            raise NavigationBackRequest("User requested to go back from app name")
                        cache_utils.save_app_name_to_cache(app_name)

                    # Sanitize the app name
                    import re
                    sanitized_name = re.sub(r'[^a-zA-Z0-9-_]', '-', app_name)
                    self.context.deployment.application_name = sanitized_name
                    printer.print(f"✅ Application name: {sanitized_name}")
                    current_step = 2

                elif current_step == 2:
                    # STEP 3: Workspace selection
                    clear_screen()

                    # Check for cached prerequisites first
                    cache_result = await self.check_for_cached_prerequisites(workflow_type)
                    if cache_result:
                        # Cache was accepted with topic info, we're done
                        return True

                    # Collect workspace info
                    if not await self.collect_workspace_info():
                        raise NavigationBackRequest("User requested to go back from workspace")

                    # Check for app name collision
                    if not await app_manager.check_and_handle_app_name_collision(self.context.deployment.application_name):
                        return False

                    current_step = 3

                elif current_step == 3:
                    # STEP 4: Topic selection
                    if not await self.collect_topic_info(workflow_type):
                        raise NavigationBackRequest("User requested to go back from topic")

                    # All steps completed successfully
                    break

            except NavigationBackRequest as e:
                # Handle back navigation between steps
                if current_step > 0:
                    # Special handling: if going back from topic (step 3) and workspace is automated,
                    # skip workspace (step 2) and go directly to app name (step 1)
                    if current_step == 3 and os.environ.get('QUIX_WORKSPACE_ID'):
                        current_step = 1  # Skip automated workspace, go to app name
                        printer.print("\n⬅️ Going back to application name (skipping automated workspace)...\n")
                    else:
                        current_step -= 1
                        printer.print("\n⬅️ Going back to previous step...\n")
                else:
                    # At first step, bubble up to phase navigation
                    raise
        
        # Cache the prerequisites (workspace and topic only)
        self.cache_prerequisites(workflow_type)
        
        printer.print(f"✅ Workspace and topic selection completed!")
        return True
    
    async def check_for_cached_prerequisites(self, workflow_type: Literal["sink", "source"]) -> bool:
        """Check for cached prerequisites and prompt user to reuse them.
        
        Args:
            workflow_type: Type of workflow
            
        Returns:
            True if cached prerequisites were loaded, False otherwise
        """
        from workflow_tools.core.working_directory import WorkingDirectory
        
        # Reset cache display flag
        self._cache_was_displayed = False
        
        # Look for existing prerequisites cache files in proper cache directory
        # Use the prerequisites path to derive the directory
        temp_path = WorkingDirectory.get_cached_prerequisites_path(workflow_type, "temp")
        cache_dir = os.path.dirname(temp_path)
        os.makedirs(cache_dir, exist_ok=True)
        
        # Get the app name to look for specific cache
        app_name = getattr(self.context.deployment, 'application_name', None)
        
        if app_name:
            # Look for cache files specific to this app
            safe_app_name = sanitize_name(app_name)
            cache_pattern = os.path.join(cache_dir, f"prerequisites_{safe_app_name}_*.json")
        else:
            # Fallback to any prerequisites cache file
            cache_pattern = os.path.join(cache_dir, "prerequisites_*.json")
        
        existing_cache_files = glob.glob(cache_pattern)
        
        if not existing_cache_files:
            return False
        
        # Find the newest cache file based on timestamp in filename
        # Pattern is: prerequisites_{app_name}_{timestamp}.json
        newest_cache = max(existing_cache_files, key=lambda x: os.path.basename(x).split('_')[-1].split('.')[0])
        
        printer.print(f"\n📋 Found cached {workflow_type} prerequisites")
        
        try:
            with open(newest_cache, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            
            # Use the new beautiful cache panel display
            content_dict = {}

            # Only show topic info in cache now (workspace comes from env var)
            if workflow_type == "source":
                content_dict["Output Topic ID"] = cached_data.get('topic_id', 'N/A')
                content_dict["Output Topic Name"] = cached_data.get('topic_name', 'N/A')
            else:
                content_dict["Topic ID"] = cached_data.get('topic_id', 'N/A')
                content_dict["Topic Name"] = cached_data.get('topic_name', 'N/A')
            
            # Display the beautiful cache panel
            printer.print_cache_panel(
                title=f"Cached {workflow_type.capitalize()} Prerequisites",
                cache_file=newest_cache,
                content_dict=content_dict,
                border_style="bright_cyan"
            )
            
            # Mark that cache was displayed
            self._cache_was_displayed = True
            
            response = get_user_approval_with_back("Do you want to use these cached prerequisites?", allow_back=True)
            if response == 'back':
                raise NavigationBackRequest("User requested to go back")
            use_cached = (response == 'yes')
            if use_cached:
                # Load cached topic data into context
                self.context.workspace.topic_id = cached_data['topic_id']
                self.context.workspace.topic_name = cached_data['topic_name']

                # Get workspace from environment or cached data (for backwards compatibility)
                workspace_id = os.environ.get('QUIX_WORKSPACE_ID') or cached_data.get('workspace_id')
                if workspace_id:
                    self.context.workspace.workspace_id = workspace_id
                    # Get workspace details
                    try:
                        workspace_details = await quix_tools.get_workspace_details(workspace_id)
                        if workspace_details:
                            self.context.workspace.workspace_name = workspace_details.get('name', workspace_id)
                            self.context.workspace.branch_name = workspace_details.get('branch', 'main')
                            if 'repositoryId' in workspace_details:
                                self.context.workspace.repository_id = workspace_details['repositoryId']
                    except Exception as e:
                        if self.debug_mode:
                            printer.print_debug(f"Could not get workspace details: {e}")
                        self.context.workspace.workspace_name = workspace_id
                        self.context.workspace.branch_name = 'main'
                else:
                    printer.print("⚠️ No workspace configured. You'll need to select one.")
                    return False

                printer.print("✅ Using cached topic settings.")
                return True
            else:
                printer.print("🔄 Collecting new prerequisites.")
                
        except NavigationBackRequest:
            # Re-raise navigation requests
            raise
        except Exception as e:
            printer.print(f"⚠️ Error loading cached prerequisites: {e}")
        
        return False
    
    async def collect_workspace_info(self) -> bool:
        """Collect workspace information from user.

        Returns:
            True if successful, False otherwise
        """
        printer.print_section_header("Step 3: Workspace Selection", icon="🏢", style="cyan")

        # Check if QUIX_WORKSPACE_ID is already set in environment
        default_workspace_id = os.environ.get('QUIX_WORKSPACE_ID')
        if default_workspace_id:
            printer.print(f"✅ Using default workspace: {default_workspace_id}")

            # Store workspace info
            self.context.workspace.workspace_id = default_workspace_id

            # Try to get additional workspace details
            try:
                workspace_details = await quix_tools.get_workspace_details(default_workspace_id)
                if workspace_details and isinstance(workspace_details, dict):
                    self.context.workspace.workspace_name = workspace_details.get('name', default_workspace_id)
                    self.context.workspace.branch_name = workspace_details.get('branch', 'main')
                    if 'repositoryId' in workspace_details:
                        self.context.workspace.repository_id = workspace_details['repositoryId']
                elif isinstance(workspace_details, str):
                    # API returned a string error message instead of JSON
                    printer.print(f"❌ Failed to get workspace details for '{default_workspace_id}'")
                    printer.print(f"   Error response: {workspace_details}")
                    printer.print(f"\n   This workspace may not exist or you may not have access to it.")
                    printer.print(f"   Would you like to select a different workspace?\n")

                    response = get_user_approval("Select a different workspace?")
                    if response:
                        default_workspace_id = None
                    else:
                        return False
            except QuixApiError as e:
                if e.status_code == 403:
                    printer.print(f"❌ Permission denied for workspace '{default_workspace_id}'")
                    printer.print(f"   Error: {e}")
                    printer.print(f"\n   Your PAT token doesn't have access to this workspace.")
                    printer.print(f"   Would you like to select a different workspace?\n")

                    response = get_user_approval("Select a different workspace?")
                    if response:
                        # Clear the environment variable temporarily and continue to manual selection
                        default_workspace_id = None
                    else:
                        return False
                else:
                    printer.print(f"❌ API error when accessing workspace '{default_workspace_id}'")
                    printer.print(f"   Error: {e}")
                    printer.print(f"\n   Would you like to select a different workspace?\n")

                    response = get_user_approval("Select a different workspace?")
                    if response:
                        default_workspace_id = None
                    else:
                        return False
            except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                printer.print(f"❌ Connection timeout when accessing workspace '{default_workspace_id}'")
                printer.print(f"   Error: {e}")
                printer.print(f"\n   Possible causes:")
                printer.print(f"   - Network connectivity issues")
                printer.print(f"   - Firewall blocking access to portal-api.cloud.quix.io")
                printer.print(f"   - Proxy configuration needed")
                printer.print(f"\n   Would you like to select a different workspace?\n")

                response = get_user_approval("Select a different workspace?")
                if response:
                    default_workspace_id = None
                else:
                    return False
            except (httpx.ConnectError, httpx.NetworkError) as e:
                printer.print(f"❌ Connection failed when accessing workspace '{default_workspace_id}'")
                printer.print(f"   Error: {e}")
                printer.print(f"\n   Unable to connect to Quix API. Possible causes:")
                printer.print(f"   - No internet connection")
                printer.print(f"   - DNS resolution issues")
                printer.print(f"   - Firewall or security software blocking the connection")
                printer.print(f"\n   Would you like to select a different workspace?\n")

                response = get_user_approval("Select a different workspace?")
                if response:
                    default_workspace_id = None
                else:
                    return False
            except Exception as e:
                printer.print(f"❌ Unexpected error accessing workspace '{default_workspace_id}'")
                printer.print(f"   Error type: {type(e).__name__}")
                printer.print(f"   Error details: {e}")
                printer.print(f"\n   Would you like to select a different workspace?\n")

                response = get_user_approval("Select a different workspace?")
                if response:
                    default_workspace_id = None
                else:
                    return False

            # If we cleared the default_workspace_id due to permission issues, continue to manual selection
            if default_workspace_id:
                return True

        try:
            # Get list of workspaces
            printer.print("Fetching available workspaces...")
            workspaces_df = await quix_tools.find_workspaces()
            
            if workspaces_df.empty:
                printer.print("❌ No workspaces found.")
                return False
            
            from workflow_tools.core.questionary_utils import select, clear_screen
            
            # Clear screen before showing workspace menu
            clear_screen()
            
            # Use questionary for workspace selection
            # Convert dataframe to choices for questionary
            choices = []
            workspace_map = {}
            for _, row in workspaces_df.iterrows():
                display_name = f"{row['Workspace Name']}\n      {row['Workspace ID']}"
                value = row['Workspace ID']
                choices.append({'name': display_name, 'value': value})
                workspace_map[value] = row.to_dict()
            
            # Add back option to go to app name
            choices.append({'name': '← Go back to application name', 'value': 'back'})

            selected_id = select("📋 Available Workspaces", choices, show_border=True)
            
            # Check if user wants to go back
            if selected_id == 'back':
                raise NavigationBackRequest("User requested to go back")
            
            # Get the full workspace data from the map
            selected_workspace = workspace_map[selected_id]
            
            # Store workspace info directly from selected dict
            self.context.workspace.workspace_id = selected_workspace['Workspace ID']
            self.context.workspace.workspace_name = selected_workspace['Workspace Name']
            self.context.workspace.branch_name = selected_workspace.get('Branch', 'main')
            
            # Get repository ID for secret management
            try:
                workspace_details = await quix_tools.get_workspace_details(self.context.workspace.workspace_id)
                if workspace_details and 'repositoryId' in workspace_details:
                    self.context.workspace.repository_id = workspace_details['repositoryId']
                    if self.debug_mode:
                        printer.print_debug(f"Repository ID: {self.context.workspace.repository_id}")
                else:
                    printer.print("⚠️ Warning: Could not retrieve repository ID for secret management")
            except Exception as e:
                printer.print(f"⚠️ Warning: Could not get workspace details: {e}")
            
            printer.print(f"✅ Selected workspace: {selected_workspace['Workspace Name']}")
            printer.print("")  # Add blank line for spacing
            return True
            
        except NavigationBackRequest:
            raise  # Re-raise navigation requests
        except QuixApiError as e:
            # Display the detailed error message from QuixApiError
            printer.print(str(e))
            return False
        except Exception as e:
            printer.print(f"❌ Error collecting workspace info: {e}")
            return False
    
    async def collect_topic_info(self, workflow_type: Literal["sink", "source"]) -> bool:
        """Collect topic information based on workflow type.

        Args:
            workflow_type: Type of workflow

        Returns:
            True if successful, False otherwise
        """
        topic_label = "output topic" if workflow_type == "source" else "source topic"
        printer.print_section_header(f"Step 4: {topic_label.title()} Selection", icon="📊", style="cyan")

        try:
            # Get list of topics
            printer.print(f"Fetching available topics in workspace...")
            topics_df = await quix_tools.find_topics(self.context.workspace.workspace_id)

            # Check for demo topic and create if it doesn't exist
            demo_topic_name = "demo-output-topic" if workflow_type == "source" else "demo-input-topic"
            demo_topic_exists = False
            demo_topic_created = False

            if not topics_df.empty:
                # Check if demo topic already exists
                for _, row in topics_df.iterrows():
                    if row['Topic Name'] == demo_topic_name:
                        demo_topic_exists = True
                        break

            # Create demo topic if it doesn't exist
            if not demo_topic_exists:
                printer.print(f"📝 Creating default {demo_topic_name} for first-time use...")
                try:
                    result = await quix_tools.manage_topic(
                        action=quix_tools.TopicAction.create,
                        workspace_id=self.context.workspace.workspace_id,
                        name=demo_topic_name,
                        partitions=1
                    )
                    if result:
                        printer.print(f"✅ Created {demo_topic_name} successfully!")
                        demo_topic_created = True
                        # Refresh topics list
                        topics_df = await quix_tools.find_topics(self.context.workspace.workspace_id)
                except QuixApiError as e:
                    if e.status_code == 403:
                        printer.print(f"❌ Permission denied: Cannot create topics in this workspace")
                        return False
                    else:
                        printer.print(f"⚠️ Could not create demo topic: {e}")
                except Exception as e:
                    printer.print(f"⚠️ Could not create demo topic: {e}")
                    # Continue anyway, user can select or create another

            if topics_df.empty:
                # If we just created a demo topic successfully, use it
                if demo_topic_created:
                    self.context.workspace.topic_name = demo_topic_name
                    self.context.workspace.topic_id = f"{self.context.workspace.workspace_id}-{demo_topic_name}"
                    printer.print(f"✅ Using newly created {demo_topic_name}")

                    # Log the topic URL
                    url_builder = QuixPortalURLBuilder()
                    topic_url = url_builder.get_topic_url(
                        workspace=self.context.workspace.workspace_id,
                        topic_name=demo_topic_name
                    )
                    printer.print(f"🔗 Topic URL: {topic_url}")
                    return True

                printer.print(f"❌ No topics found in the workspace.")
                # For source workflows, offer to create a topic
                if workflow_type == "source":
                    response = get_user_approval_with_back("Would you like to create a new topic?", allow_back=True)
                    if response == 'back':
                        raise NavigationBackRequest("User requested to go back")
                    create_new = (response == 'yes')
                    if create_new:
                        return await self._create_new_topic()
                return False
            
            from workflow_tools.core.questionary_utils import select, clear_screen
            
            # Clear screen before showing topic menu
            clear_screen()
            
            # Use questionary for topic selection
            # Convert dataframe to choices for questionary
            choices = []
            topic_map = {}
            demo_topic_name = "demo-output-topic" if workflow_type == "source" else "demo-input-topic"
            demo_choice = None

            for _, row in topics_df.iterrows():
                topic_name = row['Topic Name']
                display_name = f"{topic_name} (Partitions: {row.get('Partitions', 'N/A')}, Retention: {row.get('Retention (hours)', 'N/A')}h)"

                # Mark demo topic as default
                if topic_name == demo_topic_name:
                    display_name = f"⭐ {display_name} [RECOMMENDED FOR FIRST TIME]"
                    demo_choice = {'name': display_name, 'value': topic_name}
                else:
                    choices.append({'name': display_name, 'value': topic_name})
                topic_map[topic_name] = row.to_dict()

            # Put demo topic at the top if it exists
            if demo_choice:
                choices.insert(0, demo_choice)

            # Add create new option for source workflows
            if workflow_type == "source":
                choices.append({'name': '🆕 Create a new topic', 'value': 'CREATE_NEW'})

            # Add back option - if workspace is automated, indicate we're going back to app name
            if os.environ.get('QUIX_WORKSPACE_ID'):
                choices.append({'name': '← Go back to application name', 'value': 'back'})
            else:
                choices.append({'name': '← Go back to workspace selection', 'value': 'back'})
            
            selected = select(f"📋 Available Topics for {topic_label}", choices, show_border=True)
            
            # Check if user wants to go back
            if selected == 'back':
                raise NavigationBackRequest("User requested to go back")
            
            # Check if user wants to create a new topic
            if selected == 'CREATE_NEW':
                return await self._create_new_topic()
            
            # Get the full topic data from the map
            selected_topic = topic_map[selected]
            
            # Store topic info using the selected topic dict
            self.context.workspace.topic_id = selected_topic['Topic ID']
            self.context.workspace.topic_name = selected_topic['Topic Name']
            
            printer.print(f"✅ Selected {topic_label}: {selected_topic['Topic Name']}")
            printer.print("")  # Add blank line for spacing
            
            # Log the topic URL
            url_builder = QuixPortalURLBuilder()
            topic_url = url_builder.get_topic_url(
                workspace=self.context.workspace.workspace_id,
                topic_name=selected_topic['Topic Name']
            )
            printer.print(f"🔗 Topic URL: {topic_url}")
            
            return True
            
        except NavigationBackRequest:
            raise  # Re-raise navigation requests
        except QuixApiError as e:
            if e.status_code == 403:
                printer.print(f"❌ Permission denied: Cannot access topics in workspace '{self.context.workspace.workspace_id}'")
                printer.print(f"\n💡 This workspace doesn't match your PAT token's permissions.")
                printer.print(f"   Please go back and select a different workspace.\n")
            else:
                printer.print(f"❌ API Error: {e}")
            return False
        except Exception as e:
            printer.print(f"❌ Error collecting topic info: {e}")
            return False
    
    async def _create_new_topic(self) -> bool:
        """Create a new topic for source workflow.
        
        Returns:
            True if successful, False otherwise
        """
        printer.print_section_header("Creating New Topic", icon="🆕", style="yellow")
        
        topic_name = printer.input("Enter name for the new topic: ").strip()
        if not topic_name:
            printer.print("❌ Topic name cannot be empty.")
            return False
        
        # Sanitize topic name
        sanitized_name = sanitize_name(topic_name)
        if sanitized_name != topic_name:
            printer.print(f"ℹ️ Topic name sanitized to: {sanitized_name}")
            topic_name = sanitized_name
        
        try:
            printer.print(f"Creating topic '{topic_name}'...")
            result = await quix_tools.manage_topic(
                action=quix_tools.TopicAction.create,
                workspace_id=self.context.workspace.workspace_id,
                name=topic_name,
                partitions=1
            )
            
            if result:
                self.context.workspace.topic_name = topic_name
                self.context.workspace.topic_id = f"{self.context.workspace.workspace_id}-{topic_name}"
                printer.print(f"✅ Topic '{topic_name}' created successfully!")
                
                # Log the topic URL
                url_builder = QuixPortalURLBuilder()
                topic_url = url_builder.get_topic_url(
                    workspace=self.context.workspace.workspace_id,
                    topic_name=topic_name
                )
                printer.print(f"🔗 Topic URL: {topic_url}")
                return True
            else:
                printer.print("❌ Failed to create topic.")
                return False
                
        except Exception as e:
            printer.print(f"❌ Error creating topic: {e}")
            return False
    
    
    async def collect_technology_info(self, workflow_type: Literal["sink", "source"]) -> bool:
        """Collect technology information based on workflow type.

        Args:
            workflow_type: Type of workflow

        Returns:
            True if successful, False otherwise
        """
        from workflow_tools.phases.shared.cache_utils import CacheUtils
        cache_utils = CacheUtils(self.context, self.debug_mode)

        # Check for cached user prompt/requirements
        cached_requirements = cache_utils.check_cached_user_prompt()

        if cached_requirements:
            # Show cached requirements and ask if they want to use them
            if cache_utils.use_cached_user_prompt(cached_requirements):
                # Store cached requirements
                if workflow_type == "source":
                    self.context.technology.source_technology = cached_requirements
                    self.context.technology.destination_technology = cached_requirements  # For compatibility
                else:
                    self.context.technology.destination_technology = cached_requirements

                printer.print(f"✅ Using cached requirements!")
                return True

        # No cache or user chose to enter fresh requirements
        if workflow_type == "source":
            printer.print_section_header("Step 1: What do you want to build?", icon="🎯", style="cyan")
            printer.print("\nDescribe what you want to connect to or build:")
            printer.print("(e.g., \"I want to read sensor data from an MQTT broker\" or")
            printer.print("       \"Connect to a weather API and fetch forecasts every hour\")")
        else:
            printer.print_section_header("Step 1: What do you want to build?", icon="🎯", style="cyan")
            printer.print("\nDescribe what you want to build or where you want to send data:")
            printer.print("(e.g., \"I want to store events in a PostgreSQL database\" or")
            printer.print("       \"Send alerts to a Slack channel when thresholds are exceeded\")")

        user_input = printer.input("\nYour requirements: ").strip()

        if not user_input:
            printer.print(f"❌ Requirements cannot be empty.")
            return False

        # Store user requirements - this is what we'll use for app name suggestion
        if workflow_type == "source":
            self.context.technology.source_technology = user_input
            self.context.technology.destination_technology = user_input  # For compatibility
        else:
            self.context.technology.destination_technology = user_input

        # Save to cache for future runs
        cache_utils.save_user_prompt_to_cache(user_input)

        printer.print(f"✅ Got it! I understand what you want to build.")

        return True
    
    
    async def _search_library_items(self, technology: str, workflow_type: Literal["sink", "source"]) -> None:
        """Search for relevant library items for the technology.
        
        Args:
            technology: Technology name
            workflow_type: Type of workflow
        """
        try:
            printer.print(f"\n🔍 Searching Quix library for {technology} {workflow_type}s...")
            
            # Determine item type based on workflow
            item_type = "Source" if workflow_type == "source" else "Destination"
            
            # Search library
            results = await quix_tools.find_in_library(
                workspace_id=self.context.workspace.workspace_id,
                search_term=technology,
                item_type=item_type
            )
            
            if results:
                printer.print(f"✅ Found {len(results)} relevant library items")
                
                # Check for exact matches
                exact_matches = [r for r in results if technology.lower() in r['name'].lower()]
                if exact_matches:
                    self.context.technology.library_results = exact_matches
                    self.context.technology.has_exact_template_match = True
                    printer.print(f"🎯 Found {len(exact_matches)} exact matches!")
                else:
                    self.context.technology.library_results = results[:5]  # Limit to top 5
                    self.context.technology.has_exact_template_match = False
            else:
                printer.print(f"ℹ️ No specific library items found for {technology}")
                self.context.technology.library_results = []
                self.context.technology.has_exact_template_match = False
                
        except Exception as e:
            printer.print(f"⚠️ Could not search library: {e}")
            self.context.technology.library_results = []
            self.context.technology.has_exact_template_match = False

    async def _get_app_name_with_suggestion(self, workflow_type: Literal["sink", "source"]) -> Optional[str]:
        """Get app name from user with AI suggestion based on requirements.

        Args:
            workflow_type: Type of workflow

        Returns:
            App name or None if user wants to go back
        """
        clear_screen()
        printer.print_section_header("Step 2: Application Name", icon="📝", style="cyan")
        printer.print(f"\nWhat would you like to name your {workflow_type} application?")
        printer.print("   (This will be the name shown in the Quix portal)")

        # Get AI suggestion based on requirements
        suggested_name = await self._suggest_app_name(workflow_type)

        if suggested_name:
            printer.print(f"\n💡 Suggested name: {suggested_name}")

            # Offer choice to use suggestion, enter custom, or go back
            choices = [
                {'name': f'✓ Use suggested name: {suggested_name}', 'value': 'use_suggestion'},
                {'name': '✏️  Enter a different name', 'value': 'custom'},
                {'name': '← Go back to requirements', 'value': 'back'}
            ]

            action = select("Choose an option:", choices, show_border=True)

            if action == 'back':
                return None  # Signal to go back
            elif action == 'use_suggestion':
                app_name = suggested_name
            else:  # custom
                # Use questionary for text input with retry logic
                import questionary
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        app_name = questionary.text(
                            "Application name:",
                            style=QUESTIONARY_STYLE
                        ).ask()

                        if app_name and app_name.strip():
                            break
                        elif retry < max_retries - 1:
                            printer.print("⚠️ Application name cannot be empty. Please try again.")
                        else:
                            printer.print("❌ Failed to get application name after multiple attempts.")
                            return None
                    except Exception as e:
                        if self.debug_mode:
                            printer.print_debug(f"Error getting app name input: {e}")
                        if retry < max_retries - 1:
                            printer.print("⚠️ Error reading input. Please try again.")
                        else:
                            printer.print("❌ Failed to read input. Please check your terminal compatibility.")
                            return None
        else:
            # No suggestion available, offer to enter name or go back
            choices = [
                {'name': '✏️  Enter application name', 'value': 'enter'},
                {'name': '← Go back to requirements', 'value': 'back'}
            ]

            action = select("Choose an option:", choices, show_border=True)

            if action == 'back':
                return None  # Signal to go back
            else:
                # Use questionary for text input with retry logic
                import questionary
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        app_name = questionary.text(
                            "Application name:",
                            style=QUESTIONARY_STYLE
                        ).ask()

                        if app_name and app_name.strip():
                            break
                        elif retry < max_retries - 1:
                            printer.print("⚠️ Application name cannot be empty. Please try again.")
                        else:
                            printer.print("❌ Failed to get application name after multiple attempts.")
                            return None
                    except Exception as e:
                        if self.debug_mode:
                            printer.print_debug(f"Error getting app name input: {e}")
                        if retry < max_retries - 1:
                            printer.print("⚠️ Error reading input. Please try again.")
                        else:
                            printer.print("❌ Failed to read input. Please check your terminal compatibility.")
                            return None

        if not app_name or not app_name.strip():
            # Final fallback: generate a default name based on workflow type and timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            fallback_name = f"{workflow_type}-app-{timestamp}"
            printer.print(f"⚠️ No valid application name provided. Using default: {fallback_name}")
            return fallback_name

        return app_name.strip()

    async def _suggest_app_name(self, workflow_type: Literal["sink", "source"]) -> Optional[str]:
        """Generate an app name suggestion using AI based on requirements.

        Args:
            workflow_type: Type of workflow

        Returns:
            Suggested app name or None if generation fails
        """
        try:
            # Get the technology/requirements that were just collected
            tech = getattr(self.context.technology, 'destination_technology' if workflow_type == 'sink' else 'source_technology', None)

            if not tech:
                return None

            # Create the app name suggester agent
            agent = create_agent_with_model_config(
                agent_name="AppNameSuggesterAgent",
                task_type="app_name_suggestion",
                workflow_type=workflow_type,
                instructions=load_agent_instructions("AppNameSuggesterAgent"),
                context_type=WorkflowContext
            )

            # Format the prompt with requirements
            prompt = load_agent_instructions("AppNameSuggesterAgent")
            prompt = prompt.replace("{requirements}", tech)
            prompt = prompt.replace("{workflow_type}", workflow_type)

            # Get suggestion from AI with short timeout
            import asyncio
            result = await asyncio.wait_for(
                Runner.run(starting_agent=agent, input=prompt),
                timeout=10  # 10 second timeout for quick response
            )

            suggested_name = result.final_output.strip()

            # Sanitize the suggested name
            import re
            suggested_name = re.sub(r'[^a-zA-Z0-9-]', '-', suggested_name)
            suggested_name = suggested_name.lower()[:30]  # Limit to 30 chars

            return suggested_name

        except Exception as e:
            if self.debug_mode:
                printer.print_debug(f"Could not generate app name suggestion: {e}")
            return None

    def cache_prerequisites(self, workflow_type: Literal["sink", "source"]) -> None:
        """Cache the collected prerequisites to a file.

        Args:
            workflow_type: Type of workflow
        """
        try:
            # Prepare cache data - only topic info now (workspace is in env var)
            cache_data = {
                "topic_id": self.context.workspace.topic_id,
                "topic_name": self.context.workspace.topic_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Save to file
            from workflow_tools.core.working_directory import WorkingDirectory
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            app_name = getattr(self.context.deployment, 'application_name', 'app')
            safe_app_name = sanitize_name(app_name)
            
            # Build the cache file path with app name included
            temp_path = WorkingDirectory.get_cached_prerequisites_path(workflow_type, "temp")
            cache_dir = os.path.dirname(temp_path)
            os.makedirs(cache_dir, exist_ok=True)
            
            # Create filename with app name and timestamp
            cache_filename = f"prerequisites_{safe_app_name}_{timestamp}.json"
            cache_file = os.path.join(cache_dir, cache_filename)
            
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
            
            printer.print(f"\n💾 Prerequisites cached to: {cache_file}")
            
        except Exception as e:
            printer.print(f"⚠️ Could not cache prerequisites: {e}")

