# prompt_manager.py - External Prompt Management System

import os
from typing import Dict, Any, Optional
from workflow_tools.common import workflow_logger

class PromptManager:
    """Manages external prompt files for agents and tasks."""
    
    def __init__(self, prompts_base_dir: str = "prompts"):
        self.prompts_base_dir = prompts_base_dir
        self.agent_prompts_dir = os.path.join(prompts_base_dir, "agents")
        self.task_prompts_dir = os.path.join(prompts_base_dir, "tasks")
        
        # Create directories if they don't exist
        os.makedirs(self.agent_prompts_dir, exist_ok=True)
        os.makedirs(self.task_prompts_dir, exist_ok=True)
    
    def load_agent_instructions(self, agent_name: str) -> str:
        """Load agent instructions from external markdown file."""
        try:
            file_path = os.path.join(self.agent_prompts_dir, f"{agent_name}.md")
            
            if not os.path.exists(file_path):
                workflow_logger.warning(f"Agent instructions file not found: {file_path}")
                return f"[MISSING INSTRUCTIONS FILE: {file_path}]"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            workflow_logger.debug(f"Loaded agent instructions for {agent_name}")
            return content
            
        except Exception as e:
            workflow_logger.error(f"Error loading agent instructions for {agent_name}: {e}")
            return f"[ERROR LOADING INSTRUCTIONS: {e}]"
    
    def load_task_prompt(self, task_name: str, **kwargs) -> str:
        """Load and format task prompt from external markdown file."""
        try:
            file_path = os.path.join(self.task_prompts_dir, f"{task_name}.md")
            
            if not os.path.exists(file_path):
                workflow_logger.warning(f"Task prompt file not found: {file_path}")
                return f"[MISSING TASK PROMPT FILE: {file_path}]"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Format the prompt with provided kwargs
            if kwargs:
                try:
                    content = content.format(**kwargs)
                except KeyError as e:
                    workflow_logger.warning(f"Missing template variable in {task_name}: {e}")
                    # Return error message instead of unformatted template
                    return f"[ERROR: Failed to format prompt - missing variable: {e}]"
                except Exception as e:
                    workflow_logger.error(f"Error formatting task prompt {task_name}: {e}")
                    # Return error message instead of unformatted template
                    return f"[ERROR: Failed to format prompt - {e}]"
            
            workflow_logger.debug(f"Loaded task prompt for {task_name}")
            return content
            
        except Exception as e:
            workflow_logger.error(f"Error loading task prompt for {task_name}: {e}")
            return f"[ERROR LOADING TASK PROMPT: {e}]"
    
    def save_agent_instructions(self, agent_name: str, instructions: str) -> bool:
        """Save agent instructions to external markdown file."""
        try:
            file_path = os.path.join(self.agent_prompts_dir, f"{agent_name}.md")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(instructions)
            
            workflow_logger.info(f"Saved agent instructions for {agent_name} to {file_path}")
            return True
            
        except Exception as e:
            workflow_logger.error(f"Error saving agent instructions for {agent_name}: {e}")
            return False
    
    def save_task_prompt(self, task_name: str, prompt: str) -> bool:
        """Save task prompt to external markdown file."""
        try:
            file_path = os.path.join(self.task_prompts_dir, f"{task_name}.md")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            workflow_logger.info(f"Saved task prompt for {task_name} to {file_path}")
            return True
            
        except Exception as e:
            workflow_logger.error(f"Error saving task prompt for {task_name}: {e}")
            return False
    
    def list_agent_files(self) -> list:
        """List all available agent instruction files."""
        try:
            files = []
            if os.path.exists(self.agent_prompts_dir):
                for file in os.listdir(self.agent_prompts_dir):
                    if file.endswith('.md'):
                        files.append(file[:-3])  # Remove .md extension
            return sorted(files)
        except Exception as e:
            workflow_logger.error(f"Error listing agent files: {e}")
            return []
    
    def list_task_files(self) -> list:
        """List all available task prompt files."""
        try:
            files = []
            if os.path.exists(self.task_prompts_dir):
                for file in os.listdir(self.task_prompts_dir):
                    if file.endswith('.md'):
                        files.append(file[:-3])  # Remove .md extension
            return sorted(files)
        except Exception as e:
            workflow_logger.error(f"Error listing task files: {e}")
            return []

# Global prompt manager instance
prompt_manager = PromptManager()

# Convenience functions for easy access
def load_agent_instructions(agent_name: str) -> str:
    """Load agent instructions from external file."""
    return prompt_manager.load_agent_instructions(agent_name)

def load_task_prompt(task_name: str, **kwargs) -> str:
    """Load and format task prompt from external file."""
    return prompt_manager.load_task_prompt(task_name, **kwargs)

def save_agent_instructions(agent_name: str, instructions: str) -> bool:
    """Save agent instructions to external file."""
    return prompt_manager.save_agent_instructions(agent_name, instructions)

def save_task_prompt(task_name: str, prompt: str) -> bool:
    """Save task prompt to external file."""
    return prompt_manager.save_task_prompt(task_name, prompt)