"""AI-powered log analyzer service for determining test execution success/failure."""

import os
import json
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from agents import Agent, Runner, RunConfig, ModelSettings
from agents.extensions.models.litellm_model import LitellmModel
from workflow_tools.contexts import WorkflowContext
from workflow_tools.common import printer
from workflow_tools.core.prompt_manager import PromptManager
from workflow_tools.services.model_utils import create_agent_with_model_config


@dataclass
class LogAnalysisResult:
    """Result from AI log analysis."""
    success: bool
    confidence: str  # 'high', 'medium', 'low'
    reasoning: str
    key_indicators: list[str]
    recommendation: Optional[str] = None


class LogAnalyzer:
    """AI-powered service for analyzing execution logs to determine success/failure."""
    
    def __init__(self, context: WorkflowContext, debug_mode: bool = False):
        """Initialize the log analyzer.
        
        Args:
            context: Workflow context
            debug_mode: Whether to enable debug mode
        """
        self.context = context
        self.debug_mode = debug_mode
        self.run_config = RunConfig(workflow_name="Log Analysis")
    
    async def analyze_execution_logs(
        self, 
        logs: str, 
        test_objective: str,
        workflow_type: str = "sink",
        code_context: Optional[str] = None,
        is_connection_test: bool = False
    ) -> LogAnalysisResult:
        """Analyze execution logs using AI to determine success/failure.
        
        Args:
            logs: The execution logs to analyze
            test_objective: What the test was trying to achieve
            workflow_type: Either "sink" or "source"
            code_context: Optional code that was executed (for better context)
            is_connection_test: Whether this is a connection test (vs main code)
            
        Returns:
            LogAnalysisResult with success determination and reasoning
        """
        # Create the log analyzer agent using GPT-5 for its large context window
        # Using a more powerful model as requested in the issue
        agent = self._create_log_analyzer_agent()
        
        # Get the original generation prompt from context
        original_prompt = None
        if is_connection_test:
            original_prompt = getattr(self.context.code_generation, 'last_connection_test_prompt', None)
        else:
            original_prompt = getattr(self.context.code_generation, 'last_generation_prompt', None)
        
        # Prepare the analysis prompt
        analysis_prompt = self._prepare_analysis_prompt(
            logs=logs,
            test_objective=test_objective,
            workflow_type=workflow_type,
            code_context=code_context,
            original_prompt=original_prompt
        )
        
        if self.debug_mode:
            printer.print_debug(f"📊 Analyzing logs with AI (objective: {test_objective[:100]}...)")
        
        try:
            # Run the agent to analyze the logs
            result = await Runner.run(
                starting_agent=agent,
                input=analysis_prompt,
                context=self.context,
                run_config=self.run_config
            )
            
            # Parse the structured response
            return self._parse_analysis_response(result.final_output)
            
        except Exception as e:
            printer.print_debug(f"⚠️ Error in AI log analysis: {e}")
            # Fall back to uncertain if AI analysis fails
            return LogAnalysisResult(
                success=False,
                confidence='low',
                reasoning=f"AI analysis failed: {str(e)}",
                key_indicators=[],
                recommendation="Manual review recommended"
            )
    
    def _create_log_analyzer_agent(self) -> Agent[WorkflowContext]:
        """Create the log analyzer agent.
        
        Returns:
            Configured agent for log analysis
        """
        # Load the agent prompt from external file
        instructions = PromptManager().load_agent_instructions("LogAnalyzerAgent")
        
        # Use centralized agent creation with GPT-5 configuration
        return create_agent_with_model_config(
            agent_name="LogAnalyzerAgent",
            task_type="log_analysis",
            workflow_type="both",  # Log analysis is used by both sink and source
            instructions=instructions,
            context_type=WorkflowContext
        )
    
    def _prepare_analysis_prompt(
        self,
        logs: str,
        test_objective: str,
        workflow_type: str,
        code_context: Optional[str],
        original_prompt: Optional[str] = None
    ) -> str:
        """Prepare the prompt for log analysis.
        
        Args:
            logs: Execution logs
            test_objective: What the test aimed to achieve
            workflow_type: Type of workflow
            code_context: Optional code context
            original_prompt: Original code generation prompt
            
        Returns:
            Formatted prompt for the agent
        """
        # Apply sandwich approach only if logs exceed 10,000 characters
        if len(logs) > 10000:
            # Take first 5000 and last 5000 characters
            logs_processed = (
                logs[:5000] + 
                f"\n\n... [TRUNCATED {len(logs) - 10000} characters from middle] ...\n\n" + 
                logs[-5000:]
            )
        else:
            # If logs are 10,000 chars or less, use them as-is
            logs_processed = logs
        
        prompt = f"""Analyze these execution logs to determine if the test was successful.

TEST OBJECTIVE:
{test_objective}

WORKFLOW TYPE: {workflow_type}

"""
        
        if original_prompt:
            # Include the original generation prompt for full context
            prompt += f"""ORIGINAL CODE GENERATION INSTRUCTIONS:
{original_prompt[:10000]}  # Truncate if extremely long

"""
        
        if code_context:
            # Include relevant code context if available
            prompt += f"""CODE THAT WAS EXECUTED:
```python
{code_context[:5000]}  # Truncate if too long
```

"""
        
        prompt += f"""EXECUTION LOGS:
{logs_processed}

Please analyze these logs and determine:
1. Was the test successful? (YES/NO)
2. What is your confidence level? (HIGH/MEDIUM/LOW)
3. What key indicators led to your conclusion?
4. Provide a brief reasoning for your determination
5. If unsuccessful, what recommendation do you have?

IMPORTANT: You must provide a structured JSON response with the following format:
{{
    "success": true/false,
    "confidence": "high/medium/low",
    "reasoning": "Brief explanation of your determination",
    "key_indicators": ["indicator1", "indicator2", ...],
    "recommendation": "Optional recommendation if test failed"
}}

Focus on understanding the actual behavior, not just looking for error keywords. For example:
- If data was successfully retrieved/processed, it's likely successful even without explicit success messages
- If the code achieved its objective (e.g., fetched data, connected to service), consider it successful
- Look for patterns indicating normal operation vs actual failures
"""
        
        return prompt
    
    def _parse_analysis_response(self, response: str) -> LogAnalysisResult:
        """Parse the agent's response into a structured result.
        
        Args:
            response: The agent's response
            
        Returns:
            Parsed LogAnalysisResult
        """
        try:
            # Try to extract JSON from the response
            # Handle cases where the response might have markdown formatting
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            
            # Parse the JSON response
            data = json.loads(json_str)
            
            return LogAnalysisResult(
                success=bool(data.get("success", False)),
                confidence=data.get("confidence", "low"),
                reasoning=data.get("reasoning", "No reasoning provided"),
                key_indicators=data.get("key_indicators", []),
                recommendation=data.get("recommendation")
            )
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            if self.debug_mode:
                printer.print_debug(f"⚠️ Failed to parse structured response: {e}")
                printer.print_debug(f"Raw response: {response[:500]}")
            
            # Try to extract success/failure from unstructured response
            response_lower = response.lower()
            success = "successful" in response_lower or "succeeded" in response_lower
            
            return LogAnalysisResult(
                success=success,
                confidence='low',
                reasoning=response[:500] if len(response) > 500 else response,
                key_indicators=[],
                recommendation="Manual review recommended due to response parsing issues"
            )
    
