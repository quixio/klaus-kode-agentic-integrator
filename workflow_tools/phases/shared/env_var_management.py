# env_var_management.py - Environment variable management functionality

import os
import re
import yaml
from typing import Dict, Any, List, Optional, Tuple
from workflow_tools.contexts import WorkflowContext
from workflow_tools.common import printer
from workflow_tools.core.prompt_manager import load_task_prompt
from workflow_tools.core.interactive_menu import InteractiveMenu
from workflow_tools.integrations import quix_tools
from workflow_tools.services.secret_manager import SecretManager
from .cache_utils import CacheUtils


class EnvVarManager:
    """Handles environment variable translation, collection, and management."""
    
    def __init__(self, context: WorkflowContext, run_config=None, debug_mode: bool = False):
        self.context = context
        self.run_config = run_config
        self.debug_mode = debug_mode
        self.cache_utils = CacheUtils(context, debug_mode)
        self.secret_manager = SecretManager(context, debug_mode)
    
    def convert_app_yaml_to_env(self, extract_dir: str) -> Optional[str]:
        """Convert app.yaml variables to .env format, handling secrets properly."""
        import os
        
        app_yaml_path = os.path.join(extract_dir, "app.yaml")
        
        if not os.path.exists(app_yaml_path):
            printer.print(f"⚠️ Warning: app.yaml not found in {extract_dir}")
            return None
        
        try:
            with open(app_yaml_path, 'r', encoding='utf-8') as f:
                app_config = yaml.safe_load(f)
            
            # Hard replace deprecated HiddenText with Secret in the YAML
            variables = app_config.get('variables', [])
            yaml_modified = False
            for var in variables:
                if var.get('inputType') == 'HiddenText':
                    var['inputType'] = 'Secret'
                    yaml_modified = True
            
            # Save the modified YAML back to file if changes were made
            if yaml_modified:
                with open(app_yaml_path, 'w', encoding='utf-8') as f:
                    yaml.dump(app_config, f, default_flow_style=False)
                printer.print("✅ Replaced deprecated 'HiddenText' with 'Secret' in app.yaml")
            
            env_content = "# Environment variables converted from app.yaml\n\n"
            
            if not variables:
                printer.print("⚠️ Warning: No variables found in app.yaml")
                return ""
            
            for var in variables:
                var_name = var.get('name', '')
                default_value = var.get('defaultValue', '')
                description = var.get('description', '')
                required = var.get('required', False)
                input_type = var.get('inputType', '')
                
                # Check if this is a secret variable ONLY based on app.yaml inputType
                is_secret = (input_type == 'Secret')
                
                # Add _KEY suffix to secret variables if not already present
                if is_secret and not var_name.upper().endswith('_KEY'):
                    var_name = f"{var_name}_KEY"
                
                if description:
                    env_content += f"# {description}\n"
                env_content += f"# Required: {required}\n"
                env_content += f"# DefaultValue: {default_value}\n"
                if is_secret:
                    env_content += f"# QUIX_SECRET: Enter the name of the Quix secret, not the actual value\n"
                
                env_content += f"{var_name}={default_value}\n\n"
            
            # Save .env file
            env_file_path = os.path.join(extract_dir, ".env")
            with open(env_file_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            # Count secret variables by checking for QUIX_SECRET comments
            secret_count = env_content.count("# QUIX_SECRET:")
            printer.print_verbose(f"✅ Converted app.yaml to .env with {len(variables)} variables ({secret_count} secrets)")
            
            return env_content
            
        except Exception as e:
            printer.print(f"❌ Error converting app.yaml to .env: {e}")
            return None
    
    def _ensure_secret_key_suffixes(self, env_content: str) -> str:
        """Ensure secret variables retain their _KEY suffix after AI translation."""
        lines = env_content.split('\n')
        updated_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this line is a QUIX_SECRET comment
            if line.strip().startswith('# QUIX_SECRET:'):
                # Add this comment line
                updated_lines.append(line)
                
                # Check if the next line is the variable definition
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.strip() and '=' in next_line and not next_line.strip().startswith('#'):
                        var_name, value = next_line.split('=', 1)
                        var_name = var_name.strip()
                        
                        # Ensure secret variable ends with _KEY
                        if not var_name.upper().endswith('_KEY'):
                            var_name = f"{var_name}_KEY"
                            next_line = f"{var_name}={value}"
                            
                            if self.debug_mode:
                                printer.print(f"🔧 Debug: Fixed secret variable to retain _KEY suffix: {var_name}")
                        
                        updated_lines.append(next_line)
                        i += 2  # Skip both the comment and variable lines
                        continue
            
            updated_lines.append(line)
            i += 1
        
        return '\n'.join(updated_lines)
    
    def prepare_app_variables_for_sandbox(self, detected_code_vars: List[str] = None) -> List[Dict[str, Any]]:
        """
        Prepare all user-provided variables for application configuration in sandbox.
        
        Args:
            detected_code_vars: Optional list of variables detected in generated code
            
        Returns:
            List of variable configurations for Quix application
        """
        app_vars_payload = []
        
        # Debug: Log what variables we have
        if self.debug_mode:
            printer.print_debug(f"prepare_app_variables_for_sandbox called")
            printer.print_debug(f"   User-provided vars: {list(self.context.credentials.env_var_values.keys()) if self.context.credentials.env_var_values else 'None'}")
            printer.print_debug(f"   Detected code vars: {detected_code_vars if detected_code_vars else 'None'}")
        
        # ALWAYS add the output/input topic variable if it exists
        if self.context.credentials.env_var_values:
            for topic_name in ['output', 'input']:
                if topic_name in self.context.credentials.env_var_values:
                    var_value = self.context.credentials.env_var_values[topic_name]
                    var_config = {
                        "name": topic_name,
                        "required": True,
                        "defaultValue": str(var_value)  # Ensure string conversion
                    }
                    # Determine type based on workflow
                    from workflow_tools.workflow_types import WorkflowType
                    if self.context.selected_workflow == WorkflowType.SOURCE:
                        var_config["inputType"] = "OutputTopic" if topic_name == "output" else "InputTopic"
                    else:
                        var_config["inputType"] = "InputTopic" if topic_name == "input" else "OutputTopic"
                    app_vars_payload.append(var_config)
        
        # If we have detected code variables, only include those that are actually used
        # This prevents including obsolete template variables
        if detected_code_vars and self.context.credentials.env_var_values:
            # Add variables that are used in the code (excluding topics already added)
            for var_name in detected_code_vars:
                if var_name in ['output', 'input']:
                    continue  # Already added above
                if var_name in self.context.credentials.env_var_values:
                    var_value = self.context.credentials.env_var_values[var_name]
                    var_config = {
                        "name": var_name,
                        "required": True,
                        "defaultValue": str(var_value)  # Ensure string conversion
                    }
                    
                    # Determine input type based on variable name and value patterns
                    var_lower = var_name.lower()
                    
                    # Check for secret variables
                    if any(secret_term in var_lower for secret_term in ['password', 'secret', 'token', 'key', 'auth']):
                        var_config["inputType"] = "Secret"
                    # Check for topic variables - workflow-aware
                    elif "topic" in var_lower or "input" in var_lower or "output" in var_lower:
                        # Determine if this is an input or output topic based on workflow type
                        from workflow_tools.workflow_types import WorkflowType
                        
                        if self.debug_mode:
                            printer.print(f"🔧 Debug: Processing topic variable '{var_name}' with value '{var_value}'")
                            printer.print(f"   Workflow type: {self.context.selected_workflow}")
                        
                        if self.context.selected_workflow == WorkflowType.SINK:
                            # For sink workflows, topics are typically inputs
                            if "output" in var_lower:
                                var_config["inputType"] = "OutputTopic"
                            else:
                                var_config["inputType"] = "InputTopic"
                        elif self.context.selected_workflow == WorkflowType.SOURCE:
                            # For source workflows, topics are typically outputs
                            if "input" in var_lower:
                                var_config["inputType"] = "InputTopic"
                            else:
                                var_config["inputType"] = "OutputTopic"
                        else:
                            # Default behavior for unknown workflow types
                            var_config["inputType"] = "InputTopic"
                        
                        if self.debug_mode:
                            printer.print(f"   Assigned inputType: {var_config['inputType']}")
                        
                        # Use topic name if available and no value provided
                        if self.context.workspace.topic_name and not var_value:
                            var_config["defaultValue"] = str(self.context.workspace.topic_name)  # Ensure string conversion
                    else:
                        var_config["inputType"] = "FreeText"
                    
                    app_vars_payload.append(var_config)
        elif not detected_code_vars and self.context.credentials.env_var_values:
            # No detected variables - fall back to including all user-provided variables
            # This happens during initial setup before code generation
            for var_name, var_value in self.context.credentials.env_var_values.items():
                var_config = {
                    "name": var_name,
                    "required": True,
                    "defaultValue": str(var_value)  # Ensure string conversion
                }
                
                # Determine input type
                var_lower = var_name.lower()
                if any(secret_term in var_lower for secret_term in ['password', 'secret', 'token', 'key', 'auth']):
                    var_config["inputType"] = "Secret"
                elif "topic" in var_lower or "input" in var_lower or "output" in var_lower:
                    from workflow_tools.workflow_types import WorkflowType
                    if self.context.selected_workflow == WorkflowType.SOURCE:
                        var_config["inputType"] = "OutputTopic" if "output" in var_lower else "InputTopic"
                    else:
                        var_config["inputType"] = "InputTopic" if "input" in var_lower else "OutputTopic"
                else:
                    var_config["inputType"] = "FreeText"
                
                app_vars_payload.append(var_config)
        
        # Add any additional variables detected in code that aren't already in user-provided vars
        if detected_code_vars:
            existing_var_names = [v["name"] for v in app_vars_payload]
            for var_name in detected_code_vars:
                if var_name not in existing_var_names:
                    var_config = {
                        "name": var_name,
                        "required": False,  # Not required since user didn't provide it
                        "inputType": "FreeText",
                        "defaultValue": ""  # Already a string
                    }
                    
                    # Try to provide sensible defaults for common variables
                    var_lower = var_name.lower()
                    if "consumer_group" in var_lower:
                        # Get appropriate technology name
                        if self.context.selected_workflow == WorkflowType.SOURCE:
                            tech_name = getattr(self.context.technology, 'source_technology', 'source')
                        else:
                            tech_name = self.context.technology.destination_technology or 'sink'
                        var_config["defaultValue"] = f"{tech_name.lower()}-consumer"
                    elif "buffer_size" in var_lower or "batch_size" in var_lower:
                        var_config["defaultValue"] = "1000"
                    elif "timeout" in var_lower or "delay" in var_lower:
                        var_config["defaultValue"] = "1"
                    
                    app_vars_payload.append(var_config)
        
        return app_vars_payload
    
    async def sync_or_update_app_variables(self, detected_code_vars: List[str] = None, force_update: bool = False) -> bool:
        """
        Smart variable synchronization that preserves manual updates.
        
        This method will:
        1. Check if variables already exist in the application
        2. If they exist and force_update=False, preserve them (just sync to context)
        3. If they don't exist or force_update=True, update them
        
        Args:
            detected_code_vars: Optional list of variables detected in generated code
            force_update: If True, always update app variables (default: False)
            
        Returns:
            True if operation succeeded, False otherwise
        """
        from workflow_tools.integrations import quix_tools
        
        # First, try to get current app variables
        has_existing_vars = await self.sync_variables_from_application()
        
        # Always prepare the full set of variables that should exist
        app_vars_payload = self.prepare_app_variables_for_sandbox(detected_code_vars)
        
        if not app_vars_payload:
            printer.print("  - No variables to configure")
            return True
        
        # Get existing variables from the application
        existing_vars_dict = {}
        try:
            app_details = await quix_tools.get_application_details(
                self.context.workspace.workspace_id,
                self.context.deployment.application_id
            )
            
            if app_details and 'variables' in app_details:
                # Store existing variables in a dict for merging
                for var in app_details['variables']:
                    var_name = var.get('name', '')
                    if var_name:
                        existing_vars_dict[var_name] = var
                printer.print(f"  - Found {len(existing_vars_dict)} existing variables in application")
        except Exception as e:
            printer.print(f"  - Warning: Could not fetch existing variables: {e}")
        
        # When we have detected code variables, we should ONLY include those
        # This naturally excludes template variables that were translated
        if detected_code_vars:
            # Only keep existing variables that are either:
            # 1. In the detected code variables list
            # 2. Topic variables (input/output)
            filtered_existing = {}
            for var_name, var_config in existing_vars_dict.items():
                if var_name in detected_code_vars or var_name.lower() in ['input', 'output']:
                    filtered_existing[var_name] = var_config
                else:
                    printer.print(f"  - Removing unused variable: {var_name}")
            merged_vars = filtered_existing
        else:
            # No detected vars - keep all existing (shouldn't happen in normal flow)
            merged_vars = existing_vars_dict.copy()
        
        # Update with our new/changed variables
        for var_config in app_vars_payload:
            var_name = var_config['name']
            
            # If variable exists and we're not forcing update
            if var_name in existing_vars_dict and not force_update:
                existing_var = existing_vars_dict[var_name].copy()  # Make a copy to avoid modifying original
                
                # Check if we need to update the value
                existing_value = existing_var.get('defaultValue', '')
                our_value = var_config.get('defaultValue', '')
                
                # Special handling for topic variables - always use user's value
                if var_name.lower() in ['input', 'output']:
                    if our_value:
                        existing_var['defaultValue'] = our_value
                        if existing_value != our_value:
                            printer.print(f"  - Updated {var_name} topic from '{existing_value}' to '{our_value}'")
                # Always replace placeholders with real values
                elif existing_value.startswith('{{') and existing_value.endswith('}}'):
                    # This is a placeholder - always replace if we have a value
                    if our_value and not our_value.startswith('{{'):
                        existing_var['defaultValue'] = our_value
                        printer.print(f"  - Replaced placeholder '{existing_value}' with value '{our_value}' for '{var_name}'")
                elif not existing_value and our_value:
                    # Existing is empty, use our value
                    existing_var['defaultValue'] = our_value
                elif existing_value and not our_value:
                    # Keep existing value (silently)
                    pass
                elif our_value and existing_value != our_value:
                    # Both have values but different - in non-force mode, keep existing (silently)
                    pass
                
                # Update inputType if needed
                if 'inputType' in var_config:
                    if existing_var.get('inputType') != var_config['inputType']:
                        # Update type for topic variables
                        if var_config['inputType'] in ['InputTopic', 'OutputTopic']:
                            existing_var['inputType'] = var_config['inputType']
                            printer.print(f"  - Updated type for '{var_name}' to {var_config['inputType']}")
                
                # Copy other properties from our config if they're missing
                for key in ['required', 'description']:
                    if key in var_config and key not in existing_var:
                        existing_var[key] = var_config[key]
                
                merged_vars[var_name] = existing_var
            else:
                # New variable or force update - use our config
                merged_vars[var_name] = var_config
                # Only log for important new variables (not verbose for every var)
                pass
        
        # Check if we actually need to update
        if not force_update and len(merged_vars) == len(existing_vars_dict):
            # Check if anything actually changed
            changes_needed = False
            for var_name, var_config in merged_vars.items():
                if var_name not in existing_vars_dict or existing_vars_dict[var_name] != var_config:
                    changes_needed = True
                    break
            
            if not changes_needed:
                printer.print("  - No changes needed to application variables")
                return True
        
        # Convert merged dict back to list for API
        final_vars_payload = list(merged_vars.values())
        
        # Either force_update=True, no existing vars, or we found missing/changed variables
        printer.print(f"  - Configuring application with {len(final_vars_payload)} variables...")
            
        try:
            await quix_tools.update_application_environment(
                self.context.workspace.workspace_id,
                self.context.deployment.application_id,
                final_vars_payload
            )
            printer.print("  - Application variables configured successfully")
            return True
        except Exception as e:
            printer.print(f"  - Failed to update application variables: {e}")
            return False
    
    async def sync_variables_from_application(self) -> bool:
        """
        Sync environment variables from the current application in Quix.
        This ensures we use the latest variables, including any manual updates
        made during connection testing or debugging.
        
        Returns:
            True if variables were successfully synced, False otherwise
        """
        if not hasattr(self.context.deployment, 'application_id') or not self.context.deployment.application_id:
            printer.print("  - No application ID available for variable sync")
            return False
            
        try:
            from workflow_tools.integrations import quix_tools
            
            printer.print("  - Syncing variables from current application state...")
            app_details = await quix_tools.get_application_details(
                self.context.workspace.workspace_id,
                self.context.deployment.application_id
            )
            
            if app_details and 'variables' in app_details:
                # Extract current variables from the application
                current_env_vars = {}
                for var in app_details['variables']:
                    var_name = var.get('name', '')
                    var_value = var.get('defaultValue', '')
                    if var_name:
                        current_env_vars[var_name] = var_value
                
                if current_env_vars:
                    printer.print(f"  - Found {len(current_env_vars)} variables in the application")
                    printer.print(f"  - Variables: {list(current_env_vars.keys())}")
                    
                    # DON'T merge template variables into user context!
                    # The user context should only contain:
                    # 1. Variables they provided values for (translated versions)
                    # 2. Topic variables (input/output) 
                    
                    if not self.context.credentials.env_var_values:
                        # No user values yet - this shouldn't happen in normal flow
                        # as user provides values during prerequisites phase
                        self.context.credentials.env_var_values = {}
                        printer.print("  - Warning: No user-provided variables found")
                    
                    # We don't merge app variables into user context anymore
                    # The user context is the source of truth for what they want
                    printer.print(f"  - Keeping user-provided variables: {len(self.context.credentials.env_var_values)} total")
                    return True
                else:
                    printer.print("  - No variables found in application")
                    return False
                    
        except Exception as e:
            printer.print(f"  - Could not sync application variables: {e}")
            return False
    
    async def _select_topic_for_variable(self, var_name: str, var_type: str, current_value: str) -> Optional[str]:
        """Show topic picker for InputTopic/OutputTopic variables.
        
        Args:
            var_name: The variable name
            var_type: The variable type (InputTopic or OutputTopic)
            current_value: The current default value
            
        Returns:
            Selected topic name, 'USE_DEFAULT' to use default, or None for manual input
        """
        try:
            # Get list of topics in the workspace
            printer.print(f"\n   Fetching available topics for {var_name}...")
            topics_df = await quix_tools.find_topics(self.context.workspace.workspace_id)
            
            if topics_df.empty:
                printer.print(f"   ⚠️ No topics found in the workspace.")
                # Fall back to manual input
                return None
            
            # Use questionary for topic selection
            from workflow_tools.core.questionary_utils import select
            
            # Prepare choices for questionary
            choices = []
            
            # Add "Use default" option at the beginning if there's a default value
            if current_value:
                choices.append(f"✅ Use default: {current_value}")
            
            # Add all topics
            for topic in topics_df.to_dict('records'):
                topic_name = topic['Topic Name']
                partitions = topic.get('Partitions', 'N/A')
                retention = topic.get('Retention (hours)', 'N/A')
                
                # Show current value indicator if it matches
                if topic_name == current_value:
                    choice_text = f"📌 {topic_name} (current) - Partitions: {partitions}, Retention: {retention}h"
                else:
                    choice_text = f"📊 {topic_name} - Partitions: {partitions}, Retention: {retention}h"
                
                choices.append(choice_text)
            
            # Add manual input option at the end
            choices.append("✏️ Enter topic name manually")
            
            # Display menu
            printer.print(f"\nSelect topic for '{var_name}' ({var_type})")
            if current_value:
                printer.print(f"   Current value: {current_value}")
            
            selected = select(
                "Choose a topic:",
                choices=choices
            )
            
            # Parse the selection
            if selected.startswith("✅ Use default:"):
                return 'USE_DEFAULT'
            elif selected == "✏️ Enter topic name manually":
                return None  # Fall back to manual input
            else:
                # Extract topic name from the selection
                # Remove icon and metadata
                if selected.startswith("📌 "):
                    # Current topic
                    topic_name = selected[2:].split(" (current)")[0].strip()
                elif selected.startswith("📊 "):
                    # Regular topic
                    topic_name = selected[2:].split(" - Partitions:")[0].strip()
                else:
                    topic_name = selected
                
                return topic_name
            
        except Exception as e:
            printer.print(f"   ⚠️ Could not fetch topics: {e}")
            # Fall back to manual input
            return None
    
    def _get_type_selection(self, current_type: str, is_secret: bool = False) -> Optional[str]:
        """Display numbered menu for type selection and handle invalid inputs.
        
        Args:
            current_type: The current type of the variable
            is_secret: Whether the variable is currently a secret
            
        Returns:
            Selected type or None if user cancels
        """
        from workflow_tools.core.questionary_utils import select
        
        # Define available types based on current state with icons
        if is_secret:
            # When converting from Secret, don't offer Secret again
            type_choices = [
                "📝 FreeText",
                "⬅️ InputTopic",
                "➡️ OutputTopic",
                "🔒 HiddenText",
                f"❌ Cancel (keep as {current_type})"
            ]
            type_values = ["FreeText", "InputTopic", "OutputTopic", "HiddenText", None]
        else:
            # When converting from non-secret, offer all types
            type_choices = [
                "📝 FreeText",
                "🔑 Secret",
                "🔒 HiddenText",
                "⬅️ InputTopic",
                "➡️ OutputTopic",
                f"❌ Cancel (keep as {current_type})"
            ]
            type_values = ["FreeText", "Secret", "HiddenText", "InputTopic", "OutputTopic", None]
        
        selected_choice = select(
            "Select new type:",
            type_choices,
            default=type_choices[-1]  # Default to Cancel
        )
        
        # Map the selected choice to its value
        if selected_choice:
            idx = type_choices.index(selected_choice)
            selected = type_values[idx]
        else:
            selected = None
        
        if selected is None:
            printer.print(f"   Keeping type as: {current_type}")
        
        return selected
    
    async def collect_env_vars_from_app_yaml(self, app_dir: str, auto_debug_mode: bool = False) -> bool:
        """
        Prompt users to fill in environment variable values based on app.yaml.
        Updates app.yaml directly with user-provided values.
        
        Args:
            app_dir: Directory containing app.yaml
            auto_debug_mode: If True, automatically use existing values without prompting
            
        Returns:
            True if successful, False otherwise
        """
        app_yaml_path = os.path.join(app_dir, "app.yaml")
        
        if not os.path.exists(app_yaml_path):
            printer.print("❌ Error: app.yaml not found")
            return False
        
        try:
            # Read the current app.yaml
            with open(app_yaml_path, 'r', encoding='utf-8') as f:
                app_config = yaml.safe_load(f)
            
            if 'variables' not in app_config or not app_config['variables']:
                printer.print("ℹ️ No environment variables defined in app.yaml")
                return True
            
            # Initialize env_var_values if not present
            if not hasattr(self.context.credentials, 'env_var_values') or self.context.credentials.env_var_values is None:
                self.context.credentials.env_var_values = {}
            
            # In auto-debug mode, skip all prompts and use values from app.yaml
            if auto_debug_mode:
                printer.print("🔄 Auto-debug: Reusing environment variables from app.yaml")
                # Store all variables with their values from app.yaml in context
                for var in app_config['variables']:
                    var_name = var.get('name', '')
                    var_value = var.get('defaultValue', '')
                    if var_name:
                        # Use the value from app.yaml (which was set in the first run)
                        self.context.credentials.env_var_values[var_name] = str(var_value) if var_value else ''
                        if var_value:
                            printer.print(f"   • {var_name}: {var_value}")
                
                printer.print("✅ Environment variables loaded from app.yaml")
                return True
            
            # Show the variables that Claude Code created
            printer.print("\n" + "=" * 60)
            printer.print("Claude Code has created code that uses the following variables:")
            for var in app_config['variables']:
                var_name = var.get('name', '')
                var_type = var.get('inputType', 'FreeText')
                var_desc = var.get('description', '')
                desc_text = f" - {var_desc}" if var_desc else ""
                printer.print(f"  • {var_name} (Type: {var_type}){desc_text}")
            printer.print("\nThese variables need some default values.")
            printer.print("")
            
            # Ask if user wants to edit manually or use console
            from workflow_tools.core.questionary_utils import select
            edit_options = [
                "💻 Use console to update variables",
                "📝 Edit app.yaml manually"
            ]
            edit_choice_text = select(
                "Would you like to edit them yourself in the app.yaml or shall I help you update each variable here in the console?",
                edit_options,
                default=edit_options[0]
            )
            edit_choice = "console" if "console" in edit_choice_text.lower() else "manual"
            
            if edit_choice == 'manual':
                # User wants to edit app.yaml manually
                printer.print("\n✏️ Ok, go ahead and update the 'app.yaml' and press ENTER when you're done.")
                printer.input("")  # Wait for user to press ENTER
                
                # Reload the app.yaml to get the updated values
                with open(app_yaml_path, 'r', encoding='utf-8') as f:
                    app_config = yaml.safe_load(f)
                
                # Store all variables with their values from app.yaml in context
                for var in app_config['variables']:
                    var_name = var.get('name', '')
                    var_value = var.get('defaultValue', '')
                    if var_name:
                        self.context.credentials.env_var_values[var_name] = str(var_value) if var_value else ''
                
                printer.print("✅ Environment variables loaded from your edited app.yaml")
                # User already had chance to edit, so don't show final edit prompt
                return True
            
            # Otherwise, proceed with console questionnaire
            printer.print("\n📋 Let's configure the environment variables...")
            
            # Check if all variables already have values (indicating this might be a cached app)
            variables_with_values = [v for v in app_config['variables'] if str(v.get('defaultValue', '')).strip()]
            all_have_values = len(variables_with_values) == len(app_config['variables'])
            
            if all_have_values and len(app_config['variables']) > 0:
                
                from workflow_tools.common import clear_screen
                clear_screen()
                
                printer.print("🔍 Detected that all environment variables already have values (possibly from cache).")
                printer.print("   Current values:")
                for var in app_config['variables']:
                    var_name = var.get('name', '')
                    current_value = var.get('defaultValue', '')
                    var_type = var.get('inputType', 'FreeText')
                    printer.print(f"   • {var_name}: {current_value} (Type: {var_type})")
                
                from workflow_tools.common import get_user_approval
                use_existing = get_user_approval(
                    "🤔 Would you like to use these existing values?",
                    default='yes'
                )
                if use_existing:
                    printer.print("✅ Using existing environment variable values from cached app.")
                    # Store existing values in context - ensure they're strings
                    for var in app_config['variables']:
                        var_name = var.get('name', '')
                        var_value = var.get('defaultValue', '')
                        if var_name and var_value:
                            self.context.credentials.env_var_values[var_name] = str(var_value)
                    return True
                else:
                    from workflow_tools.common import clear_screen
                    clear_screen()
                    printer.print("📝 Proceeding to collect new environment variable values...")
            
            # Process each variable
            try:
                for i, var in enumerate(app_config['variables']):
                    var_name = var.get('name', '')
                    var_type = var.get('inputType', 'FreeText')
                    var_desc = var.get('description', '')
                    var_required = var.get('required', False)
                    current_value = var.get('defaultValue', '')
                
                    # Check if this is a secret variable (by type or name pattern)
                    is_secret = var_type in ['Secret', 'HiddenText'] or self.secret_manager.is_secret_variable(var_name)
                    
                    # Display in compact format: name (description)
                    printer.print(f"{var_name} ({var_desc if var_desc else 'No description'})")
                    printer.print(f"   Type: {var_type}")
                    
                    # Show default value if present
                    if current_value and not is_secret:
                        printer.print(f"   Default: {current_value}")
                    elif current_value and is_secret:
                        printer.print(f"   Default secret key: {current_value}")
                    
                    # Handle secret variables using SecretManager
                    if is_secret:
                        # First ask if user wants to change the type from Secret to something else
                        from workflow_tools.core.questionary_utils import select
                        change_options = [
                            "🔒 Keep as Secret",
                            "🔄 Change to different type"
                        ]
                        change_secret_choice = select(
                            "This is marked as a Secret. What would you like to do?",
                            change_options,
                            default=change_options[0]
                        )
                        change_secret_type = "keep" if "Keep" in change_secret_choice else "change"
                        
                        if change_secret_type == 'change':
                            # User wants to change the type from Secret to something else
                            new_type = self._get_type_selection(var_type, is_secret=True)
                            if new_type:  # User selected a valid type
                                var['inputType'] = new_type
                                var_type = new_type
                                is_secret = False  # No longer a secret
                                printer.print(f"   ✅ Type changed from Secret to: {new_type}")
                                
                                # Now handle it as a regular variable
                                new_value = printer.input("   Value: ").strip()
                                
                                # Use default if no value provided
                                if not new_value and current_value:
                                    new_value = current_value
                                elif not new_value and var_required:
                                    # For required fields, insist on a value
                                    while not new_value:
                                        printer.print("   ⚠️ This field is required. Please provide a value.")
                                        new_value = printer.input("   Value: ").strip()
                            # If new_type is None, user cancelled - fall through to normal secret handling
                        
                        # If user didn't change type, or type change failed, handle as secret
                        if is_secret:
                            secret_key = await self.secret_manager.handle_secret_variable(var_name, var_desc)
                            if secret_key:
                                new_value = secret_key
                                # Update type to Secret if it wasn't already
                                if var_type not in ['Secret', 'HiddenText']:
                                    var['inputType'] = 'Secret'
                                    printer.print(f"   ✅ Type updated to: Secret")
                            elif var_required:
                                # For required secrets, use default if available
                                if current_value:
                                    printer.print(f"   Using default secret key: {current_value}")
                                    new_value = current_value
                                else:
                                    printer.print(f"   ⚠️ Warning: Required secret {var_name} not configured")
                                    new_value = ""
                            else:
                                # Optional secret not configured - skip
                                new_value = ""
                    else:
                        # Non-secret variable - check if it's a topic type
                        if var_type in ['InputTopic', 'OutputTopic']:
                            # For topic variables, show the topic picker
                            selected_topic = await self._select_topic_for_variable(var_name, var_type, current_value)
                            
                            if selected_topic == 'USE_DEFAULT':
                                # User chose to use the default value
                                new_value = current_value
                                printer.print(f"   Using default: {new_value}")
                            elif selected_topic:
                                # User selected a topic from the picker
                                new_value = selected_topic
                                printer.print(f"   ✅ Selected topic: {new_value}")
                            else:
                                # Fall back to manual input (user chose manual or picker failed)
                                new_value = printer.input("   Value (Press ENTER to use the default): ").strip()
                                
                                # Use default if no value provided
                                if not new_value and current_value:
                                    new_value = current_value
                                elif not new_value and var_required:
                                    # For required fields, insist on a value
                                    while not new_value:
                                        printer.print("   ⚠️ This field is required. Please provide a value.")
                                        new_value = printer.input("   Value: ").strip()
                        else:
                            # Regular non-secret variable - ask for value
                            new_value = printer.input("   Value (Press ENTER to use the default): ").strip()
                            
                            # Use default if no value provided
                            if not new_value and current_value:
                                new_value = current_value
                                # Don't print "Using default" - just use it silently
                            elif not new_value and var_required:
                                # For required fields, insist on a value
                                while not new_value:
                                    printer.print("   ⚠️ This field is required. Please provide a value.")
                                    new_value = printer.input("   Value: ").strip()
                        
                        # Ask if user wants to change the type (only for non-secrets)
                        from workflow_tools.core.questionary_utils import select
                        type_options = [
                            "❌ No, skip",
                            "🔄 Yes, change type"
                        ]
                        change_type_choice = select(
                            "Change field type?",
                            type_options,
                            default=type_options[0]
                        )
                        change_type = "yes" if "Yes" in change_type_choice else "no"
                        if change_type == 'yes':
                            new_type = self._get_type_selection(var_type, is_secret=False)
                            if new_type:  # User selected a valid type
                                var['inputType'] = new_type
                                var_type = new_type
                                printer.print(f"   ✅ Type changed to: {new_type}")
                                # If changed to secret, handle it
                                if new_type in ['Secret', 'HiddenText'] and new_value:
                                    # User just changed type to secret - need to create secret
                                    secret_key = await self.secret_manager.handle_secret_variable(var_name, var_desc)
                                    if secret_key:
                                        new_value = secret_key
                            # If new_type is None, user cancelled - type stays the same
                    
                    # IMPORTANT: Convert all values to strings to prevent API errors
                    if new_value:
                        new_value_str = str(new_value)
                        var['defaultValue'] = new_value_str
                        # Also store in context for immediate use - ensure it's a string
                        self.context.credentials.env_var_values[var_name] = new_value_str
                    
                        printer.print("")  # Add spacing between variables
            except KeyboardInterrupt:
                printer.print("\n\n⚠️ Variable configuration cancelled by user (Ctrl+C).")
                printer.print("❌ Aborting workflow.")
                return False
            
            # Write the updated app.yaml back
            with open(app_yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(app_config, f, default_flow_style=False, sort_keys=False)
            
            printer.print("✅ Environment variables saved to app.yaml")
            
            # Give user a final chance to edit app.yaml
            printer.print("\n" + "=" * 60)
            printer.print("All variables now have default values. If you made a mistake, now's your last")
            printer.print("chance to update './working_files/current/app.yaml' before we test the code.")
            printer.print("")
            printer.input("Press ENTER to proceed: ")
            
            # Reload the app.yaml one more time in case user made changes
            with open(app_yaml_path, 'r', encoding='utf-8') as f:
                app_config = yaml.safe_load(f)
            
            # Update context with any final changes
            for var in app_config['variables']:
                var_name = var.get('name', '')
                var_value = var.get('defaultValue', '')
                if var_name:
                    self.context.credentials.env_var_values[var_name] = str(var_value) if var_value else ''
            
            return True
            
        except Exception as e:
            printer.print(f"❌ Error updating app.yaml: {str(e)}")
            return False
    
    def _read_app_yaml_env_vars(self, app_dir: str) -> Optional[Dict[str, Any]]:
        """Read environment variables from app.yaml.
        
        Args:
            app_dir: Directory containing app.yaml
            
        Returns:
            Dictionary of environment variables or None
        """
        app_yaml_path = os.path.join(app_dir, "app.yaml")
        
        if not os.path.exists(app_yaml_path):
            printer.print("⚠️ Warning: app.yaml not found")
            return None
        
        try:
            with open(app_yaml_path, 'r', encoding='utf-8') as f:
                app_config = yaml.safe_load(f)
            
            # Extract environment variables
            env_vars = {}
            if 'variables' in app_config:
                for var in app_config['variables']:
                    var_name = var.get('name')
                    if var_name:
                        env_vars[var_name] = {
                            'description': var.get('description', ''),
                            'required': var.get('required', False),
                            'default': var.get('defaultValue', ''),
                            'input_type': var.get('inputType', 'FreeText')
                        }
            
            return env_vars
            
        except Exception as e:
            printer.print(f"❌ Error reading app.yaml: {str(e)}")
            return None
    
    def prepare_session_variables(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Prepare environment variables and secrets for session update.
        IMPORTANT: Uses app.yaml as the exclusive source of truth.
        
        Returns:
            Tuple of (session_env_vars, session_secrets) dictionaries
        """
        session_env_vars = {}
        session_secrets = {}
        
        # Get the app directory from context
        app_dir = self.context.code_generation.app_extract_dir
        if not app_dir:
            printer.print("❌ Error: No app directory found")
            return session_env_vars, session_secrets
        
        # Read directly from app.yaml - it's the living state
        app_yaml_path = os.path.join(app_dir, "app.yaml")
        
        if not os.path.exists(app_yaml_path):
            printer.print("❌ Error: app.yaml not found")
            return session_env_vars, session_secrets
        
        try:
            with open(app_yaml_path, 'r', encoding='utf-8') as f:
                app_config = yaml.safe_load(f)
            
            if 'variables' not in app_config:
                printer.print("ℹ️ No environment variables defined in app.yaml")
                return session_env_vars, session_secrets
            
            printer.print(f"📋 Reading {len(app_config['variables'])} environment variables from app.yaml")
            
            # Process each variable from app.yaml - the living state
            for var in app_config['variables']:
                var_name = var.get('name', '')
                var_value = var.get('defaultValue', '')
                input_type = var.get('inputType', 'FreeText')
                
                if not var_name:
                    continue
                
                # IMPORTANT: Convert all values to strings to prevent API errors
                var_value_str = str(var_value) if var_value else ''
                
                # Handle based on inputType from app.yaml
                if input_type in ['Secret', 'HiddenText']:
                    # These are secrets
                    if var_value_str:  # Only add if there's a value
                        session_secrets[var_name] = var_value_str
                        printer.print(f"    - Secret variable '{var_name}' (type: {input_type}) prepared")
                else:
                    # Regular environment variables
                    if var_value_str:  # Only add if there's a value
                        session_env_vars[var_name] = var_value_str
                        printer.print(f"    - Regular variable '{var_name}' (type: {input_type}) prepared")
            
            return session_env_vars, session_secrets
            
        except Exception as e:
            printer.print(f"❌ Error reading app.yaml: {str(e)}")
            return session_env_vars, session_secrets
    
    async def sync_and_update_session_environment(self, 
                                                   session_id: str, 
                                                   code: str = None,
                                                   force_re_collect: bool = False) -> bool:
        """
        Centralized method to sync variables from app.yaml and update session environment.
        This ensures consistent handling of regular variables vs secrets.
        
        Args:
            session_id: The IDE session ID to update
            code: Optional code to detect additional variables from
            force_re_collect: Force re-collection of variable values from user
            
        Returns:
            True if successful, False otherwise
        """
        try:
            printer.print("🔄 Syncing environment variables with session...")
            
            # Step 1: Detect variables from code if provided
            detected_env_vars = []
            if code:
                detected_env_vars = self.detect_environment_variables(code)
                if detected_env_vars:
                    printer.print(f"  📋 Variables detected in code: {detected_env_vars}")
            
            # Step 2: Sync variables to app.yaml if needed
            if detected_env_vars:
                await self.sync_or_update_app_variables(
                    detected_code_vars=detected_env_vars,
                    force_update=False  # Preserve existing variables
                )
            
            # Step 3: Re-collect values from user if needed
            if force_re_collect:
                printer.print("\n📋 Re-collecting environment variable values...")
                await self.collect_env_vars_from_app_yaml(self.context.code_generation.app_extract_dir)
                
                # Save updated values to cache
                from workflow_tools.phases.shared.cache_utils import CacheUtils
                cache_utils = CacheUtils(self.context, self.debug_mode)
                if self.context.code_generation.app_extract_dir:
                    cache_utils.save_app_directory_to_cache(self.context.code_generation.app_extract_dir)
                    printer.print("✅ Saved updated environment variables to cache")
            
            # Step 4: Prepare session variables from app.yaml (source of truth)
            session_env_vars, session_secrets = self.prepare_session_variables()
            
            if not session_env_vars and not session_secrets:
                printer.print("  ℹ️ No environment variables to update")
                return True
            
            # Step 5: Update session environment
            printer.print(f"  📤 Updating session with {len(session_env_vars)} variables and {len(session_secrets)} secrets")
            
            from workflow_tools.integrations import quix_tools
            update_result = await quix_tools.update_session_environment(
                self.context.workspace.workspace_id,
                session_id,
                environment_variables=session_env_vars if session_env_vars else None,
                secrets=session_secrets if session_secrets else None
            )
            
            if update_result:
                printer.print("  ✅ Session environment updated successfully")
                return True
            else:
                printer.print("  ❌ Failed to update session environment")
                return False
                
        except Exception as e:
            printer.print(f"❌ Error syncing session environment: {str(e)}")
            return False
    
    def detect_environment_variables(self, code: str) -> List[str]:
        """Detect environment variables from os.environ.get(), os.environ[], and os.getenv() calls in code.
        
        Args:
            code: Python source code to analyze
            
        Returns:
            List of unique environment variable names found in the code
        """
        # Patterns to match different ways of accessing environment variables
        patterns = [
            r'os\.environ\.get\(["\']([^"\']+)["\']',           # os.environ.get("VAR_NAME")
            r'os\.environ\[["\']([^"\']+)["\']\]',              # os.environ["VAR_NAME"]
            r'os\.getenv\(["\']([^"\']+)["\']',                 # os.getenv("VAR_NAME")
        ]
        
        detected_vars = []
        for pattern in patterns:
            matches = re.findall(pattern, code)
            detected_vars.extend(matches)
        
        # Remove duplicates and return
        return list(set(detected_vars))
    
    
    async def _collect_env_var_values_from_user(self, env_content: str, missing_var_suggestions: List[Dict[str, str]] = None) -> Dict[str, str]:
        """Collect environment variable values from user with human-in-the-loop feedback."""
        if not env_content:
            return {}
        
        # First, extract all variables and get smart defaults in one batch
        variables = []
        lines = env_content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check if this is a variable line
            if line and '=' in line and not line.startswith('#'):
                var_name, default_value = line.split('=', 1)
                var_name = var_name.strip()
                default_value = default_value.strip()
                
                # Check if previous lines indicate this is a secret or required
                is_secret = False
                is_required = True  # Default to required
                has_meaningful_default = True  # Default to having a meaningful default
                
                # Look backwards only at immediately preceding comment lines (not across variables)
                j = i - 1
                while j >= 0 and lines[j].strip().startswith('#'):
                    comment_line = lines[j].strip()
                    if comment_line.startswith('# QUIX_SECRET:'):
                        is_secret = True
                    elif comment_line.startswith('# Required:'):
                        # Extract the boolean value after "Required:"
                        required_value = comment_line.split('# Required:')[1].strip().lower()
                        is_required = required_value in ['true', '1', 'yes']
                    elif comment_line.startswith('# DefaultValue:'):
                        # Check if defaultValue is false (can be omitted)
                        default_val = comment_line.split('# DefaultValue:')[1].strip().lower()
                        has_meaningful_default = default_val not in ['false', '']
                    j -= 1
                
                variables.append((var_name, default_value, is_secret, is_required, has_meaningful_default))
            
            i += 1
        
        if not variables:
            return {}
        
        printer.print("\n--- Environment Variable Collection ---")
        printer.print("Please provide values for the following environment variables:")
        printer.print("NOTE: For secret variables, enter the NAME of your Quix secret (not the actual password/key)")
        printer.print("(Leave empty to use default values)\n")
        
        env_values = {}
        
        # Now collect user input for each variable (using AI-generated defaults)
        for var_name, default_value, is_secret_var, is_required, has_meaningful_default in variables:
            
            # Show variable info
            printer.print(f"\n📝 Variable: {var_name}")
            if not is_required:
                printer.print(f"   ⚪ OPTIONAL")
            if default_value:
                printer.print(f"   Default: {default_value}")
            
            # Handle secret variables using SecretManager
            if is_secret_var:
                # Get description from previous comment lines if available
                description = ""
                j = i - 1
                while j >= 0 and lines[j].strip().startswith('#') and not lines[j].strip().startswith('# QUIX_SECRET:'):
                    comment_line = lines[j].strip()
                    if not comment_line.startswith('# Required:') and not comment_line.startswith('# DefaultValue:'):
                        description = comment_line.lstrip('# ')
                        break
                    j -= 1
                
                secret_key = await self.secret_manager.handle_secret_variable(var_name, description)
                if secret_key:
                    env_values[var_name] = secret_key
                elif is_required:
                    # For required secrets, use default if available
                    if default_value:
                        printer.print(f"   Using default secret key: {default_value}")
                        env_values[var_name] = default_value
                    else:
                        printer.print(f"   ⚠️ Warning: Required secret {var_name} not configured")
                        env_values[var_name] = ""
                # For optional secrets, skip if no key provided
                continue
            
            # Get user input with appropriate prompt for non-secret variables
            if is_required:
                # Required variables - always use default or get input
                prompt = f"   Enter value for {var_name} (or press Enter for default): "
                
                user_input = printer.input(prompt).strip()
                
                if user_input:
                    env_values[var_name] = user_input
                elif default_value:
                    env_values[var_name] = default_value
                else:
                    env_values[var_name] = ""
            else:
                # Optional variables - behavior depends on whether they have meaningful defaults
                if has_meaningful_default and default_value:
                    # Optional with meaningful default - can use default or skip
                    prompt = f"   Enter value for {var_name} (Enter=use default, 's'=skip): "
                    
                    user_input = printer.input(prompt).strip()
                    
                    if user_input == 's':
                        # User chose to skip this optional variable
                        continue
                    elif user_input:
                        # User provided a value
                        env_values[var_name] = user_input
                    else:
                        # User pressed Enter - use default for optional variable
                        env_values[var_name] = default_value
                        
                else:
                    # Optional without meaningful default (defaultValue: false) - can be omitted with Enter
                    prompt = f"   Enter value for {var_name} (or press Enter to skip): "
                    
                    user_input = printer.input(prompt).strip()
                    
                    if user_input:
                        # User provided a value
                        env_values[var_name] = user_input
                    # If no input, skip entirely (don't add to env_values)
        
        printer.print(f"\n✅ Collected {len(env_values)} environment variables")
        
        # Ask if user wants to add extra variables with preview of suggestions
        if missing_var_suggestions:
            suggested_names = [var.get('name', 'UNKNOWN') for var in missing_var_suggestions]
            suggestion_preview = f"\nSuggested vars: {', '.join(suggested_names)}\n"
        else:
            suggestion_preview = f"\nSuggested vars: None\n"
        
        prompt_text = f"\nWould you like to add any additional environment variables? (y/N):{suggestion_preview} "
        if printer.input(prompt_text).strip().lower() == 'y':
            extra_vars = self._collect_additional_env_vars(missing_var_suggestions or [])
            env_values.update(extra_vars)
            printer.print(f"✅ Added {len(extra_vars)} additional variables")
        
        return env_values
    
    def _collect_additional_env_vars(self, missing_var_suggestions: List[Dict[str, str]]) -> Dict[str, str]:
        """Collect additional environment variables from user with intelligent suggestions."""
        extra_vars = {}
        
        printer.print("\n--- Additional Environment Variables ---")
        
        # Show intelligent suggestions first if available
        if missing_var_suggestions:
            # Get appropriate technology name
            from workflow_tools.workflow_types import WorkflowType
            if self.context.selected_workflow == WorkflowType.SOURCE:
                tech_name = getattr(self.context.technology, 'source_technology', None) or self.context.technology.destination_technology
            else:
                tech_name = self.context.technology.destination_technology
            printer.print(f"💡 We've identified {len(missing_var_suggestions)} potentially useful variables for {tech_name}:")
            printer.print()
            
            for i, suggestion in enumerate(missing_var_suggestions, 1):
                name = suggestion.get('name', 'UNKNOWN')
                description = suggestion.get('description', 'No description')
                default = suggestion.get('default', '')
                required = suggestion.get('required', False)
                
                req_text = " (RECOMMENDED)" if required else " (optional)"
                printer.print(f"{i}. {name}{req_text}")
                printer.print(f"   {description}")
                if default:
                    printer.print(f"   Default: {default}")
                printer.print()
            
            # Ask user to select from suggestions
            while True:
                choice = printer.input("Select a variable by number, or press Enter to continue: ").strip()
                if not choice:
                    break
                
                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(missing_var_suggestions):
                        suggestion = missing_var_suggestions[choice_idx]
                        var_name = suggestion.get('name')
                        suggested_default = suggestion.get('default', '')
                        
                        # Ask for value with suggested default
                        if suggested_default:
                            var_value = printer.input(f"Value for {var_name} (default: {suggested_default}): ").strip()
                            if not var_value:  # Use default if empty
                                var_value = suggested_default
                        else:
                            var_value = printer.input(f"Value for {var_name}: ").strip()
                        
                        extra_vars[var_name] = var_value
                        printer.print(f"✅ Added {var_name} = {var_value}")
                        
                        # Remove from suggestions to avoid duplication
                        missing_var_suggestions.pop(choice_idx)
                        
                        # Show remaining suggestions
                        if missing_var_suggestions:
                            printer.print(f"\nRemaining suggestions:")
                            for i, remain_suggestion in enumerate(missing_var_suggestions, 1):
                                name = remain_suggestion.get('name', 'UNKNOWN')
                                req_text = " (RECOMMENDED)" if remain_suggestion.get('required', False) else " (optional)"
                                printer.print(f"{i}. {name}{req_text}")
                        else:
                            printer.print("\n✅ All suggestions applied!")
                            break
                    else:
                        printer.print(f"❌ Invalid choice. Please enter 1-{len(missing_var_suggestions)} or press Enter to continue.")
                except ValueError:
                    printer.print(f"❌ Invalid input. Please enter a number 1-{len(missing_var_suggestions)} or press Enter to continue.")
        
        # Manual entry section
        printer.print("\nEnter any additional custom variables (press Enter with empty name to stop):")
        
        while True:
            var_name = printer.input("Variable name (or press Enter to stop): ").strip()
            if not var_name:
                break
            
            var_value = printer.input(f"Value for {var_name}: ").strip()
            extra_vars[var_name] = var_value
            printer.print(f"✅ Added {var_name}")
        
        return extra_vars
    
    async def collect_env_values_with_cache(self, env_content: str, missing_var_suggestions: List[Dict[str, str]] = None) -> Dict[str, str]:
        """Collect environment variable values from user with caching support."""
        # Check for cached environment variables first
        cached_env_vars = self.cache_utils.check_cached_env_vars()
        if cached_env_vars:
            if self.cache_utils.use_cached_env_vars(cached_env_vars):
                printer.print("✅ Using cached environment variables.")
                return cached_env_vars
            else:
                printer.print("📥 Proceeding with fresh environment variable collection.")
        
        # No cache found or user rejected cache, collect fresh values
        env_values = await self._collect_env_var_values_from_user(env_content, missing_var_suggestions)
        
        # Save to cache for future runs
        self.cache_utils.save_env_vars_to_cache(env_values, env_content)
        
        return env_values