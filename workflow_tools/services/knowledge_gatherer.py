# knowledge_gatherer.py - Unified Knowledge Gathering Service

import os
from typing import Dict, Any, Optional
from workflow_tools.contexts import WorkflowContext
from workflow_tools.common import printer
from workflow_tools.phases.shared import EnvVarManager, AppManager, CacheUtils
from workflow_tools.phases.base.base_phase import PhaseResult
from workflow_tools.exceptions import NavigationBackRequest
from agents import RunConfig


class KnowledgeGatheringService:
    """Unified service for knowledge gathering across sink and source workflows."""
    
    def __init__(self, context: WorkflowContext, run_config: RunConfig, debug_mode: bool = False):
        self.context = context
        self.run_config = run_config
        self.debug_mode = debug_mode
        
        # Initialize modular components
        self.env_var_manager = EnvVarManager(context, run_config, debug_mode)
        self.app_manager = AppManager(context, debug_mode)
        self.cache_utils = CacheUtils(context, debug_mode)
    
    async def gather_knowledge(self, workflow_type: str) -> PhaseResult:
        """
        Gather knowledge for either sink or source workflow.
        Now uses fixed starter templates instead of AI selection.
        
        Args:
            workflow_type: Either "sink" or "source"
        
        Returns:
            PhaseResult indicating success or failure
        """
        # Phase header is already shown by base_phase
        # Just show what we're doing
        printer.print("\n")  # Add spacing after phase header
        printer.print("📦 Setting up application and workspace...")
        printer.print("")  # Add spacing between sections
        
        # Use fixed starter templates
        if workflow_type == "sink":
            template_id = "starter-destination"
            printer.print("📦 Using starter sink template (starter-destination)")
        else:  # source
            template_id = "starter-source"
            printer.print("📦 Using starter source template (starter-source)")
        
        # Store the template selection in context
        # Fixed: Use library_item_id instead of selected_template_id for consistency
        self.context.technology.library_item_id = template_id
        self.context.technology.selected_template_id = template_id
        # DO NOT overwrite destination_technology - it contains the user's requirements!
        
        # App name should already be set by prerequisites phase
        if not hasattr(self.context.deployment, 'application_name') or not self.context.deployment.application_name:
            printer.print("\n❌ Application name not set. This should have been collected in prerequisites phase.")
            return PhaseResult(success=False, message="Application name not set")
        
        sanitized_name = self.context.deployment.application_name
        printer.print(f"✅ Using application name: {sanitized_name}")
        printer.print("")  # Add spacing before next section
        
        # Create application from the starter template
        printer.print("🔨 Creating application from starter template...")
        if not await self.app_manager.create_application():
            return PhaseResult(success=False, message="Failed to create application")
        
        # For source workflows, check for cached schema analysis based on app name
        if workflow_type == "source":
            cached_schema = self.cache_utils.check_cached_schema_analysis(sanitized_name)
            if cached_schema:
                # Found cached schema - ask user if they want to use it
                try:
                    if self.cache_utils.use_cached_schema_analysis(cached_schema, sanitized_name):
                        # User wants to use cached schema - skip connection testing
                        printer.print("🚀 Skipping connection testing phase due to cached schema.")

                        # Set flag to skip connection testing and schema phases
                        self.context.skip_connection_testing = True

                        # IMPORTANT: Also load the cached requirements so generation phase has them
                        cached_requirements = self.cache_utils.check_cached_user_prompt()
                        if cached_requirements:
                            # Store in context so generation phase can access them
                            self.context.technology.source_technology = cached_requirements
                            printer.print(f"✅ Loaded cached requirements for generation phase")
                        
                        # Save the cached schema to proper cache directory
                        import os
                        from datetime import datetime
                        from workflow_tools.core.working_directory import WorkingDirectory
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        schema_file_path = WorkingDirectory.get_cached_schema_path("source", f"source_schema_{timestamp}")
                        
                        with open(schema_file_path, 'w', encoding='utf-8') as file:
                            file.write(cached_schema)
                        
                        # Set the schema doc path in context (required for code generation)
                        self.context.code_generation.source_schema_doc_path = schema_file_path
                        printer.print(f"✅ Loaded cached schema analysis to: {schema_file_path}")
                        
                        # Continue with rest of workflow
                        success = await self._continue_workflow_after_template_selection(workflow_type)
                        if success:
                            return PhaseResult(success=True, message="Source knowledge gathering completed with cached schema")
                        else:
                            return PhaseResult(success=False, message="Failed to complete workflow after template selection")
                    else:
                        # User wants fresh analysis - proceed normally with connection testing
                        printer.print("📥 Proceeding with fresh schema analysis and connection testing.")
                        # No special flag needed - normal workflow will proceed
                except NavigationBackRequest:
                    raise  # Re-raise navigation requests
            # If no cached schema found, proceed normally
        
        # Continue with rest of workflow (download code, etc.)
        success = await self._continue_workflow_after_template_selection(workflow_type)
        if success:
            return PhaseResult(success=True, message=f"{workflow_type.capitalize()} knowledge gathering and app setup completed")
        else:
            return PhaseResult(success=False, message="Failed to complete workflow after template selection")
    
    def _get_technology(self, workflow_type: str) -> Optional[str]:
        """Get the appropriate technology based on workflow type."""
        if workflow_type == "sink":
            return self.context.technology.destination_technology
        else:  # source
            # For source, check source_technology first, then fall back to destination_technology
            return getattr(self.context.technology, 'source_technology', None) or self.context.technology.destination_technology
    
    async def _continue_workflow_after_template_selection(self, workflow_type: str) -> bool:
        """Continue the workflow after template selection.
        Note: We no longer collect environment variables here - Claude Code will handle that.
        """
        # Download and extract the whole app to working_files subfolder
        printer.print_debug(f"\n🔄 Downloading and extracting application code.")
        extract_dir = self.app_manager.download_and_extract_app_code(
            self.context.workspace.workspace_id, 
            self.context.deployment.application_id
        )
        if not extract_dir:
            printer.print("❌ Failed to download application code.")
            return False
        
        self.context.code_generation.app_extract_dir = extract_dir
        
        # Read template requirements.txt
        printer.print_debug(f"\n📋 Reading template requirements.")
        requirements_path = os.path.join(extract_dir, "requirements.txt")
        if os.path.exists(requirements_path):
            # Update quixstreams version before loading
            from workflow_tools.services.requirements_updater import RequirementsUpdater
            updater = RequirementsUpdater()
            updater.update_requirements_file(requirements_path)
            
            # Now read the updated requirements
            with open(requirements_path, 'r', encoding='utf-8') as f:
                self.context.code_generation.template_requirements = f.read()
            printer.print_debug("✅ Loaded requirements.txt from extracted code")
        else:
            printer.print_debug("⚠️ Warning: requirements.txt not found in extracted code")
            self.context.code_generation.template_requirements = ""
        
        # Note: We're NOT collecting environment variables here anymore
        # Claude Code will update app.yaml and we'll collect them after code generation
        printer.print("✅ Template downloaded and ready for code generation")
        
        # Load template files from extracted directory (still needed for reference)
        self.app_manager.load_template_files(extract_dir)
        
        # Read documentation (still useful for context)
        self.cache_utils.load_documentation(workflow_type)
        
        # Save debug files if in debug mode
        if self.debug_mode:
            self.app_manager.save_debug_files()
        
        printer.print(f"✅ All {workflow_type} knowledge gathered successfully.")
        return True