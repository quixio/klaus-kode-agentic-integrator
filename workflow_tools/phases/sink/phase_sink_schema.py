# phase_sink_schema.py - Sink Schema Analysis Phase

import os
import json
from agents import Agent, Runner
from workflow_tools.common import WorkflowContext, printer, get_user_approval, get_user_approval_with_back
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.core.navigation import NavigationRequest, SinkWorkflowSteps
from workflow_tools.integrations import quix_tools
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.services.model_utils import create_agent_with_model_config
from workflow_tools.core.prompt_manager import load_agent_instructions, load_task_prompt

class SinkSchemaPhase(BasePhase):
    """Handles schema analysis and approval."""
    
    phase_name = "sink_schema"
    phase_description = "Analyze data schema from source topic"
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        
        # Define schema analyzer agent using model configuration and external prompts
        self.schema_analyzer_agent = create_agent_with_model_config(
            agent_name="SinkSchemaAnalyzerAgent",
            task_type="schema_analysis",
            workflow_type="sink",
            instructions=load_agent_instructions("SinkSchemaAnalyzerAgent"),
            context_type=WorkflowContext
        )
    
    async def execute(self) -> PhaseResult:
        """Analyze schema from topic messages and get user approval."""
        if not self.context.workspace.workspace_id or not self.context.workspace.topic_id: 
            return PhaseResult(success=False, message="Missing workspace_id or topic_id")
        
        # Create working_files directory
        os.makedirs("working_files", exist_ok=True)
        
        # Check if cached schema analysis exists using proper cache structure
        from workflow_tools.core.working_directory import WorkingDirectory
        schema_file_path = WorkingDirectory.get_cached_schema_path("sink", f"{self.context.workspace.topic_id}_schema_analysis")
        if os.path.exists(schema_file_path):
            printer.print(f"\n📋 Found existing schema analysis for topic '{self.context.workspace.topic_id}'")
            with open(schema_file_path, "r", encoding="utf-8") as f:
                cached_schema = f.read()
            
            printer.print("\n--- Cached Schema Analysis ---")
            printer.print_markdown(
                cached_schema,
                title="📊 Cached Schema Analysis"
            )
            
            response = get_user_approval_with_back("Would you like to use this cached schema analysis instead of re-analyzing?", allow_back=True)
            if response == 'back':
                raise NavigationBackRequest("User requested to go back")
            if response == 'yes':
                # Clear screen before continuing with cached schema
                from workflow_tools.common import clear_screen
                clear_screen()
                
                printer.print("✅ Using cached schema analysis.")
                
                # Extract the schema description (remove the title line)
                schema_lines = cached_schema.split('\n')
                if schema_lines and schema_lines[0].startswith("# Schema Analysis for Topic:"):
                    schema_description = '\n'.join(schema_lines[2:])  # Skip title and empty line
                else:
                    schema_description = cached_schema
                
                # Create backwards-compatible schema_analysis.md file in cache/schemas directory
                backwards_compatible_path = WorkingDirectory.get_cached_schema_path("sink", "schema_analysis")
                with open(backwards_compatible_path, "w", encoding="utf-8") as f:
                    f.write(cached_schema)  # Write the full cached content
                printer.print(f"📋 Created backwards-compatible schema file: {backwards_compatible_path}")
                
                # Store the schema analysis in context (without sample data since we're using cached)
                self.context.schema.data_schema = {"analysis": schema_description, "sample_data": None}
                return PhaseResult(success=True, message="Using cached schema analysis")
            else:
                # Clear screen before fresh analysis
                from workflow_tools.common import clear_screen
                clear_screen()
                
                printer.print("📥 Proceeding with fresh schema analysis.")
        
        printer.print("\nFetching message sample from topic...")
        printer.print(f"Topic: {self.context.workspace.topic_name}")
        messages_data = await quix_tools.get_topic_sample(self.context.workspace.workspace_id, self.context.workspace.topic_id)

        # Check if the API call failed or topic is empty
        if not messages_data:
            printer.print("\n⚠️  The topic exists but appears to be empty (no messages found).")
            printer.print(f"   Topic: {self.context.workspace.topic_name}")
            printer.print("\n   This is normal if you haven't set up a data source yet.")
            printer.print("   For sink workflows, you typically need:")
            printer.print("   • A source application writing data to this topic")
            printer.print("   • Or some test data to analyze the schema")

            printer.print("\n   You have a few options:")
            printer.print("   1. Go back and select a different topic that has data")
            printer.print("   2. Set up a source to write data to this topic first")
            printer.print("   3. Skip schema analysis and define it manually in your code")

            # Use questionary for better selection
            from workflow_tools.core.questionary_utils import select
            choices = [
                {'name': '← Go back and select a different topic', 'value': 'back'},
                {'name': '⏭️  Skip schema analysis and proceed', 'value': 'skip'},
                {'name': '❌ Exit workflow to set up a data source first', 'value': 'exit'}
            ]

            response = select("What would you like to do?", choices, show_border=True)

            if response == 'back':
                # Request navigation back to topic selection step
                self.context.navigation_request = NavigationRequest(
                    target_step=SinkWorkflowSteps.COLLECT_TOPIC,
                    message="User requested to go back to select different topic"
                )
                raise NavigationBackRequest("User requested to go back to select different topic")
            elif response == 'skip':
                printer.print("\n⚠️  Skipping schema analysis.")
                printer.print("   You'll need to handle the data schema manually in your sink code.")
                self.context.schema.data_schema = {"analysis": "Schema analysis skipped - topic was empty", "sample_data": None}
                return PhaseResult(success=True, message="Schema analysis skipped - proceeding without schema")
            else:  # exit
                printer.print("\n👍 Exiting workflow.")
                printer.print("   Set up a source to write data to the topic, then run the sink workflow again.")
                return PhaseResult(success=False, message="User chose to exit and set up data source first")
        
        # Check if the topic has no messages (empty topic)
        if isinstance(messages_data, dict) and "messages" in messages_data:
            messages = messages_data.get("messages", [])
            if not messages:
                printer.print("\n⚠️  The selected topic appears to be empty (no messages found).")
                printer.print(f"   Topic: {self.context.workspace.topic_id}")
                printer.print("\n   Please ensure the topic contains data before attempting to analyze its schema.")
                
                response = get_user_approval_with_back(
                    "\nWould you like to go back and select a different topic?", 
                    allow_back=True
                )
                
                if response == 'back' or response == 'yes':
                    # Request navigation back to topic selection step
                    self.context.navigation_request = NavigationRequest(
                        target_step=SinkWorkflowSteps.COLLECT_TOPIC,
                        message="User requested to go back due to empty topic"
                    )
                    raise NavigationBackRequest("User requested to go back due to empty topic")
                else:
                    return PhaseResult(success=False, message="Topic is empty - no messages to analyze")
        
        printer.print("🤖 Asking AI to analyze schema from the data sample - this might take a minute.")
        data_sample_str = json.dumps(messages_data, indent=2, ensure_ascii=False)
        
        # Extract first message for raw example
        first_message = None
        if messages_data and isinstance(messages_data, dict) and "messages" in messages_data:
            messages = messages_data.get("messages", [])
            if messages:
                first_message = messages[0]
        
        # Load prompt template and format with variables
        agent_prompt = load_task_prompt(
            "sink_schema_analysis",
            data_sample=data_sample_str
        )
        
        # Get analysis from AI with timeout
        import asyncio
        try:
            result = await asyncio.wait_for(
                Runner.run(starting_agent=self.schema_analyzer_agent, input=agent_prompt),
                timeout=120  # 2 minute timeout
            )
        except asyncio.TimeoutError:
            printer.print("⚠️ Schema analysis timed out after 2 minutes.")
            printer.print("   This might be due to the AI model being overloaded or the data being too large.")
            return PhaseResult(success=False, message="Schema analysis timed out")
        
        schema_description = result.final_output
        # Display schema analysis with Rich markdown formatting
        printer.print_markdown(
            schema_description,
            title="🤖 AI Schema Analysis"
        )
        
        # Loop to allow retry with feedback
        retry_count = 0
        max_retries = 5
        current_schema_description = schema_description
        
        while retry_count <= max_retries:
            response = get_user_approval_with_back("Does this analysis look correct?", allow_back=True)
            if response == 'back':
                raise NavigationBackRequest("User requested to go back")
            if response == 'yes':
                # Save schema analysis with topic ID-based filename
                with open(schema_file_path, "w", encoding="utf-8") as f:
                    f.write(f"# Schema Analysis for Topic: {self.context.workspace.topic_id}\n\n{current_schema_description}")
                printer.print(f"✅ Schema analysis approved and saved to '{schema_file_path}'.")
                
                # Store the schema analysis in context
                self.context.schema.data_schema = {"analysis": current_schema_description, "sample_data": messages_data}
                return PhaseResult(success=True, message="Schema analysis completed and approved")
            else:
                from workflow_tools.core.questionary_utils import select, text
                
                # User rejected - offer options
                printer.print("\n❌ Schema analysis needs adjustment.")
                
                choices = [
                    {'name': '💬 Provide feedback to improve the analysis', 'value': '1'},
                    {'name': '← Go back to previous phase', 'value': '2'},
                    {'name': '❌ Abort workflow', 'value': '3'}
                ]
                
                choice = select("Choose an option:", choices, show_border=True)
                
                if choice == '2':
                    raise NavigationBackRequest("User requested to go back")
                elif choice == '3':
                    printer.print("🛑 Schema analysis aborted by user.")
                    return PhaseResult(success=False, message="Schema rejected by user")
                elif choice == '1':
                    # Get user feedback
                    printer.print("\n📝 Please describe what needs to be corrected in the schema analysis:")
                    printer.print("   (e.g., 'The timestamp field is actually in milliseconds, not seconds')")
                    user_feedback = text("", multiline=False, show_border=False).strip()
                    
                    if not user_feedback:
                        printer.print("⚠️ No feedback provided. Please try again.")
                        continue
                    
                    # Re-run analysis with feedback
                    printer.print("\n🤖 Re-analyzing schema with your feedback...")
                    
                    # Load retry prompt template and format with variables
                    enhanced_prompt = load_task_prompt(
                        "sink_schema_analysis_retry",
                        previous_analysis=current_schema_description,
                        user_feedback=user_feedback,
                        data_sample=data_sample_str
                    )
                    
                    try:
                        result = await asyncio.wait_for(
                            Runner.run(starting_agent=self.schema_analyzer_agent, input=enhanced_prompt),
                            timeout=120
                        )
                        current_schema_description = result.final_output
                        
                        printer.print("\n--- Updated Schema Analysis ---")
                        printer.print_markdown(
                            current_schema_description,
                            title="🔄 Updated Schema Analysis"
                        )
                        
                        retry_count += 1
                        
                    except asyncio.TimeoutError:
                        printer.print("⚠️ Schema re-analysis timed out.")
                        printer.print("🛑 Unable to complete schema analysis.")
                        return PhaseResult(success=False, message="Schema analysis timed out")
                    except Exception as e:
                        printer.print(f"❌ Error during re-analysis: {str(e)}")
                        printer.print("🛑 Unable to complete schema analysis.")
                        return PhaseResult(success=False, message=f"Schema analysis error: {str(e)}")
                else:
                    printer.print("⚠️ Invalid choice. Please try again.")
                    continue
        
        printer.print(f"❌ Maximum retry attempts ({max_retries}) reached.")
        return PhaseResult(success=False, message="Schema analysis could not be completed")