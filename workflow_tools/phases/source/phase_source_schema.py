# phase_source_schema.py - Source Schema Analysis Phase

import os
import json
from datetime import datetime
from agents import Agent, Runner, RunConfig
from workflow_tools.common import WorkflowContext, printer, get_user_approval, get_user_approval_with_back
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.services.model_utils import create_agent_with_model_config
from workflow_tools.integrations import quix_tools

class SourceSchemaPhase(BasePhase):
    """Handles source schema analysis from sample data."""
    
    phase_name = "source_schema"
    phase_description = "Analyze source schema"
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.run_config = RunConfig(workflow_name="Create Quix Source (V1)")

        # Load agent instructions from external prompt file
        from workflow_tools.core.prompt_manager import load_agent_instructions

        # Define schema analyzer agent using model configuration
        self.schema_analyzer_agent = create_agent_with_model_config(
            agent_name="SourceSchemaAnalyzerAgent",
            task_type="schema_analysis",
            workflow_type="source",
            instructions=load_agent_instructions("SourceSchemaAnalyzerAgent"),
            context_type=WorkflowContext
        )
    
    async def execute(self) -> PhaseResult:
        """Execute the source schema analysis workflow."""
        # Phase header is already shown by base_phase
        # No need for additional header here
        
        try:
            # Create working_files directory
            os.makedirs("working_files", exist_ok=True)
            
            # Note: Schema caching is now handled earlier in the knowledge gathering phase
            # This phase only runs when fresh schema analysis is needed
            printer.print("📥 Performing fresh schema analysis from sample data.")
            
            # Step 1: Analyze sample data structure
            if not await self._analyze_sample_data_structure():
                return PhaseResult(success=False, message="Phase failed")
            
            # Step 2: Create schema documentation (generate timestamped file name)
            if not self._create_schema_documentation():
                return PhaseResult(success=False, message="Phase failed")
            
            # Step 3: Get user approval
            if not await self._get_schema_approval():
                return PhaseResult(success=False, message="Phase failed")
            
            printer.print("✅ Source schema analysis completed successfully!")
            return PhaseResult(success=True, message="Phase completed successfully")
            
        except NavigationBackRequest:
            # Re-raise navigation requests to be handled by phase orchestrator
            raise
        except Exception as e:
            printer.print(f"❌ Error in source schema analysis: {str(e)}")
            return PhaseResult(success=False, message="Phase failed")
    
    async def _analyze_sample_data_structure(self) -> bool:
        """Analyze the structure of sample data using AI."""
        printer.print("🔍 Analyzing sample data structure. This might take a minute...")
        
        try:
            if not hasattr(self.context, 'sample_data_file') or not os.path.exists(self.context.sample_data_file):
                printer.print("❌ No sample data file found for analysis.")
                return False
            
            # Read sample data
            with open(self.context.sample_data_file, 'r', encoding='utf-8') as file:
                sample_data = file.read()

            # Load prompt template and format with variables
            from workflow_tools.core.prompt_manager import load_task_prompt
            prompt = load_task_prompt(
                "source_schema_analysis",
                technology_name=self.context.technology.destination_technology,
                sample_data=sample_data
            )
            
            # Get analysis from AI with timeout
            import asyncio
            try:
                result = await asyncio.wait_for(
                    Runner.run(
                        starting_agent=self.schema_analyzer_agent,
                        input=prompt,
                        context=self.context,
                        run_config=self.run_config
                    ),
                    timeout=120  # 2 minute timeout
                )
            except asyncio.TimeoutError:
                printer.print("⚠️ Schema analysis timed out after 2 minutes.")
                printer.print("   This might be due to the AI model being overloaded or the sample data being too large.")
                return False
            
            # Store analysis
            self.context.source_schema_analysis = result.final_output
            
            printer.print("✅ Sample data structure analyzed.")
            
            return True
            
        except Exception as e:
            printer.print(f"❌ Error analyzing sample data structure: {str(e)}")
            return False
    
    def _create_schema_documentation(self, schema_file_path: str = None) -> bool:
        """Create and save schema documentation."""
        printer.print("📝 Creating schema documentation.")
        
        try:
            # Create comprehensive schema document
            schema_doc = f"""# Source Schema Analysis - {self.context.technology.destination_technology}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Source Technology:** {self.context.technology.destination_technology}
**Topic:** {self.context.workspace.topic_name}

## Schema Analysis

{self.context.source_schema_analysis}

## Configuration Details

- **Workspace ID:** {self.context.workspace.workspace_id}
- **Output Topic:** {self.context.workspace.topic_name} ({self.context.workspace.topic_id})
- **Application:** {self.context.deployment.application_name} ({self.context.deployment.application_id})

## Environment Variables

{json.dumps(self.context.credentials.env_var_values or {}, indent=2)}

## Sample Data Location

{getattr(self.context, 'sample_data_file', 'Not available')}
"""
            
            # Use provided path or generate timestamped one
            if not schema_file_path:
                from workflow_tools.core.working_directory import WorkingDirectory
                # Get the schema cache path using a timestamp identifier
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                schema_file_path = WorkingDirectory.get_cached_schema_path("source", f"source_schema_{timestamp}")
            
            os.makedirs("working_files", exist_ok=True)
            
            with open(schema_file_path, 'w', encoding='utf-8') as file:
                file.write(schema_doc)
            
            self.context.code_generation.source_schema_doc_path = schema_file_path
            
            printer.print(f"✅ Schema documentation created: {schema_file_path}")
            
            return True
            
        except Exception as e:
            printer.print(f"❌ Error creating schema documentation: {str(e)}")
            return False
    
    
    async def _get_schema_approval(self) -> bool:
        """Get user approval for the schema analysis."""
        printer.print_section_header("Schema Analysis Results", icon="👀", style="green")
        printer.print("")
        
        retry_count = 0
        max_retries = 5
        
        try:
            while retry_count <= max_retries:
                # Display the schema analysis with Rich markdown formatting
                printer.print_markdown(
                    self.context.source_schema_analysis,
                    title="📊 Schema Analysis Summary"
                )
                printer.print("")
                
                # Get user approval
                response = get_user_approval_with_back("Does this schema analysis look correct for your source data?", allow_back=True)
                if response == 'back':
                    raise NavigationBackRequest("User requested to go back")
                if response == 'yes':
                    printer.print("✅ Schema analysis approved by user.")
                    break
                else:
                    from workflow_tools.core.questionary_utils import select
                    
                    printer.print("\n❌ Schema analysis needs adjustment.")
                    
                    choices = [
                        {'name': '💬 Provide feedback to improve the analysis', 'value': '1'},
                        {'name': '✏️ Manually edit the schema documentation', 'value': '2'},
                        {'name': '← Go back to previous phase', 'value': '3'},
                        {'name': '❌ Abort workflow', 'value': '4'}
                    ]
                    
                    retry_choice = select("Choose an option:", choices, show_border=True)
                    
                    if retry_choice == "1":
                        printer.print("🔄 Retrying schema analysis with feedback.")
                        success = await self._retry_schema_analysis()
                        if success:
                            retry_count += 1
                            continue  # Loop to show updated analysis
                        else:
                            printer.print("❌ Failed to re-analyze schema.")
                            return False
                    elif retry_choice == "2":
                        from workflow_tools.core.questionary_utils import text
                        printer.print("✏️  Please manually edit the schema documentation file:")
                        printer.print(f"   {self.context.code_generation.source_schema_doc_path}")
                        text("Press ENTER when you've finished editing:", show_border=False)
                        return True
                    elif retry_choice == "3":
                        raise NavigationBackRequest("User requested to go back")
                    else:
                        printer.print("❌ Schema analysis aborted by user.")
                        return False
            
            if retry_count > max_retries:
                printer.print(f"❌ Maximum retry attempts ({max_retries}) reached.")
                return False
            
            # Save schema analysis to app name-based cache for future use
            from workflow_tools.phases.shared.cache_utils import CacheUtils
            cache_utils = CacheUtils(self.context, self.debug_mode)
            app_name = self.context.deployment.application_name
            if app_name and self.context.source_schema_analysis:
                # Read the complete schema document for caching
                if hasattr(self.context.code_generation, 'source_schema_doc_path') and os.path.exists(self.context.code_generation.source_schema_doc_path):
                    with open(self.context.code_generation.source_schema_doc_path, 'r', encoding='utf-8') as f:
                        complete_schema_doc = f.read()
                    cache_utils.save_schema_analysis_to_cache(complete_schema_doc, app_name)
            
            return True
            
        except Exception as e:
            printer.print(f"❌ Error getting schema approval: {str(e)}")
            return False
    
    async def _retry_schema_analysis(self) -> bool:
        """Retry schema analysis with user feedback."""
        try:
            # Get user feedback for improvement
            feedback = printer.input("What specific aspects of the schema analysis need improvement? ").strip()
            
            if not feedback:
                printer.print("❌ No feedback provided for improvement.")
                return False
            
            printer.print("\n🤖 Re-analyzing schema with your feedback...")
            
            # Read sample data again if available
            sample_data = ""
            if hasattr(self.context, 'sample_data_file') and os.path.exists(self.context.sample_data_file):
                with open(self.context.sample_data_file, 'r', encoding='utf-8') as file:
                    sample_data = file.read()
            
            # Load retry prompt template and format with variables
            from workflow_tools.core.prompt_manager import load_task_prompt
            enhanced_prompt = load_task_prompt(
                "source_schema_analysis_retry",
                technology_name=self.context.technology.destination_technology,
                previous_analysis=self.context.source_schema_analysis,
                user_feedback=feedback,
                sample_data=sample_data
            )
            
            # Re-run the analysis
            import asyncio
            from agents import Runner
            
            try:
                result = await asyncio.wait_for(
                    Runner.run(
                        starting_agent=self.schema_analyzer_agent,
                        input=enhanced_prompt,
                        context=self.context,
                        run_config=self.run_config
                    ),
                    timeout=120
                )
                
                # Update the schema analysis
                self.context.source_schema_analysis = result.final_output
                
                # Display updated schema analysis with Rich markdown formatting
                printer.print_markdown(
                    self.context.source_schema_analysis,
                    title="📊 Updated Schema Analysis"
                )
                
                # Recreate the documentation with updated analysis
                return self._create_schema_documentation()
                
            except asyncio.TimeoutError:
                printer.print("⚠️ Schema re-analysis timed out.")
                return False
                
        except Exception as e:
            printer.print(f"❌ Error during schema analysis retry: {str(e)}")
            return False