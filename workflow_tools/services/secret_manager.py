"""Secret management service for handling Quix secrets during credential setup."""

import os
import re
from typing import Dict, List, Optional, Tuple
from workflow_tools.contexts import WorkflowContext
from workflow_tools.common import printer
from workflow_tools.integrations import quix_tools


class SecretManager:
    """Service for managing Quix secrets during environment variable collection."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        """Initialize the secret manager.
        
        Args:
            context: Workflow context containing workspace and repository information
            debug_mode: Whether to enable debug mode
        """
        self.context = context
        self.debug_mode = debug_mode
    
    async def handle_secret_variable(self, var_name: str, var_description: str = "") -> Optional[str]:
        """
        Handle a secret variable by either selecting existing secret or creating new one.
        
        Args:
            var_name: Name of the environment variable
            var_description: Description of what the variable is for
            
        Returns:
            Secret key name to use as the variable value, or None if cancelled
        """
        if not self.context.workspace.workspace_id or not self.context.workspace.repository_id:
            printer.print("❌ Error: Workspace or repository ID not available for secret management")
            return None
        
        printer.print(f"\n🔐 Secret Variable: {var_name}")
        if var_description:
            printer.print(f"   Description: {var_description}")
        
        # Check if secret already exists
        printer.print("   Checking if secret already exists...")
        
        # Ask user if they want to use existing or create new
        from workflow_tools.common import get_user_approval
        
        use_existing = get_user_approval("Does this secret already exist in your workspace?")
        
        if use_existing:
            # List existing secrets and let user choose
            secret_key = await self._select_existing_secret(var_name)
            if secret_key:
                return secret_key
            # If user cancelled, try again
            return await self.handle_secret_variable(var_name, var_description)
        else:
            # Create new secret
            secret_key = await self._create_new_secret(var_name, var_description)
            return secret_key
    
    async def _select_existing_secret(self, var_name: str) -> Optional[str]:
        """
        List existing secrets and let user select one.
        
        Args:
            var_name: Name of the environment variable
            
        Returns:
            Selected secret key name or None if cancelled
        """
        try:
            # Get available secret keys for this workspace
            secret_keys = await quix_tools.get_workspace_secret_keys(
                self.context.workspace.repository_id,
                self.context.workspace.workspace_id
            )
            
            if not secret_keys:
                printer.print("   No existing secrets found in this workspace.")
                printer.print("   Would you like to create a new secret instead?")
                return None
            
            printer.print(f"\n   Available secrets:")
            for i, key in enumerate(secret_keys, 1):
                printer.print(f"   {i}. {key}")
            
            while True:
                choice = printer.input(f"   Select secret (1-{len(secret_keys)}) or 'c' to cancel: ").strip().lower()
                
                if choice == 'c':
                    return None
                
                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(secret_keys):
                        selected_key = secret_keys[choice_idx]
                        printer.print(f"   ✅ Selected existing secret: {selected_key}")
                        return selected_key
                    else:
                        printer.print(f"   Invalid choice. Please enter 1-{len(secret_keys)} or 'c' to cancel.")
                except ValueError:
                    printer.print(f"   Invalid input. Please enter a number 1-{len(secret_keys)} or 'c' to cancel.")
                    
        except Exception as e:
            import traceback
            if self.debug_mode:
                printer.print(f"   ❌ Debug: Full error traceback:")
                printer.print(traceback.format_exc())
            printer.print(f"   ❌ Error listing secrets: {e}")
            printer.print("   Proceeding to create a new secret instead.")
            return None
    
    async def _create_new_secret(self, var_name: str, var_description: str = "") -> Optional[str]:
        """
        Create a new secret with user-provided value.
        
        Args:
            var_name: Name of the environment variable
            var_description: Description of what the variable is for
            
        Returns:
            New secret key name or None if cancelled
        """
        printer.print(f"\n   Creating new secret for {var_name}")
        
        # Get the secret value from user (securely, without showing characters)
        secret_value = printer.secure_input("   Enter the secret value: ").strip()
        if not secret_value:
            printer.print("   ❌ Secret value cannot be empty.")
            return None
        
        # Generate a sensible secret key name
        suggested_key = self._generate_secret_key_name(var_name)
        custom_key = printer.input(f"   Secret key name (default: {suggested_key}): ").strip()
        secret_key = custom_key if custom_key else suggested_key
        
        # Ask about scoping (repository vs workspace)
        from workflow_tools.core.questionary_utils import select
        
        scope_choices = [
            {'name': '🌐 Repository-scoped (accessible from all workspaces)', 'value': 'repository'},
            {'name': '📁 Workspace-scoped (this workspace only)', 'value': 'workspace'}
        ]
        
        scope_choice = select("Select secret scope:", scope_choices, show_border=True)
        
        if scope_choice == 'repository':
            repository_scoped = True
            printer.print(f"   Creating repository-scoped secret: {secret_key}")
        else:
            repository_scoped = False
            printer.print(f"   Creating workspace-scoped secret: {secret_key}")
        
        try:
            # Create the secret
            success = await quix_tools.create_secret(
                self.context.workspace.repository_id,
                self.context.workspace.workspace_id,
                secret_key,
                secret_value,
                repository_scoped
            )
            
            if success:
                scope_text = "repository" if repository_scoped else "workspace"
                printer.print(f"   ✅ Successfully created {scope_text}-scoped secret: {secret_key}")
                return secret_key
            else:
                printer.print(f"   ❌ Failed to create secret: {secret_key}")
                return None
                
        except Exception as e:
            printer.print(f"   ❌ Error creating secret: {e}")
            return None
    
    def _generate_secret_key_name(self, var_name: str) -> str:
        """
        Generate a sensible secret key name from the variable name.
        
        Args:
            var_name: Original variable name
            
        Returns:
            Suggested secret key name
        """
        # Clean up the variable name
        clean_name = var_name.upper()
        
        # Remove common suffixes that might be redundant
        suffixes_to_remove = ['_KEY', '_SECRET', '_TOKEN', '_PASSWORD']
        for suffix in suffixes_to_remove:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)]
                break
        
        # Add technology context if available
        tech_name = None
        from workflow_tools.workflow_types import WorkflowType
        if self.context.selected_workflow == WorkflowType.SOURCE:
            tech_name = getattr(self.context.technology, 'source_technology', None) or self.context.technology.destination_technology
        else:
            tech_name = self.context.technology.destination_technology
        
        if tech_name:
            # Clean tech name
            tech_clean = re.sub(r'[^a-zA-Z0-9]', '_', tech_name.upper())
            # Add tech prefix if not already present
            if not clean_name.startswith(tech_clean):
                clean_name = f"{tech_clean}_{clean_name}"
        
        # Ensure it ends with an appropriate suffix
        if not any(clean_name.endswith(suffix) for suffix in ['_KEY', '_SECRET', '_TOKEN', '_PASSWORD']):
            # Determine appropriate suffix based on variable name
            var_lower = var_name.lower()
            if 'password' in var_lower:
                clean_name += '_PASSWORD'
            elif 'token' in var_lower:
                clean_name += '_TOKEN'
            elif 'secret' in var_lower:
                clean_name += '_SECRET'
            else:
                clean_name += '_KEY'
        
        return clean_name
    
    def is_secret_variable(self, var_name: str) -> bool:
        """
        Determine if a variable should be treated as a secret.
        
        Args:
            var_name: Variable name to check
            
        Returns:
            True if the variable should be treated as a secret
        """
        var_lower = var_name.lower()
        secret_terms = ['password', 'secret', 'token', 'key', 'auth', 'credential']
        return any(term in var_lower for term in secret_terms)