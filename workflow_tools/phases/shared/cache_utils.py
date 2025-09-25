# cache_utils.py - Caching utilities for template selection, environment variables, and generated code

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from workflow_tools.contexts import WorkflowContext
from workflow_tools.common import printer, get_user_approval, get_user_approval_with_back, sanitize_name
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.core.working_directory import WorkingDirectory, WorkflowType as WDWorkflowType


class CacheUtils:
    """Handles caching for template selections and environment variables."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        self.context = context
        self.debug_mode = debug_mode
        # Ensure directory structure exists
        WorkingDirectory.ensure_structure()
    
    def _get_workflow_type(self) -> WDWorkflowType:
        """Get the workflow type as string for WorkingDirectory."""
        from workflow_tools.workflow_types import WorkflowType
        if self.context.selected_workflow == WorkflowType.SOURCE:
            return "source"
        else:
            return "sink"
    
    def _get_cached_template_filename(self) -> str:
        """Get the filename for cached template selection."""
        # Use a generic filename since technology might not be set yet
        workflow = self._get_workflow_type()
        # Use a generic name for the template cache
        return WorkingDirectory.get_cached_template_path(workflow, "template_cache")
    
    def check_cached_template_selection(self) -> Optional[Dict[str, str]]:
        """Check if there's a cached template selection for this technology."""
        cache_file = self._get_cached_template_filename()
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            printer.print(f"\n📋 Found cached technology and template selection")
            with open(cache_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the markdown content to extract technology and template details
            template_info = {}
            for line in content.split('\n'):
                if line.startswith('**Source Technology:**'):
                    template_info['source_technology'] = line.split('**Source Technology:**')[1].strip()
                elif line.startswith('**Destination Technology:**'):
                    template_info['destination_technology'] = line.split('**Destination Technology:**')[1].strip()
                elif line.startswith('**Selected Template:**'):
                    template_info['name'] = line.split('**Selected Template:**')[1].strip()
                elif line.startswith('**Template ID:**'):
                    template_info['itemId'] = line.split('**Template ID:**')[1].strip()
                elif line.startswith('**Description:**'):
                    template_info['shortDescription'] = line.split('**Description:**')[1].strip()
                elif line.startswith('**Tags:**'):
                    tags_str = line.split('**Tags:**')[1].strip()
                    template_info['tags'] = [tag.strip() for tag in tags_str.split(',')]
                elif line.startswith('**AI Reasoning:**'):
                    template_info['reasoning'] = line.split('**AI Reasoning:**')[1].strip()
                elif line.startswith('**Tech Prep Advice File:**'):
                    template_info['tech_prep_file'] = line.split('**Tech Prep Advice File:**')[1].strip()
            
            if template_info.get('itemId'):
                return template_info
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not read cached template selection: {e}")
        
        return None
    
    def use_cached_template_selection(self, cached_selection: Dict[str, str]) -> bool:
        """Show cached template selection to user and ask for confirmation."""
        # Show the cached content like schema phase does
        cache_file = self._get_cached_template_filename()
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached_content = f.read()
        
        # Parse the cached content to extract key-value pairs
        content_dict = {}
        for line in cached_content.split('\n'):
            if line.strip() and ':' in line and not line.startswith('#'):
                if '**' in line:
                    # Parse markdown-style bold entries
                    key = line.split('**')[1] if '**' in line else line.split(':')[0]
                    value = line.split(':')[-1].strip() if ':' in line else ''
                    content_dict[key] = value
        
        # Show tech prep file if it exists
        tech_prep_file = cached_selection.get('tech_prep_file')
        if tech_prep_file and os.path.exists(tech_prep_file):
            content_dict["Tech Prep Advice"] = tech_prep_file
        
        # Display the beautiful cache panel
        printer.print_cache_panel(
            title="Cached Technology and Template Selection",
            cache_file=cache_file,
            content_dict=content_dict,
            border_style="green"
        )
        
        response = get_user_approval_with_back("Would you like to use this cached template selection instead of re-selecting?", allow_back=True)
        if response == 'back':
            raise NavigationBackRequest("User requested to go back")
        return response == 'yes'
    
    def save_template_selection_to_cache(self, selected_item: Dict[str, Any], reasoning: str):
        """Save template selection to markdown file for future runs."""
        cache_file = self._get_cached_template_filename()
        
        try:
            os.makedirs("working_files", exist_ok=True)
            
            # Determine app name based on workflow type
            from workflow_tools.workflow_types import WorkflowType
            if hasattr(self.context.deployment, 'application_name'):
                app_name = self.context.deployment.application_name
            else:
                app_name = 'app'
            
            if self.context.selected_workflow == WorkflowType.SOURCE:
                tech_label = "Source Application"
            else:
                tech_label = "Destination Application"
            
            # Include tech prep advice filename if it exists
            tech_prep_file = getattr(self.context.technology, 'technology_preparation_advice_file', None)
            
            content = f"""**{tech_label}:** {app_name}

# Template Selection for {app_name}

**Selected Template:** {selected_item.get('name', 'Unknown')}
**Template ID:** {selected_item.get('itemId', 'Unknown')}
**Description:** {selected_item.get('shortDescription', 'No description')}
**Tags:** {', '.join(selected_item.get('tags', []))}

**AI Reasoning:** {reasoning}
"""
            
            # Add tech prep file reference if it exists
            if tech_prep_file:
                content += f"\n**Tech Prep Advice File:** {tech_prep_file}\n"
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            printer.print(f"✅ Template selection approved and saved to '{cache_file}'.")
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not save template selection cache: {e}")
    
    def _get_cached_env_vars_filename(self) -> str:
        """Get the filename for cached environment variables."""
        from workflow_tools.workflow_types import WorkflowType
        
        # Determine app name
        if hasattr(self.context.deployment, 'application_name'):
            app_name = self.context.deployment.application_name
        else:
            app_name = 'app'
        
        workflow = self._get_workflow_type()
        return WorkingDirectory.get_cached_env_vars_path(workflow, app_name)
    
    def check_cached_env_vars(self) -> Optional[Dict[str, str]]:
        """Check if there are cached environment variables for this technology."""
        cache_file = self._get_cached_env_vars_filename()
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            # Get the appropriate app name
            if hasattr(self.context.deployment, 'application_name'):
                app_name = self.context.deployment.application_name
            else:
                app_name = 'app'
            
            printer.print(f"\n📋 Found existing environment variables for application '{app_name}'")
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Return just the values dict (or None if empty)
            env_values = cached_data.get('env_values', {})
            return env_values if env_values else None
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not read cached environment variables: {e}")
        
        return None
    
    def use_cached_env_vars(self, cached_env_vars: Dict[str, str]) -> bool:
        """Show cached environment variables to user and ask for confirmation."""
        cache_file = self._get_cached_env_vars_filename()
        
        # Prepare content dict with masked secrets
        content_dict = {}
        if cached_env_vars:
            for var_name, var_value in cached_env_vars.items():
                if any(secret_term in var_name.lower() for secret_term in ['password', 'secret', 'token', 'key']):
                    content_dict[var_name] = f"{var_value} 🔐"
                else:
                    content_dict[var_name] = var_value
        else:
            content_dict["Status"] = "No cached variables found"
        
        # Display the beautiful cache panel
        printer.print_cache_panel(
            title="Cached Environment Variables",
            cache_file=cache_file,
            content_dict=content_dict,
            border_style="yellow"
        )
        
        response = get_user_approval_with_back("Would you like to use these cached environment variables instead of re-entering them?", allow_back=True)
        if response == 'back':
            raise NavigationBackRequest("User requested to go back")
        return response == 'yes'
    
    def save_env_vars_to_cache(self, env_values: Dict[str, str], translated_env_content: str):
        """Save environment variables to cache file for future runs."""
        cache_file = self._get_cached_env_vars_filename()
        
        try:
            os.makedirs("working_files", exist_ok=True)
            
            # Create comprehensive cache data
            if hasattr(self.context.deployment, 'application_name'):
                app_name = self.context.deployment.application_name
            else:
                app_name = 'app'
            cache_data = {
                'application': app_name,
                'timestamp': datetime.now().isoformat(),
                'env_values': env_values,
                'translated_env_template': translated_env_content,
                'variable_count': len(env_values)
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            
            printer.print(f"✅ Environment variables cached to: {cache_file}")
            
            # Also create a .env file for user convenience
            self._generate_env_file_from_cache(env_values, app_name)
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not save environment variables cache: {e}")
    
    def _generate_env_file_from_cache(self, env_values: Dict[str, str], app_name: str):
        """Generate a .env file from cached environment variables."""
        env_file_path = f"working_files/.env_{sanitize_name(app_name)}"
        
        try:
            content = f"# Environment variables for {app_name}\n"
            content += f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for var_name, var_value in env_values.items():
                if any(secret_term in var_name.lower() for secret_term in ['password', 'secret', 'token', 'key']):
                    content += f"# SECRET KEY: This references a Quix secret\n"
                    content += f"{var_name}={var_value}\n"
                else:
                    content += f"{var_name}={var_value}\n"
                content += "\n"
            
            with open(env_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            printer.print(f"📄 Generated .env file: {env_file_path}")
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not generate .env file: {e}")
    
    def load_documentation(self, workflow_type: str = "sink"):
        """Load local documentation files based on workflow type.
        
        Args:
            workflow_type: Either "sink" or "source"
        """
        # Select documentation files based on workflow type
        if workflow_type == "source":
            local_doc_files = [
                "./resources/source/README.md",
                "./resources/source/custom-sources.md",
                "./resources/common/serialization.md",
                "./resources/common/stateful-processing.md"
            ]
        else:  # sink
            local_doc_files = [
                "./resources/sink/README-sink.md",
                "./resources/sink/custom-sinks.md",
                "./resources/sink/sinks.md",
                "./resources/common/serialization.md"
            ]
        
        printer.print(f"\n📚 Loading {workflow_type} documentation...")
        
        doc_contents = []
        for doc_file in local_doc_files:
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    doc_contents.append(f"# From {doc_file}\n\n{content}")
                    printer.print(f"✅ Loaded documentation from {doc_file}")
            except FileNotFoundError:
                printer.print(f"⚠️ Warning: Could not find {doc_file}")
            except Exception as e:
                printer.print(f"⚠️ Warning: Error reading {doc_file}: {e}")
        
        self.context.code_generation.docs_content = "\n\n---\n\n".join(doc_contents)
    
    # Code caching methods for generated code
    def _get_cached_code_filename(self, code_type: str) -> str:
        """Get the filename for cached generated code.
        
        Args:
            code_type: Type of code being cached ('connection_test' or 'sandbox')
        """
        from workflow_tools.workflow_types import WorkflowType
        
        # Determine app name
        if hasattr(self.context.deployment, 'application_name'):
            app_name = self.context.deployment.application_name
        else:
            app_name = 'app'
        
        workflow = self._get_workflow_type()
        
        # Special handling for connection test
        if code_type == "connection_test" and workflow == "source":
            return WorkingDirectory.get_cached_connection_test_path(app_name)
        else:
            return WorkingDirectory.get_cached_code_path(workflow, code_type, app_name)
    
    def check_cached_code(self, code_type: str) -> Optional[str]:
        """Check if there's cached generated code for this technology and code type.
        
        Args:
            code_type: Type of code to check ('connection_test' or 'sandbox')
            
        Returns:
            Cached code content or None if not found
        """
        cache_file = self._get_cached_code_filename(code_type)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            # Get app name for display
            if hasattr(self.context.deployment, 'application_name'):
                app_name = self.context.deployment.application_name
            else:
                app_name = 'app'
            
            printer.print(f"\n📋 Found cached {code_type.replace('_', ' ')} code for application '{app_name}'")
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_code = f.read()
            
            return cached_code
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not read cached {code_type} code: {e}")
        
        return None
    
    def use_cached_code(self, cached_code: str, code_type: str) -> bool:
        """Show cached code to user and ask for confirmation.
        
        Args:
            cached_code: The cached code content
            code_type: Type of code being used ('connection_test' or 'sandbox')
            
        Returns:
            True if user wants to use cached code, False otherwise
        """
        cache_file = self._get_cached_code_filename(code_type)
        
        # Prepare content dict
        content_dict = {}
        
        # Get file modification time for context
        try:
            mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            content_dict["Last Modified"] = mod_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
        
        # Add code stats
        code_lines = cached_code.split('\n')
        content_dict["Total Lines"] = str(len(code_lines))
        content_dict["File Size"] = f"{len(cached_code)} characters"
        
        # Display the beautiful cache panel
        printer.print_cache_panel(
            title=f"Cached {code_type.replace('_', ' ').title()} Code",
            cache_file=cache_file,
            content_dict=content_dict,
            border_style="magenta"
        )
        
        # Show first 30 lines of cached code as preview
        code_lines = cached_code.split('\n')
        preview_lines = min(30, len(code_lines))
        preview_code = '\n'.join(code_lines[:preview_lines])
        if len(code_lines) > preview_lines:
            preview_code += f"\n\n# ... ({len(code_lines) - preview_lines} more lines)"
        
        printer.print_code(
            preview_code,
            language="python",
            title=f"Code Preview (first {preview_lines} lines)",
            line_numbers=True
        )
        printer.print_divider()
        
        question = f"Would you like to use this cached {code_type.replace('_', ' ')} code instead of generating new code via AI?"
        response = get_user_approval_with_back(question, allow_back=True)
        if response == 'back':
            raise NavigationBackRequest("User requested to go back")
        if response == 'yes':
            printer.print(f"✅ Using cached {code_type.replace('_', ' ')} code")
            return True
        else:
            printer.print(f"🔄 Will generate fresh {code_type.replace('_', ' ')} code")
            return False
    
    def save_code_to_cache(self, code: str, code_type: str):
        """Save generated code to cache file for future runs.
        
        Args:
            code: The generated code to cache
            code_type: Type of code being cached ('connection_test' or 'sandbox')
        """
        cache_file = self._get_cached_code_filename(code_type)
        
        try:
            os.makedirs("working_files", exist_ok=True)
            
            # Add header comment with metadata
            from workflow_tools.workflow_types import WorkflowType
            if self.context.selected_workflow == WorkflowType.SOURCE:
                tech_name = getattr(self.context.technology, 'source_technology', None) or self.context.technology.destination_technology
            else:
                tech_name = self.context.technology.destination_technology
            
            # Get app name
            app_name = getattr(self.context.deployment, 'application_name', 'app')
            
            header = f"""# Cached {code_type.replace('_', ' ')} code for {app_name}
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Template: {getattr(self.context.technology, 'selected_item_name', 'Unknown')}
# This is cached code - delete this file to force regeneration

"""
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(header + code)
            
            printer.print(f"✅ {code_type.replace('_', ' ').title()} code cached to: {cache_file}")
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not save {code_type} code to cache: {e}")
    
    # Claude Code SDK specific caching methods
    def _get_cached_claude_code_filename(self) -> str:
        """Get the filename for cached Claude Code SDK generated code."""
        from workflow_tools.workflow_types import WorkflowType
        
        # Determine app name based on workflow type
        if hasattr(self.context.deployment, 'application_name'):
            app_name = self.context.deployment.application_name
        else:
            app_name = 'app'
        
        if self.context.selected_workflow == WorkflowType.SOURCE:
            prefix = "source"
        else:
            prefix = "sink"
        
        sanitized_app_name = sanitize_name(app_name)
        return f"working_files/{prefix}_claude_code_{sanitized_app_name}.py"
    
    def check_cached_claude_code(self) -> Optional[str]:
        """Check if there's cached Claude Code SDK generated code for this technology."""
        cache_file = self._get_cached_claude_code_filename()
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            # Get app name for display
            if hasattr(self.context.deployment, 'application_name'):
                app_name = self.context.deployment.application_name
            else:
                app_name = 'app'
            
            printer.print(f"\n📋 Found cached Claude Code SDK generated code for application '{app_name}'")
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_code = f.read()
            
            return cached_code
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not read cached Claude Code SDK code: {e}")
        
        return None
    
    def use_cached_claude_code(self, cached_code: str) -> bool:
        """Show cached Claude Code SDK code to user and ask for confirmation."""
        cache_file = self._get_cached_claude_code_filename()
        
        # Prepare content dict
        content_dict = {}
        
        # Get file modification time for context
        try:
            mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            content_dict["Last Modified"] = mod_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
        
        # Add code stats
        code_lines = cached_code.split('\n')
        content_dict["Total Lines"] = str(len(code_lines))
        content_dict["Generated By"] = "Claude Code SDK"
        
        # Display the beautiful cache panel
        printer.print_cache_panel(
            title="Cached Claude Code SDK Generated Code",
            cache_file=cache_file,
            content_dict=content_dict,
            border_style="blue"
        )
        
        # Show first 30 lines of cached code as preview
        code_lines = cached_code.split('\n')
        preview_lines = min(30, len(code_lines))
        preview_code = '\n'.join(code_lines[:preview_lines])
        if len(code_lines) > preview_lines:
            preview_code += f"\n\n# ... ({len(code_lines) - preview_lines} more lines)"
        
        printer.print_code(
            preview_code,
            language="python",
            title=f"Code Preview (first {preview_lines} lines)",
            line_numbers=True
        )
        printer.print_divider()
        
        question = "Would you like to use this cached Claude Code SDK generated code instead of generating new code?"
        response = get_user_approval_with_back(question, allow_back=True)
        if response == 'back':
            raise NavigationBackRequest("User requested to go back")
        if response == 'yes':
            printer.print("✅ Using cached Claude Code SDK generated code")
            return True
        else:
            printer.print("🔄 Will generate fresh code via Claude Code SDK")
            return False
    
    def save_claude_code_to_cache(self, code: str):
        """Save Claude Code SDK generated code to cache file for future runs."""
        cache_file = self._get_cached_claude_code_filename()
        
        try:
            os.makedirs("working_files", exist_ok=True)
            
            # Add header comment with metadata
            from workflow_tools.workflow_types import WorkflowType
            if self.context.selected_workflow == WorkflowType.SOURCE:
                tech_name = getattr(self.context.technology, 'source_technology', None) or self.context.technology.destination_technology
            else:
                tech_name = self.context.technology.destination_technology
            
            # Get app name
            app_name = getattr(self.context.deployment, 'application_name', 'app')
            
            header = f"""# Cached Claude Code SDK generated code for {app_name}
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Template: {getattr(self.context.technology, 'selected_item_name', 'Unknown')}
# This is cached code - delete this file to force regeneration

"""
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(header + code)
            
            printer.print(f"✅ Claude Code SDK generated code cached to: {cache_file}")
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not save Claude Code SDK code to cache: {e}")
    
    # User input caching methods
    def _get_cached_user_prompt_filename(self) -> str:
        """Get the filename for cached user prompt (app requirements)."""
        from workflow_tools.workflow_types import WorkflowType

        # Determine workflow type
        if self.context.selected_workflow == WorkflowType.SOURCE:
            workflow_type = "source"
        else:
            workflow_type = "sink"

        # Requirements are now cached separately from app name
        # Use a fixed filename for requirements cache
        requirements_cache_name = "user_requirements"

        # Use the prompts directory for user prompts
        return WorkingDirectory.get_cached_prompt_path(workflow_type, requirements_cache_name)
    
    def check_cached_user_prompt(self) -> Optional[str]:
        """Check if there's a cached user prompt (app requirements) for this technology."""
        cache_file = self._get_cached_user_prompt_filename()

        if not os.path.exists(cache_file):
            return None

        try:
            printer.print(f"\n📋 Found cached user requirements")
            with open(cache_file, 'r', encoding='utf-8') as f:
                full_content = f.read()

            # Extract only the actual requirements (skip header comments)
            lines = full_content.split('\n')
            actual_requirements = []
            in_header = True

            for line in lines:
                if in_header:
                    # Skip comment lines and empty lines at the beginning
                    if line.strip() and not line.strip().startswith('#'):
                        in_header = False
                        actual_requirements.append(line)
                else:
                    actual_requirements.append(line)

            # Join and clean up
            requirements = '\n'.join(actual_requirements).strip()
            return requirements if requirements else None
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not read cached user prompt: {e}")
        
        return None
    
    def use_cached_user_prompt(self, cached_prompt: str, is_for_additional_requirements: bool = False) -> bool:
        """Show cached user prompt to user and ask for confirmation.

        Args:
            cached_prompt: The cached requirements to show
            is_for_additional_requirements: If True, this is being called in the context where
                                           the user can add additional requirements to base requirements
        """
        cache_file = self._get_cached_user_prompt_filename()

        # Prepare content dict
        content_dict = {}

        # Get file modification time for context
        try:
            mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            content_dict["Last Modified"] = mod_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass

        # Add requirements info - show full requirements in the box if short enough
        if len(cached_prompt) <= 200:
            content_dict["Requirements"] = cached_prompt
        else:
            # For longer requirements, show preview in box and full text below
            content_dict["Requirements Preview"] = cached_prompt[:150] + "..."
            content_dict["Full Length"] = f"{len(cached_prompt)} characters"

        # Display the beautiful cache panel with appropriate title
        if is_for_additional_requirements:
            panel_title = "Cached Base Requirements"
        else:
            panel_title = "Cached User Requirements"

        printer.print_cache_panel(
            title=panel_title,
            cache_file=cache_file,
            content_dict=content_dict,
            border_style="cyan"
        )

        # If requirements are long, show full text separately
        if len(cached_prompt) > 200:
            printer.print("\n📝 Full requirements:")
            printer.print(f'"{cached_prompt}"')

        # Choose appropriate question based on context
        if is_for_additional_requirements:
            question = "Would you like to reuse these base requirements?\n(You can add additional requirements in the next step)"
        else:
            question = "Would you like to use these cached app requirements instead of entering new ones?"

        response = get_user_approval_with_back(question, allow_back=True)
        if response == 'back':
            raise NavigationBackRequest("User requested to go back")
        if response == 'yes':
            printer.print("✅ Using cached app requirements")
            return True
        else:
            printer.print("🔄 Will enter fresh app requirements")
            return False
    
    def save_user_prompt_to_cache(self, user_prompt: str):
        """Save user prompt (app requirements) to cache file for future runs."""
        cache_file = self._get_cached_user_prompt_filename()
        
        try:
            # Ensure the cache directory exists
            cache_dir = os.path.dirname(cache_file)
            os.makedirs(cache_dir, exist_ok=True)
            
            # Add header comment with metadata
            from workflow_tools.workflow_types import WorkflowType
            if self.context.selected_workflow == WorkflowType.SOURCE:
                tech_name = getattr(self.context.technology, 'source_technology', None) or self.context.technology.destination_technology
            else:
                tech_name = self.context.technology.destination_technology
            
            # Note: Requirements are now cached independently of app name
            workflow = self._get_workflow_type()

            header = f"""# Cached user requirements for {workflow} workflow
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# This is cached requirements - delete this file to force re-entry

"""
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(header + user_prompt)
            
            printer.print(f"✅ App requirements cached to: {cache_file}")
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not save user prompt to cache: {e}")
    
    # App name caching methods
    def _get_cached_additional_requirements_filename(self) -> str:
        """Get the filename for cached additional requirements (source workflow only)."""
        # This is only for source workflows
        workflow_type = "source"

        # Additional requirements are cached independently of app name
        # Use a fixed filename for additional requirements cache
        additional_cache_name = "additional_requirements"

        # Use the prompts directory
        return WorkingDirectory.get_cached_prompt_path(workflow_type, additional_cache_name)

    def check_cached_additional_requirements(self) -> Optional[str]:
        """Check if there's cached additional requirements for source workflow."""
        cache_file = self._get_cached_additional_requirements_filename()

        if not os.path.exists(cache_file):
            return None

        try:
            printer.print(f"\n📋 Found cached additional requirements")
            with open(cache_file, 'r', encoding='utf-8') as f:
                full_content = f.read()

            # Extract actual requirements (skip header comments)
            lines = full_content.split('\n')
            actual_requirements = []
            in_header = True

            for line in lines:
                if in_header:
                    # Skip comment lines and empty lines at the beginning
                    if line.strip() and not line.strip().startswith('#'):
                        in_header = False
                        actual_requirements.append(line)
                else:
                    actual_requirements.append(line)

            # Join and clean up
            requirements = '\n'.join(actual_requirements).strip()
            return requirements if requirements else ""

        except Exception as e:
            printer.print(f"⚠️ Warning: Could not read cached additional requirements: {e}")

        return None

    def use_cached_additional_requirements(self, cached_additional: str) -> bool:
        """Show cached additional requirements to user and ask for confirmation."""
        cache_file = self._get_cached_additional_requirements_filename()

        # Prepare content dict
        content_dict = {}

        # Get file modification time for context
        try:
            mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            content_dict["Last Modified"] = mod_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass

        # Add requirements info - show in the box if short enough
        if cached_additional:
            if len(cached_additional) <= 200:
                content_dict["Additional Requirements"] = cached_additional
            else:
                content_dict["Additional Requirements Preview"] = cached_additional[:150] + "..."
                content_dict["Full Length"] = f"{len(cached_additional)} characters"
        else:
            content_dict["Additional Requirements"] = "(None - using same as initial requirements)"

        # Display the beautiful cache panel
        printer.print_cache_panel(
            title="Cached Additional Requirements from Previous Run",
            cache_file=cache_file,
            content_dict=content_dict,
            border_style="cyan"
        )

        # If requirements are long, show full text separately
        if cached_additional and len(cached_additional) > 200:
            printer.print("\n📝 Full cached additional requirements:")
            printer.print(f'"{cached_additional}"')

        question = "Would you like to reuse these cached additional requirements or enter new ones?"
        response = get_user_approval_with_back(question, allow_back=True)
        if response == 'back':
            raise NavigationBackRequest("User requested to go back")
        if response == 'yes':
            printer.print("✅ Using cached additional requirements")
            return True  # Return True means use cached
        else:
            printer.print("🔄 Will enter fresh additional requirements")
            return False  # Return False means don't use cached, enter new

    def save_additional_requirements_to_cache(self, additional_requirements: str):
        """Save additional requirements to cache file for future runs."""
        cache_file = self._get_cached_additional_requirements_filename()

        try:
            # Ensure the cache directory exists
            cache_dir = os.path.dirname(cache_file)
            os.makedirs(cache_dir, exist_ok=True)

            # Additional requirements are cached independently of app name
            header = f"""# Cached additional requirements for source workflow
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# This is for source workflow additional requirements only
# Delete this file to force re-entry

"""

            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(header + additional_requirements)

            printer.print(f"✅ Additional requirements cached to: {cache_file}")

        except Exception as e:
            printer.print(f"⚠️ Warning: Could not save additional requirements to cache: {e}")

    def _get_cached_app_name_filename(self) -> str:
        """Get the filename for cached app name."""
        from workflow_tools.workflow_types import WorkflowType
        
        # Determine workflow type
        if self.context.selected_workflow == WorkflowType.SOURCE:
            workflow_type = "source"
        else:
            workflow_type = "sink"
        
        # Store app names in the prompts directory with a special prefix
        return WorkingDirectory.get_cached_prompt_path(workflow_type, "app_name")
    
    def check_cached_app_name(self) -> Optional[str]:
        """Check if there's a cached app name for this technology."""
        cache_file = self._get_cached_app_name_filename()
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            # Get app name for display - don't use None
            display_name = 'current app'
            if hasattr(self.context.deployment, 'application_name') and self.context.deployment.application_name:
                display_name = self.context.deployment.application_name

            printer.print(f"\n📋 Found cached app name")
            with open(cache_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # Extract only the actual app name (skip header comments)
            lines = content.split('\n')
            cached_app_name = None
            for line in lines:
                if line.strip() and not line.strip().startswith('#'):
                    cached_app_name = line.strip()
                    break

            # Validate the cached name
            if cached_app_name and cached_app_name.lower() != 'none':
                return cached_app_name
            else:
                printer.print("⚠️ Invalid cached app name found, ignoring cache")
                return None
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not read cached app name: {e}")
        
        return None
    
    def use_cached_app_name(self, cached_name: str) -> bool:
        """Show cached app name to user and ask for confirmation."""
        cache_file = self._get_cached_app_name_filename()
        
        # Don't clear screen here - we want to preserve any previous output
        # Prepare content dict
        content_dict = {}
        
        # Get file modification time for context
        try:
            mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            content_dict["Last Modified"] = mod_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
        
        content_dict["App Name"] = cached_name
        
        # Display the beautiful cache panel
        printer.print_cache_panel(
            title="Cached App Name",
            cache_file=cache_file,
            content_dict=content_dict,
            border_style="bright_green"
        )
        
        question = "Would you like to use this cached app name instead of entering a new one?"
        response = get_user_approval_with_back(question, allow_back=True)
        if response == 'back':
            raise NavigationBackRequest("User requested to go back")
        if response == 'yes':
            printer.print("✅ Using cached app name")
            return True
        else:
            printer.print("🔄 Will enter fresh app name")
            return False
    
    def save_app_name_to_cache(self, app_name: str):
        """Save app name to cache file for future runs."""
        cache_file = self._get_cached_app_name_filename()
        
        try:
            # Ensure the cache directory exists
            cache_dir = os.path.dirname(cache_file)
            os.makedirs(cache_dir, exist_ok=True)
            
            # Add header comment with metadata
            from workflow_tools.workflow_types import WorkflowType
            if self.context.selected_workflow == WorkflowType.SOURCE:
                tech_name = getattr(self.context.technology, 'source_technology', None) or self.context.technology.destination_technology
            else:
                tech_name = self.context.technology.destination_technology
            
            header = f"""# Cached app name for {app_name}
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Template: {getattr(self.context.technology, 'selected_item_name', 'Unknown')}
# This is cached app name - delete this file to force re-entry

"""
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(header + app_name)
            
            printer.print(f"✅ App name cached to: {cache_file}")
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not save app name to cache: {e}")

    
    # ===== APP DIRECTORY CACHING METHODS =====
    
    def _get_cached_app_directory_path(self, is_connection_test: bool = False) -> str:
        """Get the path for the cached application directory.
        
        Args:
            is_connection_test: If True, returns path for connection test cache,
                               if False, returns path for main app cache
        """
        # Include app name to make cache unique per application
        app_name = self.context.deployment.application_name or "unknown-app"
        
        # Determine cache type
        cache_type = "connection_test" if is_connection_test else "main"
        
        workflow = self._get_workflow_type()
        return WorkingDirectory.get_cached_app_dir(workflow, app_name, cache_type)
    
    def check_cached_app_directory(self) -> Optional[str]:
        """Check if there's a cached application directory for this technology.
        
        NOTE: This only checks for main app caches, NOT connection test caches.
        
        Returns:
            Path to cached app directory if it exists, None otherwise
        """
        # Always check for main app cache, not connection test cache
        cache_dir = self._get_cached_app_directory_path(is_connection_test=False)
        
        if not os.path.exists(cache_dir):
            return None
        
        # Check if the cache directory has the essential files
        main_py_path = os.path.join(cache_dir, "main.py")
        app_yaml_path = os.path.join(cache_dir, "app.yaml")
        requirements_path = os.path.join(cache_dir, "requirements.txt")
        
        if not all(os.path.exists(path) for path in [main_py_path, app_yaml_path]):
            printer.print(f"⚠️ Warning: Cached app directory incomplete, removing: {cache_dir}")
            import shutil
            shutil.rmtree(cache_dir, ignore_errors=True)
            return None
        
        try:
            # Get app name for display
            app_name = self.context.deployment.application_name or "unknown-app"
            
            # Display in a nice section header
            printer.print_section_header(f"Cached Application Found: {app_name}", 
                                       icon="📂", style="green")
            return cache_dir
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not read cached app directory: {e}")
        
        return None
    
    def use_cached_app_directory(self, cached_app_dir: str) -> bool:
        """Ask user if they want to use cached app directory and handle their choice.
        
        Args:
            cached_app_dir: Path to the cached application directory
            
        Returns:
            True if user wants to use cached app directory, False otherwise
        """
        from workflow_tools.common import get_user_approval
        from workflow_tools.exceptions import NavigationBackRequest
        
        # Get the app name from context for display
        app_name = self.context.deployment.application_name or "unknown-app"
        
        # List the files in the cached directory for user information
        try:
            cached_files = os.listdir(cached_app_dir)
            
            # Get the modification time of the cache
            cache_mtime = os.path.getmtime(cached_app_dir)
            cache_time = datetime.fromtimestamp(cache_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            # Display cache info in a nice panel
            cache_info = {
                "Application": app_name,
                "Files": ', '.join(cached_files),
                "Last Modified": cache_time,
                "Location": cached_app_dir
            }
            
            printer.print_cache_panel(
                title="Cached Application Details",
                cache_file=cached_app_dir,
                content_dict=cache_info,
                border_style="green"
            )
            
        except Exception as e:
            printer.print(f"⚠️ Error reading cache details: {e}")
        
        # Show a preview of the cached main.py code
        try:
            main_py_path = os.path.join(cached_app_dir, "main.py")
            if os.path.exists(main_py_path):
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    code_content = f.read()
                
                # Show first 15 lines of code (skip empty lines and comments at the start)
                code_lines = code_content.split('\n')
                displayed_lines = 0
                preview_lines = []
                for line in code_lines:
                    if displayed_lines >= 15:
                        break
                    preview_lines.append(line)
                    if line.strip():  # Count non-empty lines
                        displayed_lines += 1
                
                preview_code = '\n'.join(preview_lines)
                if len(code_lines) > 15:
                    preview_code += "\n# ... (more code)"
                
                printer.print_code(
                    preview_code,
                    language="python",
                    title=f"Cached Code Preview for '{app_name}'",
                    line_numbers=True
                )
                printer.print_divider()
                
        except Exception as e:
            printer.print(f"   Could not read code preview: {e}")
        
        # Use the proper approval function with back option
        from workflow_tools.common import get_user_approval_with_back
        
        question = f"Would you like to use this cached application '{app_name}' (all files: main.py, app.yaml, requirements.txt) instead of generating new code?"
        response = get_user_approval_with_back(question, allow_back=True)
        
        if response == 'back':
            raise NavigationBackRequest("User requested to go back from cached app selection")
        elif response == 'yes':
            printer.print("✅ Using cached application")
            return True
        else:
            printer.print("📝 Will generate fresh application code and files.")
            return False
    
    def save_app_directory_to_cache(self, app_dir: str, is_connection_test: bool = False) -> bool:
        """Save entire application directory to cache for future runs.
        
        Args:
            app_dir: Source application directory to cache
            is_connection_test: If True, saves as connection test cache,
                               if False, saves as main app cache
            
        Returns:
            True if caching was successful, False otherwise
        """
        if not os.path.exists(app_dir):
            printer.print(f"❌ Error: App directory does not exist: {app_dir}")
            return False
        
        cache_dir = self._get_cached_app_directory_path(is_connection_test=is_connection_test)
        
        try:
            # Remove existing cache if it exists
            if os.path.exists(cache_dir):
                import shutil
                shutil.rmtree(cache_dir)
            
            # Create cache directory
            os.makedirs(cache_dir, exist_ok=True)
            
            # Copy all files from app directory to cache directory
            import shutil
            for item in os.listdir(app_dir):
                source_path = os.path.join(app_dir, item)
                dest_path = os.path.join(cache_dir, item)
                
                if os.path.isfile(source_path):
                    shutil.copy2(source_path, dest_path)
                elif os.path.isdir(source_path):
                    shutil.copytree(source_path, dest_path)
            
            # Get app name for display
            if hasattr(self.context.deployment, 'application_name'):
                app_name = self.context.deployment.application_name
            else:
                app_name = 'app'
            
            printer.print(f"✅ Application directory cached to: {cache_dir}")
            return True
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not save app directory to cache: {e}")
            return False
    
    def restore_cached_app_directory(self, cached_app_dir: str, target_app_dir: str) -> bool:
        """Restore cached application directory to the target location.
        
        Args:
            cached_app_dir: Source cached directory
            target_app_dir: Target application directory
            
        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            # Remove existing target directory if it exists
            if os.path.exists(target_app_dir):
                import shutil
                shutil.rmtree(target_app_dir)
            
            # Create target directory
            os.makedirs(target_app_dir, exist_ok=True)
            
            # Copy all files from cache to target directory
            import shutil
            for item in os.listdir(cached_app_dir):
                source_path = os.path.join(cached_app_dir, item)
                dest_path = os.path.join(target_app_dir, item)
                
                if os.path.isfile(source_path):
                    shutil.copy2(source_path, dest_path)
                elif os.path.isdir(source_path):
                    shutil.copytree(source_path, dest_path)
            
            # Set the context to use this restored directory
            self.context.code_generation.app_extract_dir = target_app_dir
            
            printer.print(f"✅ Application directory restored from cache to: {target_app_dir}")
            return True
            
        except Exception as e:
            printer.print(f"❌ Error restoring cached app directory: {e}")
            return False
    
    # ============== Connection Test Caching ==============
    
    
    def get_cached_connection_test(self) -> Optional[str]:
        """Check for and optionally use cached connection test application.
        
        This method checks for a cached application directory that includes:
        - main.py (full application code)
        - app.yaml (environment variables)
        - requirements.txt (dependencies)
        - connection_test.py (connection test code)
        
        Returns:
            The cached connection test code if user accepts cached app, None otherwise
        """
        # Check for cached connection test app directory (not just code file)
        cached_app_dir = self._get_cached_app_directory_path(is_connection_test=True)
        
        if not os.path.exists(cached_app_dir):
            return None
        
        # Check if the cache directory has the essential files for connection test
        main_py_path = os.path.join(cached_app_dir, "main.py")
        app_yaml_path = os.path.join(cached_app_dir, "app.yaml")
        requirements_path = os.path.join(cached_app_dir, "requirements.txt")
        connection_test_path = os.path.join(cached_app_dir, "connection_test.py")
        
        if not all(os.path.exists(path) for path in [main_py_path, app_yaml_path, requirements_path]):
            printer.print(f"⚠️ Warning: Cached connection test app directory incomplete, removing: {cached_app_dir}")
            import shutil
            shutil.rmtree(cached_app_dir, ignore_errors=True)
            return None
        
        try:
            app_name = self.context.deployment.application_name or "unknown-app"
            
            printer.print(f"📦 Found cached connection test application for '{app_name}'")
            
            # List the files in the cached directory for user information
            cached_files = os.listdir(cached_app_dir)
            printer.print(f"   Cached connection test app contains: {', '.join(cached_files)}")
            
            # Show the modification time of the cache
            cache_mtime = os.path.getmtime(cached_app_dir)
            cache_time = datetime.fromtimestamp(cache_mtime).strftime('%Y-%m-%d %H:%M:%S')
            printer.print(f"   Last modified: {cache_time}")
            
            # Show preview of connection test code if it exists
            if os.path.exists(connection_test_path):
                with open(connection_test_path, 'r', encoding='utf-8') as f:
                    connection_code = f.read()
                
                # Show preview of connection test code
                preview_code = connection_code[:400] + "\n# ..." if len(connection_code) > 400 else connection_code
                printer.print_code(
                    preview_code,
                    language="python",
                    title="Cached Connection Test Code Preview",
                    line_numbers=False
                )
                printer.print_divider()
            
            # Ask user if they want to use the entire cached app (not just code)
            if get_user_approval(f"Use this cached connection test application '{app_name}' (includes all files: main.py, app.yaml, requirements.txt, connection_test.py)?"):
                printer.print("✅ Using cached connection test application.")
                
                # Restore the cached app directory to working directory
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_dir = WorkingDirectory.get_current_app_dir()
                target_app_dir = os.path.join(current_dir, f"{app_name}_conn_test_{timestamp}")
                
                if self.restore_cached_app_directory(cached_app_dir, target_app_dir):
                    # Update context to point to restored directory
                    self.context.code_generation.app_extract_dir = target_app_dir
                    
                    # Return the connection test code
                    if os.path.exists(connection_test_path):
                        # Read from the cached directory (not target, since we want the original)
                        with open(os.path.join(cached_app_dir, "connection_test.py"), 'r') as f:
                            return f.read()
                    else:
                        # Fallback: return main.py content
                        with open(os.path.join(cached_app_dir, "main.py"), 'r') as f:
                            return f.read()
                else:
                    printer.print("❌ Failed to restore cached connection test app")
                    return None
            else:
                printer.print("📝 Will generate fresh connection test application...")
                return None
                
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not process cached connection test app: {e}")
            return None
    
    def backup_and_swap_main_py(self, app_dir: str, connection_test_code: str) -> bool:
        """Backup existing main.py and replace with connection test code.
        
        Args:
            app_dir: The application directory
            connection_test_code: The connection test code to use as main.py
            
        Returns:
            True if successful, False otherwise
        """
        try:
            main_py_path = os.path.join(app_dir, "main.py")
            main_py_backup_path = os.path.join(app_dir, "main_final.py.backup")
            
            # If there's an existing main.py, back it up
            if os.path.exists(main_py_path):
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    existing_main = f.read()
                
                if existing_main != connection_test_code:
                    # This is likely the final generated code, back it up
                    import shutil
                    shutil.copy2(main_py_path, main_py_backup_path)
                    printer.print(f"📋 Backed up existing main.py to main_final.py.backup")
            
            # Write the connection test code as main.py for testing
            with open(main_py_path, 'w', encoding='utf-8') as f:
                f.write(connection_test_code)
            printer.print(f"✅ Connection test code written to main.py for testing")
            
            # Also save as connection_test.py for reference
            test_code_path = os.path.join(app_dir, "connection_test.py")
            with open(test_code_path, 'w', encoding='utf-8') as f:
                f.write(connection_test_code)
            
            return True
            
        except Exception as e:
            printer.print(f"❌ Error swapping main.py: {e}")
            return False
    
    def restore_final_code_from_backup(self, app_dir: str) -> Optional[str]:
        """Restore final code from backup if it exists.
        
        Args:
            app_dir: The application directory
            
        Returns:
            The restored code if successful, None otherwise
        """
        try:
            main_py_path = os.path.join(app_dir, "main.py")
            main_py_backup_path = os.path.join(app_dir, "main_final.py.backup")
            
            if not os.path.exists(main_py_backup_path):
                return None
            
            printer.print("📋 Found backup of final code from connection testing phase.")
            
            if get_user_approval("Use existing final code from backup? (No will generate new code)"):
                import shutil
                shutil.copy2(main_py_backup_path, main_py_path)
                
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    restored_code = f.read()
                
                printer.print("✅ Restored final code from backup")
                return restored_code
            else:
                printer.print("📝 Will generate fresh final code...")
                return None
                
        except Exception as e:
            printer.print(f"❌ Error restoring from backup: {e}")
            return None
    
    def cleanup_connection_test_backup(self, app_dir: str) -> None:
        """Remove connection test backup after successful final code generation.
        
        Args:
            app_dir: The application directory
        """
        try:
            main_py_backup_path = os.path.join(app_dir, "main_final.py.backup")
            if os.path.exists(main_py_backup_path):
                os.remove(main_py_backup_path)
                printer.print("🗑️ Removed connection test backup (replaced with new final code)")
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not remove backup: {e}")
    
    # ============== Schema Analysis Caching by App Name ==============
    
    def _get_cached_schema_analysis_filename(self, app_name: str) -> str:
        """Get the filename for cached schema analysis based on app name.
        
        Args:
            app_name: The application name
            
        Returns:
            Path to the schema analysis cache file
        """
        workflow = self._get_workflow_type()
        return WorkingDirectory.get_cached_schema_path(workflow, app_name)
    
    def check_cached_schema_analysis(self, app_name: str) -> Optional[str]:
        """Check if there's a cached schema analysis for this app name.
        
        Args:
            app_name: The application name
            
        Returns:
            Cached schema analysis content or None if not found
        """
        cache_file = self._get_cached_schema_analysis_filename(app_name)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            printer.print(f"\n📋 Found cached schema analysis for app '{app_name}'")
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_schema = f.read()
            
            return cached_schema
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not read cached schema analysis: {e}")
        
        return None
    
    def use_cached_schema_analysis(self, cached_schema: str, app_name: str) -> bool:
        """Show cached schema analysis to user and ask for confirmation.
        
        Args:
            cached_schema: The cached schema analysis content
            app_name: The application name
            
        Returns:
            True if user wants to use cached schema, False otherwise
        """
        cache_file = self._get_cached_schema_analysis_filename(app_name)
        
        # Prepare content dict
        content_dict = {}
        
        # Get file modification time for context
        try:
            mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            content_dict["Last Modified"] = mod_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
        
        content_dict["App Name"] = app_name
        content_dict["Schema Size"] = f"{len(cached_schema)} characters"
        
        # Display the beautiful cache panel
        printer.print_cache_panel(
            title=f"Cached Schema Analysis for '{app_name}'",
            cache_file=cache_file,
            content_dict=content_dict,
            border_style="bright_magenta"
        )
        
        # Show the cached schema as a formatted markdown preview
        printer.print_markdown_preview(
            cached_schema,
            max_length=500,
            title="Schema Preview",
            style="bright_magenta"
        )
        
        question = f"Would you like to use this cached schema analysis for app '{app_name}' instead of running connection test and fresh analysis?"
        response = get_user_approval_with_back(question, allow_back=True)
        if response == 'back':
            raise NavigationBackRequest("User requested to go back")
        if response == 'yes':
            printer.print("✅ Using cached schema analysis")
            return True
        else:
            printer.print("📥 Will run connection test and generate fresh schema analysis")
            return False
    
    def save_schema_analysis_to_cache(self, schema_analysis: str, app_name: str):
        """Save schema analysis to cache file for future runs.
        
        Args:
            schema_analysis: The schema analysis content to cache
            app_name: The application name
        """
        cache_file = self._get_cached_schema_analysis_filename(app_name)
        
        try:
            os.makedirs("working_files", exist_ok=True)
            
            # Add header comment with metadata
            header = f"""# Cached schema analysis for {app_name}
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# This is cached schema analysis - delete this file to force fresh analysis

"""
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(header + schema_analysis)
            
            printer.print(f"✅ Schema analysis cached to: {cache_file}")
            
        except Exception as e:
            printer.print(f"⚠️ Warning: Could not save schema analysis to cache: {e}")

    # ============== Centralized App Generation with Cache ==============
    
    def handle_cached_app_generation(self, workflow_type: str = "sink") -> Optional[str]:
        """Centralized method to handle cached app directory for generation phases.
        
        Args:
            workflow_type: Either "sink" or "source"
            
        Returns:
            The cached code if successful, None if should continue to fresh generation
        """
        cached_app_dir = self.check_cached_app_directory()
        if not cached_app_dir:
            return None
        
        if not self.use_cached_app_directory(cached_app_dir):
            return None
        
        # Generate new target app directory name in current directory
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        app_name = self.context.deployment.application_name or f"unknown-{workflow_type}"
        current_dir = WorkingDirectory.get_current_app_dir()
        target_app_dir = os.path.join(current_dir, f"{app_name}_restored_{timestamp}")
        
        # Restore the cached app directory
        if not self.restore_cached_app_directory(cached_app_dir, target_app_dir):
            printer.print("❌ Error restoring cached app directory, generating fresh code")
            return None
        
        printer.print("✅ Using cached application files")
        
        # For source workflow, handle the backup/restore of final code
        if workflow_type == "source":
            main_py_path = os.path.join(target_app_dir, "main.py")
            main_py_backup_path = os.path.join(target_app_dir, "main_final.py.backup")
            
            if os.path.exists(main_py_backup_path):
                # Restore the final code from backup
                import shutil
                shutil.copy2(main_py_backup_path, main_py_path)
                printer.print("📋 Restored final code from backup")
        
        # Read and return the main.py
        main_py_path = os.path.join(target_app_dir, "main.py")
        try:
            with open(main_py_path, 'r', encoding='utf-8') as f:
                cached_code = f.read()
            return cached_code
        except Exception as e:
            printer.print(f"❌ Error reading cached main.py: {e}")
            return None
