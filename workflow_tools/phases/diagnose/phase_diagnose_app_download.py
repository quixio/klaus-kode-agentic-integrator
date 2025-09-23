# phase_diagnose_app_download.py - Application Download and Analysis Phase

import os
import asyncio
from typing import Optional, Dict, Any
from workflow_tools.services.runner_utils import run_agent_with_retry
from workflow_tools.common import WorkflowContext, printer
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult
from workflow_tools.phases.shared.app_management import AppManager
from workflow_tools.integrations.quix_tools import get_application_details
from workflow_tools.core.prompt_manager import prompt_manager, load_agent_instructions
from workflow_tools.services.model_utils import create_agent_with_model_config
from workflow_tools.exceptions import NavigationBackRequest
from workflow_tools.core.questionary_utils import select
from workflow_tools.common import clear_screen
from workflow_tools.core.navigation import NavigationRequest, DiagnoseWorkflowSteps


class DiagnoseAppDownloadPhase(BasePhase):
    """Downloads application files and analyzes them to understand the app's purpose."""
    
    phase_name = "diagnose_app_download"
    phase_description = "Download and analyze application"
    
    def __init__(self, context: WorkflowContext, run_config: Any, debug_mode: bool = False):
        super().__init__(context, debug_mode)
        self.app_manager = AppManager(context, debug_mode)
        
        # Create analyzer agent
        self.analyzer_agent = create_agent_with_model_config(
            agent_name="DiagnoseAnalyzerAgent",
            task_type="code_analysis",
            workflow_type="diagnose",
            instructions="Analyze the application code to understand its purpose and functionality.",
            context_type=WorkflowContext
        )
    
    async def execute(self) -> PhaseResult:
        """Execute the download and analysis phase."""
        try:
            printer.print("\n" + "="*50)
            printer.print("APPLICATION DOWNLOAD & ANALYSIS")
            printer.print("="*50)
            
            # Step 1: Get application details
            if not await self._get_app_details():
                return PhaseResult(success=False, message="Failed to get application details")
            
            # Step 2: Download application files using existing AppManager
            if not self._download_app_files():
                return PhaseResult(success=False, message="Failed to download application files")
            
            # Step 3: Analyze the application
            if not await self._analyze_application():
                return PhaseResult(success=False, message="Failed to analyze application")
            
            # Step 4: Present analysis and get user choice
            user_choice = await self._get_user_choice()
            
            # Store the choice in context for next phase
            if not hasattr(self.context, 'diagnose'):
                self.context.diagnose = {}
            self.context.diagnose['initial_choice'] = user_choice
            
            return PhaseResult(success=True, message="Application download and analysis complete")
            
        except NavigationBackRequest:
            raise
        except Exception as e:
            printer.print(f"❌ Error during download/analysis: {e}")
            return PhaseResult(success=False, message=f"Failed: {e}")
    
    async def _get_app_details(self) -> bool:
        """Get detailed information about the selected application."""
        try:
            printer.print(f"\n📋 Getting details for application '{self.context.workspace.app_name}'...")
            
            app_details = await get_application_details(
                self.context.workspace.workspace_id,
                self.context.workspace.app_id
            )
            
            if not app_details:
                printer.print("❌ Failed to get application details")
                return False
            
            # Store additional details
            self.context.workspace.app_details = app_details
            
            # Store the application ID in deployment context for consistency
            self.context.deployment.application_id = self.context.workspace.app_id
            self.context.deployment.application_name = self.context.workspace.app_name
            
            # Extract useful information
            git_ref = app_details.get('gitReference', 'main')
            language = app_details.get('language', 'Python')
            
            printer.print(f"✅ Application details retrieved")
            printer.print(f"   Language: {language}")
            printer.print(f"   Git Reference: {git_ref}")
            
            return True
            
        except Exception as e:
            printer.print(f"❌ Error getting app details: {e}")
            return False
    
    def _download_app_files(self) -> bool:
        """Download application files using the existing AppManager."""
        try:
            printer.print(f"\n📥 Downloading application files...")
            
            # Use the existing AppManager method
            extract_dir = self.app_manager.download_and_extract_app_code(
                workspace_id=self.context.workspace.workspace_id,
                application_id=self.context.workspace.app_id
            )
            
            if not extract_dir:
                printer.print("❌ Failed to download application files")
                return False
            
            # Store the directory path
            self.context.workspace.app_directory = extract_dir
            
            # List files for context
            files = []
            for root, dirs, filenames in os.walk(extract_dir):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for filename in filenames:
                    if not filename.startswith('.'):
                        rel_path = os.path.relpath(os.path.join(root, filename), extract_dir)
                        files.append(rel_path)
            
            self.context.workspace.app_files = files
            
            printer.print(f"✅ Downloaded {len(files)} files to: {extract_dir}")
            if len(files) <= 10:
                for f in files:
                    printer.print(f"   - {f}")
            else:
                # Show first few files
                for f in files[:5]:
                    printer.print(f"   - {f}")
                printer.print(f"   ... and {len(files) - 5} more files")
            
            return True
            
        except Exception as e:
            printer.print(f"❌ Error downloading files: {e}")
            return False
    
    async def _analyze_application(self) -> bool:
        """Use AI to analyze the application and understand its purpose."""
        try:
            # Check for cached analysis first
            from workflow_tools.core.working_directory import WorkingDirectory
            app_name = self.context.workspace.app_name
            analysis_file_path = WorkingDirectory.get_cached_analysis_path("diagnose", app_name)
            
            if os.path.exists(analysis_file_path):
                printer.print(f"\n📋 Found existing application analysis for '{app_name}'")

                # Read the cached analysis first to show preview
                with open(analysis_file_path, 'r', encoding='utf-8') as f:
                    cached_analysis = f.read()

                # Display preview of cached analysis
                printer.print("\n" + "─" * 50)
                printer.print_markdown(
                    cached_analysis,
                    title="📊 Cached Application Analysis Preview"
                )
                printer.print("─" * 50)
                printer.print(f"\n📁 Cache file location: {analysis_file_path}")

                printer.print("\nWould you like to use this cached analysis?")

                choices = [
                    {'name': '📂 Use cached analysis', 'value': 'cached'},
                    {'name': '🔄 Generate new analysis', 'value': 'new'}
                ]

                selected_action = select("", choices, show_border=False)

                # Use cached analysis if selected
                if selected_action == 'cached':
                    # Clear screen before continuing with cached analysis
                    clear_screen()

                    # Store and display cached analysis
                    if not hasattr(self.context, 'diagnose'):
                        self.context.diagnose = {}
                    self.context.diagnose['app_analysis'] = cached_analysis

                    printer.print("✅ Using cached application analysis.")
                    printer.print_section_header("Application Analysis (Cached)", icon="📄", style="cyan")
                    printer.print_code(cached_analysis, language="markdown")
                    return True
                else:
                    # Clear screen before fresh analysis
                    clear_screen()
                    printer.print("📥 Proceeding with fresh analysis...")
            
            printer.print(f"\n🔍 Analyzing application code...")
            
            # Prepare the prompt
            app_dir = self.context.workspace.app_directory
            
            # Create file list for analysis
            file_list = "\n".join([f"- {f}" for f in self.context.workspace.app_files[:20]])  # Limit to first 20 files
            if len(self.context.workspace.app_files) > 20:
                file_list += f"\n... and {len(self.context.workspace.app_files) - 20} more files"
            
            # Load the analysis prompt
            prompt = prompt_manager.load_task_prompt(
                "diagnose_app_analysis",
                app_name=self.context.workspace.app_name,
                app_id=self.context.workspace.app_id,
                workspace_id=self.context.workspace.workspace_id,
                app_directory=app_dir,
                file_list=file_list
            )
            
            # Read key files for analysis
            files_content = []
            
            # Try to read main application file
            for main_file in ['app.py', 'main.py', 'index.py', 'application.py']:
                main_path = os.path.join(app_dir, main_file)
                if os.path.exists(main_path):
                    with open(main_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        files_content.append(f"\n### {main_file}\n```python\n{content[:3000]}\n```")
                        if len(content) > 3000:
                            files_content.append("... (truncated)")
                    break
            
            # Read app.yaml if exists
            yaml_path = os.path.join(app_dir, 'app.yaml')
            if os.path.exists(yaml_path):
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    files_content.append(f"\n### app.yaml\n```yaml\n{content[:2000]}\n```")
                    if len(content) > 2000:
                        files_content.append("... (truncated)")
            
            # Read requirements.txt if exists
            req_path = os.path.join(app_dir, 'requirements.txt')
            if os.path.exists(req_path):
                with open(req_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    files_content.append(f"\n### requirements.txt\n```\n{content[:500]}\n```")
                    if len(content) > 500:
                        files_content.append("... (truncated)")
            
            # Combine prompt with file contents
            full_prompt = prompt + "\n\n## File Contents\n" + "\n".join(files_content)
            
            # Get AI analysis with centralized retry logic
            result = await run_agent_with_retry(
                starting_agent=self.analyzer_agent,
                input=full_prompt,
                context=self.context,
                operation_name=f"Analyzing application '{self.context.workspace.app_name}'"
            )

            if result is None:
                # All retries exhausted
                printer.print("\n💡 Tip: You can retry this workflow when the API is less busy.")
                return False

            # Extract the string output from RunResult
            response = result.final_output
            
            # Store analysis
            if not hasattr(self.context, 'diagnose'):
                self.context.diagnose = {}
            self.context.diagnose['app_analysis'] = response
            
            # Save analysis to cache
            from workflow_tools.core.working_directory import WorkingDirectory
            analysis_file_path = WorkingDirectory.get_cached_analysis_path("diagnose", app_name)
            os.makedirs(os.path.dirname(analysis_file_path), exist_ok=True)
            with open(analysis_file_path, 'w', encoding='utf-8') as f:
                f.write(response)
            printer.print(f"💾 Analysis saved to cache for future use")
            
            # Display analysis
            printer.print("\n" + "="*50)
            printer.print("APPLICATION ANALYSIS RESULTS")
            printer.print("="*50)
            printer.print(response)
            
            return True
            
        except Exception as e:
            printer.print(f"❌ Error analyzing application: {e}")
            return False
    
    async def _get_user_choice(self) -> str:
        """Get user's choice on how to proceed."""
        printer.print_section_header("Next Steps", icon="✅", style="green")
        
        # Clear screen for menu
        clear_screen()

        printer.print("What would you like to do?")
        printer.print("")

        choices = [
            {'name': '🚀 Run the application and check logs', 'value': 'run'},
            {'name': '📝 Provide additional context or requirements first', 'value': 'context'},
            {'name': '⬅️ Go back to application selection', 'value': 'back'}
        ]

        selected_action = select("", choices, show_border=False)

        if selected_action == 'back':
            # Navigate back to application selection
            self.context.navigation_request = NavigationRequest(
                target_step=DiagnoseWorkflowSteps.SELECT_APPLICATION,
                message="User requested to go back to application selection"
            )
            raise NavigationBackRequest()

        return selected_action