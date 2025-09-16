# app_management.py - Application creation and management functionality

import os
import zipfile
import io
import requests
from typing import Optional
from workflow_tools.contexts import WorkflowContext
from workflow_tools.common import printer, sanitize_name, generate_unique_app_name, ensure_name_length_limit
from workflow_tools.integrations import quix_tools
from workflow_tools.core.url_builder import QuixPortalURLBuilder
from workflow_tools.core.working_directory import WorkingDirectory


class AppManager:
    """Handles application creation, downloading, and setup."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        self.context = context
        self.debug_mode = debug_mode
    
    def download_and_extract_app_code(self, workspace_id: str, application_id: str) -> Optional[str]:
        """Download and extract application code to the current working directory."""
        # Get environment variables for API access
        token = os.environ.get("QUIX_TOKEN")
        base_url = os.environ.get("QUIX_BASE_URL", "https://portal-api.platform.quix.io")
        
        if not token:
            printer.print("")  # Add spacing before error
            printer.print("❌ Error: QUIX_TOKEN environment variable not set.")
            printer.print("")
            printer.print("No Quix PAT token detected.")
            printer.print("To get one, sign up for a free Quix account here:")
            printer.print_markup("[bold cyan][link=https://portal.cloud.quix.io/signup?utm_campaign=klaus-kode]https://portal.cloud.quix.io/signup?utm_campaign=klaus-kode[/link][/bold cyan]")
            printer.print("")  # Add spacing after error
            return None
        
        # Create the API URL
        url = f"{base_url}/{workspace_id}/applications/{application_id}/zip"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Version": "2.0"
        }
        
        try:
            printer.print_verbose(f"🔄 Downloading application code from Quix.")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                # Clear and use the current app directory
                extract_dir = WorkingDirectory.get_current_app_dir()
                WorkingDirectory.clear_current_app()  # Clear any existing content
                
                # Extract zip content
                zip_data = io.BytesIO(response.content)
                with zipfile.ZipFile(zip_data, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                printer.print(f"✅ Application code extracted to: {extract_dir}")
                
                # List extracted files for debugging
                if self.debug_mode:
                    printer.print_debug("📁 Extracted files:")
                    for filename in os.listdir(extract_dir):
                        printer.print_debug(f"  - {filename}")
                
                return extract_dir
                
            elif response.status_code == 204:
                printer.print("⚠️ No content received. Application might be empty.")
                return None
            elif response.status_code == 401:
                printer.print("❌ Error: Unauthorized. Check if your QUIX_TOKEN is correct.")
                return None
            elif response.status_code == 404:
                printer.print(f"❌ Error: Application or workspace not found.")
                return None
            else:
                printer.print(f"❌ Error downloading application code. Status: {response.status_code}")
                return None
                
        except Exception as e:
            printer.print(f"❌ Error during application download: {e}")
            return None

    async def check_and_handle_app_name_collision(self, app_name: str) -> bool:
        """Check for application name collision and handle it.
        
        Args:
            app_name: The application name to check for collisions
            
        Returns:
            True if no collision or collision was resolved, False if user aborted
        """
        from workflow_tools.common import get_user_approval
        
        # Generate path from the name
        base_app_path = sanitize_name(app_name)
        
        printer.print(f"🔍 Checking for existing applications with name '{app_name}'...")
        
        # Search by both name and path to catch all cases
        existing_apps = []
        
        # Search by name
        apps_by_name = await quix_tools.find_applications(
            self.context.workspace.workspace_id,
            search=app_name
        )
        existing_apps.extend(apps_by_name)
        
        # Also search by path (since starter templates use path but different names)
        apps_by_path = await quix_tools.find_applications(
            self.context.workspace.workspace_id,
            search=base_app_path
        )
        existing_apps.extend(apps_by_path)
        
        # Remove duplicates based on applicationId
        seen_ids = set()
        unique_apps = []
        for app in existing_apps:
            app_id = app.get('applicationId')
            if app_id and app_id not in seen_ids:
                seen_ids.add(app_id)
                unique_apps.append(app)
        existing_apps = unique_apps
        
        # Filter to exact matches - check both name AND path
        exact_matches = [
            app for app in existing_apps 
            if app.get('name') == app_name or app.get('path') == f"/{base_app_path}"
        ]
        
        # If an exact match exists, ask the user what to do
        if exact_matches:
            existing_app = exact_matches[0]
            printer.print("")  # Add spacing before warning
            printer.print(f"⚠️  Found existing application '{app_name}' (ID: {existing_app['applicationId']})")
            printer.print("   This application already exists in your workspace.")
            printer.print("")  # Add spacing before menu
            
            from workflow_tools.core.questionary_utils import select
            
            choices = [
                {'name': '🗑️  Delete the existing application and create a fresh one with the same name', 'value': 'delete'},
                {'name': '📝 Keep the existing application and create a new one with a different name', 'value': 'keep'}
            ]
            
            choice = select("What would you like to do?", choices, show_border=True)
            
            delete_existing = (choice == 'delete')
            
            printer.print("")  # Add spacing after selection
            
            if delete_existing:
                printer.print(f"🗑️  Deleting existing application '{app_name}'...")
                
                # Also clean up any existing local directories for this app
                self.cleanup_existing_local_directories(app_name)
                
                deletion_success = await quix_tools.delete_application(
                    self.context.workspace.workspace_id,
                    existing_app['applicationId']
                )
                
                if not deletion_success:
                    printer.print(f"\n⚠️ Failed to delete existing application, will create with a different name")
                    # Fall back to using a random suffix
                    unique_name = generate_unique_app_name(app_name)
                    unique_name = ensure_name_length_limit(unique_name, max_length=50)
                    self.context.deployment.application_name = unique_name
                    printer.print(f"✅ Will use name: {unique_name}")
                else:
                    printer.print("✅ Existing application deleted successfully")
                    # Keep the original name
                    self.context.deployment.application_name = app_name
            else:
                # User chose to keep existing app and create a duplicate
                printer.print("📝 Creating application with a unique name suffix...")
                unique_name = generate_unique_app_name(app_name)
                unique_name = ensure_name_length_limit(unique_name, max_length=50)
                self.context.deployment.application_name = unique_name
                printer.print(f"✅ Will use name: {unique_name}")
        else:
            # No collision, proceed with original name
            printer.print("✅ No name collision detected")
            
        return True

    def cleanup_existing_local_directories(self, application_name: str) -> None:
        """Clean up existing local directories for the given application name.
        
        This removes any existing local directories that might be associated with
        the application to ensure a clean start when recreating an app.
        
        Args:
            application_name: The name of the application to clean up directories for
        """
        import shutil
        
        printer.print("🧹 Cleaning up existing local directories...")
        
        # Look for directories in working_files that might be associated with this app
        working_files_dir = "working_files"
        if not os.path.exists(working_files_dir):
            return
        
        directories_removed = 0
        
        try:
            # Look for any directory that might be related to this app
            # Patterns to look for:
            # - {app_id}_source_code (the main pattern)
            # - Any directory containing the sanitized app name
            sanitized_app_name = sanitize_name(application_name)
            
            for item in os.listdir(working_files_dir):
                item_path = os.path.join(working_files_dir, item)
                
                # Skip files, only process directories
                if not os.path.isdir(item_path):
                    continue
                
                # Check if this directory might be related to our app
                should_remove = False
                
                # NEVER remove cache directories - they should be preserved
                if item.startswith("cached_app_"):
                    should_remove = False
                # Pattern 1: Directory name contains the sanitized app name (but not cache directories)
                elif sanitized_app_name.lower() in item.lower():
                    should_remove = True
                
                # Pattern 2: Directory ends with "_source_code" and we can't identify the app
                # In this case, we'll be more conservative and only remove if we're confident
                if item.endswith("_source_code"):
                    # If we already have an application_id in context, remove any directory with that ID
                    if (hasattr(self.context.deployment, 'application_id') and 
                        self.context.deployment.application_id and 
                        self.context.deployment.application_id in item):
                        should_remove = True
                
                if should_remove:
                    printer.print(f"   Removing directory: {item_path}")
                    shutil.rmtree(item_path, ignore_errors=True)
                    directories_removed += 1
            
            if directories_removed > 0:
                printer.print(f"✅ Removed {directories_removed} existing local director{'y' if directories_removed == 1 else 'ies'}")
            else:
                printer.print("ℹ️ No existing local directories found to clean up")
                
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not clean up some local directories: {e}")
            # Don't fail the whole process if cleanup fails
    
    async def create_application(self) -> bool:
        """Create the application from the selected template."""
        printer.print("📦 Starting application creation from template...")
        
        # Determine if this is a source or sink workflow
        from workflow_tools.workflow_types import WorkflowType
        from workflow_tools.common import get_user_approval
        
        # Check if user already provided an application name
        if hasattr(self.context.deployment, 'application_name') and self.context.deployment.application_name:
            # Use the user-provided name
            base_app_name = self.context.deployment.application_name
            # Ensure the name doesn't exceed the 50 character limit
            base_app_name = ensure_name_length_limit(base_app_name, max_length=50)
            # Generate path from the name (replacing spaces and special chars)
            base_app_path = sanitize_name(base_app_name)
        else:
            # Fallback to auto-generated name (for backward compatibility)
            # Get the appropriate technology name based on workflow type
            if self.context.selected_workflow == WorkflowType.SOURCE:
                tech_name = getattr(self.context.technology, 'source_technology', None) or self.context.technology.destination_technology
                app_type = "source"
            else:  # Default to sink for SINK and other workflows
                tech_name = self.context.technology.destination_technology
                app_type = "sink"
            
            sanitized_tech_name = sanitize_name(tech_name)
            base_app_name = f"{sanitized_tech_name}-{app_type}-draft"
            # Ensure the base name doesn't exceed the 50 character limit
            base_app_name = ensure_name_length_limit(base_app_name, max_length=50)
            base_app_path = f"{sanitized_tech_name}-{app_type}"
        
        # Check for name collision using centralized logic
        # Note: In most cases this was already handled during prerequisites collection,
        # but we keep this as a safety net in case the user bypassed that flow
        if not await self.check_and_handle_app_name_collision(base_app_name):
            return False
        
        # Update the path to match the potentially updated name
        final_app_name = self.context.deployment.application_name
        if final_app_name != base_app_name:
            # Name was changed due to collision, update path accordingly
            base_app_path = sanitize_name(final_app_name)
        
        self.context.deployment.application_path = base_app_path
        
        # Now create the application
        printer.print(f"Creating sandbox application '{self.context.deployment.application_name}' from template '{self.context.technology.library_item_id}'.")
        printer.print(f"  Name: {self.context.deployment.application_name}")
        printer.print(f"  Path: {self.context.deployment.application_path}")
        
        # Try to create the application, with automatic retry on name collision
        # (in case deletion failed or there was a race condition)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                app_data = await quix_tools.create_app_from_template(
                    self.context.workspace.workspace_id, 
                    self.context.technology.library_item_id,
                    self.context.deployment.application_name,
                    self.context.deployment.application_path
                )
                if app_data and app_data.get('applicationId'):
                    break  # Success, exit retry loop
                else:
                    printer.print(f"🔄 Application creation returned empty data, trying with different name.")
                    # Generate a unique name for retry
                    unique_name = generate_unique_app_name(base_app_name)
                    unique_name = ensure_name_length_limit(unique_name, max_length=50)
                    self.context.deployment.application_name = unique_name
                    suffix = unique_name.split('-')[-1]
                    self.context.deployment.application_path = f"{base_app_path}-{suffix}"
            except quix_tools.QuixApiError as e:
                error_msg = str(e).lower()
                if attempt < max_retries - 1 and ("already exists" in error_msg or "conflict" in error_msg or "already in use" in error_msg):
                    if "name" in error_msg:
                        printer.print(f"🔄 Application name '{self.context.deployment.application_name}' already exists, trying with random suffix.")
                    elif "path" in error_msg:
                        printer.print(f"🔄 Application path '{self.context.deployment.application_path}' already in use, trying with random suffix.")
                    else:
                        printer.print(f"🔄 Application name/path collision detected, trying with random suffix.")
                    # Generate a unique name for retry
                    unique_name = generate_unique_app_name(base_app_name)
                    unique_name = ensure_name_length_limit(unique_name, max_length=50)
                    self.context.deployment.application_name = unique_name
                    suffix = unique_name.split('-')[-1]
                    self.context.deployment.application_path = f"{base_app_path}-{suffix}"
                else:
                    printer.print(f"❌ Failed to create application from template: {e}")
                    return False
        
        if not app_data or not app_data.get('applicationId'):
            printer.print("❌ Failed to create application after multiple attempts.")
            return False
        
        # Store application info
        self.context.deployment.application_id = app_data['applicationId']
        
        # Check if the API returned a different name than what we requested
        # The API might use the template's default name instead of our custom name
        actual_app_name = app_data.get('name', self.context.deployment.application_name)
        actual_app_path = app_data.get('path', self.context.deployment.application_path)
        
        if actual_app_name != self.context.deployment.application_name:
            printer.print(f"⚠️ WARNING: API used different name than requested!")
            printer.print(f"   Requested: {self.context.deployment.application_name}")
            printer.print(f"   Actual: {actual_app_name}")
            printer.print(f"   This appears to be a Quix API issue - it's using the template's default name.")
            # Update our context to match what the API actually created
            self.context.deployment.application_name = actual_app_name
        
        if actual_app_path != self.context.deployment.application_path:
            printer.print(f"⚠️ WARNING: API used different path than requested!")
            printer.print(f"   Requested: {self.context.deployment.application_path}")
            printer.print(f"   Actual: {actual_app_path}")
            # Update our context to match what the API actually created
            self.context.deployment.application_path = actual_app_path
        
        # Add check for workspace branch
        workspace_branch = getattr(self.context.workspace, 'branch', None)
        if workspace_branch:
            url_builder = QuixPortalURLBuilder()
            application_url = url_builder.get_application_ide_url(
                self.context.workspace.workspace_id,
                self.context.deployment.application_id,
                workspace_branch
            )
            printer.print(f"✅ Application created successfully!")
            printer.print(f"   Name: {actual_app_name}")
            printer.print(f"   Path: {actual_app_path}")
            printer.print(f"   ID: {self.context.deployment.application_id}")
            printer.print(f"   IDE URL: {application_url}")
        else:
            printer.print(f"✅ Application created successfully!")
            printer.print(f"   Name: {actual_app_name}")
            printer.print(f"   Path: {actual_app_path}")
            printer.print(f"   ID: {self.context.deployment.application_id}")
        
        return True
    
    async def create_ide_session(self, use_app_variables: bool = False) -> bool:
        """Create IDE session without overwriting already loaded template context.
        
        Args:
            use_app_variables: If True, fetch and use the app's existing environment variables
        """
        printer.print("Creating IDE session.")
        
        # Log the application URL for reference
        url_builder = QuixPortalURLBuilder()
        branch = self.context.workspace.branch_name or "main"
        app_url = url_builder.get_application_url(
            workspace=self.context.workspace.workspace_id,
            application_name=self.context.deployment.application_name,
            branch=branch
        )
        printer.print(f"🔗 Running session in application: {app_url}")
        
        # Prepare environment variables and secrets if requested
        environment_variables = None
        secrets = None
        
        if use_app_variables:
            # Fetch application's existing variables for diagnose workflow
            printer.print("📋 Fetching application's existing environment variables...")
            app_details = await quix_tools.get_application_details(
                self.context.workspace.workspace_id,
                self.context.deployment.application_id
            )
            
            if app_details and 'variables' in app_details:
                environment_variables = {}
                secrets = {}
                
                for var in app_details.get('variables', []):
                    var_name = var.get('name')
                    default_value = var.get('defaultValue')
                    input_type = var.get('inputType')
                    
                    if var_name and default_value is not None:
                        if input_type == 'Secret':
                            # For secrets, the defaultValue is the secret key name
                            secrets[var_name] = default_value
                        else:
                            # For regular variables, use the default value
                            environment_variables[var_name] = default_value
                
                if environment_variables or secrets:
                    printer.print(f"✅ Found {len(environment_variables)} variables and {len(secrets)} secrets")
        
        session_data = await quix_tools.manage_session(
            quix_tools.SessionAction.start, 
            self.context.workspace.workspace_id, 
            self.context.deployment.application_id,
            branch_name=self.context.workspace.branch_name,
            environment_variables=environment_variables,
            secrets=secrets
        )
        if not session_data or not session_data.get('sessionId'):
            printer.print(f"🛑 Failed to start IDE session. Aborting.")
            return False
        self.context.deployment.session_id = session_data.get('sessionId')
        printer.print(f"✅ IDE Session started with ID: {self.context.deployment.session_id}")
        return True
    
    def load_template_files(self, extract_dir: str) -> bool:
        """Load template files from extracted directory."""
        # Read template code from extracted files
        main_py_path = os.path.join(extract_dir, "main.py")
        if os.path.exists(main_py_path):
            with open(main_py_path, 'r', encoding='utf-8') as f:
                self.context.code_generation.template_code = f.read()
        else:
            printer.print("⚠️ Warning: main.py not found in extracted code")
            self.context.code_generation.template_code = ""
        
        # Read template requirements from extracted files
        requirements_path = os.path.join(extract_dir, "requirements.txt")
        if os.path.exists(requirements_path):
            # Update quixstreams version before loading
            from workflow_tools.services.requirements_updater import RequirementsUpdater
            updater = RequirementsUpdater()
            updater.update_requirements_file(requirements_path)
            
            # Now read the updated requirements
            with open(requirements_path, 'r', encoding='utf-8') as f:
                self.context.code_generation.template_requirements = f.read()
            printer.print("✅ Loaded requirements.txt from extracted code")
        else:
            printer.print("⚠️ Warning: requirements.txt not found in extracted code")
            self.context.code_generation.template_requirements = ""
        
        return True
    
    def save_debug_files(self) -> None:
        """Save template code and docs to resources folder for debugging."""
        try:
            os.makedirs("resources", exist_ok=True)
            
            # Save template code
            with open("resources/template_code.py", "w", encoding="utf-8") as f:
                f.write(f"# Template code from library item: {self.context.technology.library_item_id}\n")
                f.write(f"# Application ID: {self.context.deployment.application_id}\n")
                f.write(f"# Session ID: {self.context.deployment.session_id}\n")
                f.write(f"# Destination Technology: {self.context.technology.destination_technology}\n\n")
                f.write(self.context.code_generation.template_code or "")
            
            # Save template requirements
            with open("resources/template_requirements.txt", "w", encoding="utf-8") as f:
                f.write(f"# Template requirements from library item: {self.context.technology.library_item_id}\n")
                f.write(f"# Application ID: {self.context.deployment.application_id}\n")
                f.write(f"# Session ID: {self.context.deployment.session_id}\n")
                f.write(f"# Destination Technology: {self.context.technology.destination_technology}\n\n")
                f.write(self.context.code_generation.template_requirements or "")
            
            # Save documentation
            with open("resources/docs_content.md", "w", encoding="utf-8") as f:
                f.write(f"# Documentation gathered for {self.context.technology.destination_technology}\n\n")
                f.write(self.context.code_generation.docs_content or "")
            
            printer.print("🔧 Debug: Template code and docs saved to resources/ folder")
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not save debug files: {e}")