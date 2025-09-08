"""Utility functions for model configuration and agent creation.

These utilities were extracted from the deprecated CodeGeneratorService
and are still used by debug_analyzer and log_analyzer.
"""

import os
from agents import Agent, ModelSettings
from agents.extensions.models.litellm_model import LitellmModel
from workflow_tools.contexts import WorkflowContext
from workflow_tools.common import printer
from workflow_tools.core.config_loader import ConfigLoader

config = ConfigLoader()


def create_model_settings(model_name: str, temperature: float) -> ModelSettings:
    """
    Create ModelSettings with temperature handling for different model types.
    
    Args:
        model_name: Name of the model (e.g., "gpt-5-mini", "gpt-4o")
        temperature: Temperature value to use (ignored for GPT-5 models)
    
    Returns:
        ModelSettings instance with appropriate parameters
    """
    if model_name.startswith("gpt-5"):
        printer.print(f"⚠️ {model_name} detected: omitting temperature parameter")
        return ModelSettings()
    else:
        return ModelSettings(temperature=temperature)


def create_agent_with_model_config(agent_name: str, 
                                  task_type: str, 
                                  workflow_type: str,
                                  instructions: str,
                                  context_type=WorkflowContext) -> Agent:
    """Centralized agent creation with proper model configuration handling.
    
    This utility function handles the logic for choosing between direct OpenAI API calls
    and LiteLLM wrapper based on the model configuration.
    
    Args:
        agent_name: Name of the agent
        task_type: Task type for model config lookup (e.g., 'code_generation')
        workflow_type: Workflow type for model config lookup (e.g., 'sink', 'source')
        instructions: Agent instructions/prompt
        context_type: Context type for the agent (defaults to WorkflowContext)
    
    Returns:
        Configured Agent instance
    """
    # Get model configuration
    model_config = config.get_model_config(task_type, workflow_type)
    
    # Get temperature from config (default to 0.3 if not specified)
    temperature = 0.3  # Default
    models_config = config.load_models_config()
    if 'parameters' in models_config and 'temperature' in models_config['parameters']:
        temperature = models_config['parameters']['temperature'].get(task_type, 0.3)
    
    # Log the temperature and model being used
    printer.print(f"🌡️ Using temperature {temperature} for {agent_name}")
    printer.print(f"   Model: {model_config.get('provider', 'openai')}/{model_config.get('model', 'gpt-4o')}")
    
    # Extract model configuration
    bypass_litellm = model_config.get("bypass_litellm", False)
    provider = model_config.get("provider", "openai")
    model_name = model_config.get("model", "gpt-4o")
    
    # Log the model configuration being used
    printer.print(f"🔧 Model config: provider={provider}, bypass_litellm={bypass_litellm}")
    
    if provider == "openai" and bypass_litellm:
        # Legacy path: Direct OpenAI API call (kept for backward compatibility)
        # Note: This requires a real OPENAI_API_KEY which we no longer use
        printer.print(f"⚠️ Warning: Legacy OpenAI direct API path for {model_name}")
        printer.print(f"   Consider updating config to use provider: anthropic")
        
        # Create model settings with centralized temperature handling
        model_settings = create_model_settings(model_name, temperature)
        
        # Add GPT-5 specific parameters if needed
        if model_name.startswith("gpt-5"):
            verbosity = model_config.get("verbosity")
            reasoning = model_config.get("reasoning") 
            
            if verbosity:
                printer.print(f"🔧 GPT-5 verbosity: {verbosity}")
                # Add verbosity to model settings - this will need to be passed to the API call
                model_settings.extra_body = model_settings.extra_body or {}
                model_settings.extra_body["text"] = {"verbosity": verbosity}
            
            if reasoning:
                printer.print(f"🧠 GPT-5 reasoning: {reasoning}")
                # Add reasoning to model settings - this will need to be passed to the API call  
                model_settings.extra_body = model_settings.extra_body or {}
                model_settings.extra_body["reasoning"] = {"effort": reasoning}
        
        return Agent[context_type](
            name=agent_name,
            model=model_name,
            model_settings=model_settings,
            instructions=instructions,
        )
    elif provider == "anthropic" or not bypass_litellm:
        # Use LiteLLM wrapper for Anthropic or other providers
        if provider == "anthropic":
            printer.print(f"🌐 Using LiteLLM wrapper for Anthropic model: {model_name}")
            api_key = os.getenv("ANTHROPIC_API_KEY")
            litellm_model_name = f"anthropic/{model_name}"
        else:
            printer.print(f"🌐 Using LiteLLM wrapper for {provider} model: {model_name}")
            # For other providers, use appropriate API key and model format
            api_key = os.getenv(f"{provider.upper()}_API_KEY")
            litellm_model_name = f"{provider}/{model_name}"
        
        # Create model settings with centralized temperature handling
        model_settings = create_model_settings(model_name, temperature)
        
        return Agent[context_type](
            name=agent_name,
            model=LitellmModel(
                model=litellm_model_name,
                api_key=api_key,
            ),
            model_settings=model_settings,
            instructions=instructions,
        )
    else:
        # Fallback to Anthropic via LiteLLM for any unconfigured cases
        printer.print(f"🔄 Fallback to Anthropic (claude-3-5-haiku-latest) for {model_name}")
        
        # Create model settings with centralized temperature handling
        model_settings = create_model_settings("claude-3-5-haiku-latest", temperature)
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        return Agent[context_type](
            name=agent_name,
            model=LitellmModel(
                model="anthropic/claude-3-5-haiku-latest",
                api_key=api_key,
            ),
            model_settings=model_settings,
            instructions=instructions,
        )