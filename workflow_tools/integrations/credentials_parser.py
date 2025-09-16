# credentials_parser.py - AI-powered dynamic connection details parsing

import json
import re
from typing import Dict, Any, Optional, Tuple
from agents import Agent, Runner
from workflow_tools.common import WorkflowContext, printer, workflow_logger

class CredentialsParser:
    """Handles AI-powered parsing of user-provided connection details."""
    
    def __init__(self, context: WorkflowContext, run_config, debug_mode: bool = False):
        self.context = context
        self.run_config = run_config
        self.debug_mode = debug_mode
        self.parser_agent = None
    
    def _create_parser_agent(self) -> Agent:
        """Create lightweight agent for parsing connection details."""
        if self.parser_agent is None:
            self.parser_agent = Agent[WorkflowContext](
                name="CredentialsParser",
                model="gpt-4o-mini",  # Use lightweight model for parsing
                instructions=(
                    "You are a connection details parser. Your task is to parse user-provided connection "
                    "details into structured JSON format. "
                    "Guidelines:\n"
                    "1. Parse comma-separated credential pairs into key-value JSON structure\n"
                    "2. Clean up formatting and standardize field names\n"
                    "3. Handle common variations (e.g., 'hostname' -> 'host', 'port_number' -> 'port')\n"
                    "4. Preserve secret key references exactly as provided\n"
                    "5. Remove any quotes or unnecessary whitespace\n"
                    "6. Return ONLY valid JSON - no explanations or additional text\n"
                    "7. If input is unclear, make reasonable assumptions and parse what you can\n"
                    "8. Convert port numbers to strings for consistency\n"
                    "9. Standardize boolean values to 'true'/'false' strings\n"
                    "10. Handle URL parsing for endpoints (separate protocol, host, port if needed)"
                ),
                tools=[],
            )
        return self.parser_agent
    
    def _create_validation_agent(self) -> Agent:
        """Create agent for validating parsed credentials against technology requirements."""
        validation_agent = Agent[WorkflowContext](
            name="CredentialsValidator",
            model="gpt-4o-mini",
            instructions=(
                "You are a connection details validator. Your task is to validate parsed connection "
                "details against technology-specific requirements. "
                "Guidelines:\n"
                "1. Analyze the destination technology and its typical connection requirements\n"
                "2. Check if required fields are present\n"
                "3. Suggest missing fields that might be needed\n"
                "4. Validate field formats (e.g., port numbers, URLs, boolean values)\n"
                "5. Provide brief feedback on completeness and correctness\n"
                "6. Return a simple assessment: 'VALID' or 'MISSING: [field1, field2]' or 'INVALID: [reason]'\n"
                "7. Be helpful but concise - focus on actionable feedback"
            ),
            tools=[],
        )
        return validation_agent
    
    def _display_connection_prompt(self, destination_technology: str) -> str:
        """Display the connection details prompt to the user."""
        prompt_message = f"""
Can you give me the connection details I need to connect to your {destination_technology}?

For example:
 - A database server might need:
   Host: host_name, Port: port_number, DBname: database_name, Table: table_name, etc.

 - A REST API might need:
   POST_endpoint: http_url, APIToken: bearer_token

 - A cloud service might need:
   Region: us-east-1, AccessKey: ACCESS_KEY_SECRET, Bucket: bucket_name

Enter these details as a comma-separated list of credential pairs.

EXAMPLE:
Host: mydbserver.com, Port: 5432, DBname: analytics, Table: sensor_data, Password: DB_PASSWORD_SECRET

⚠️ DONT enter any cleartext passwords here ⚠️ 
🗝️ Instead, use your secret key as the password value 🗝️
🗝️ IMPORTANT: Name password/secret fields with '_SECRET_KEY' suffix 🗝️
🗝️ Example: Password: DB_PASSWORD_SECRET_KEY, Token: API_TOKEN_SECRET_KEY 🗝️

Your connection details:"""
        
        return printer.input(prompt_message).strip()
    
    async def _parse_credentials_with_ai(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Parse user input using AI agent."""
        try:
            parser_agent = self._create_parser_agent()
            
            result = await Runner.run(
                starting_agent=parser_agent,
                input=f"Parse these connection details: {user_input}",
                context=self.context,
                run_config=self.run_config
            )
            
            # Extract JSON from response
            json_text = result.final_output.strip()
            
            # Try to extract JSON if it's wrapped in other text
            json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            
            # Parse JSON
            parsed_credentials = json.loads(json_text)
            
            if self.debug_mode:
                workflow_logger.debug(f"Parsed credentials: {parsed_credentials}")
            
            return parsed_credentials
            
        except json.JSONDecodeError as e:
            printer.print(f"❌ Error parsing JSON: {e}")
            return None
        except Exception as e:
            printer.print(f"❌ Error during AI parsing: {e}")
            workflow_logger.error(f"Credentials parsing error: {e}")
            return None
    
    def _display_parsed_credentials(self, parsed_credentials: Dict[str, Any]) -> bool:
        """Display parsed credentials for user confirmation."""
        printer.print("\nOK, I've turned your input into a JSON config. Can you double-check that this is the correct connection config?:")
        printer.print("")
        
        # Format JSON nicely for display
        json_output = json.dumps(parsed_credentials, indent=2)
        printer.print(json_output)
        printer.print("")
        
        from workflow_tools.common import get_user_approval
        return get_user_approval("Is this correct?")
    
    def _get_correction_input(self) -> str:
        """Get correction input from user."""
        return printer.input("What needs to be changed? Please provide the corrected details: ").strip()
    
    async def _validate_credentials(self, credentials: Dict[str, Any], destination_technology: str) -> Tuple[bool, str]:
        """Validate parsed credentials against technology requirements."""
        try:
            validation_agent = self._create_validation_agent()
            
            validation_prompt = (
                f"Validate these connection details for {destination_technology}:\n"
                f"{json.dumps(credentials, indent=2)}\n"
                f"Are these sufficient and correct for connecting to {destination_technology}?"
            )
            
            result = await Runner.run(
                starting_agent=validation_agent,
                input=validation_prompt,
                context=self.context,
                run_config=self.run_config
            )
            
            validation_result = result.final_output.strip()
            
            # Simple validation logic
            if "VALID" in validation_result.upper():
                return True, "Credentials look good!"
            else:
                return False, validation_result
                
        except Exception as e:
            workflow_logger.error(f"Validation error: {e}")
            return True, "Validation skipped due to error"  # Default to valid
    
    async def collect_dynamic_credentials(self, destination_technology: str) -> Dict[str, Any]:
        """
        Collect connection details using AI-powered dynamic parsing.
        
        Args:
            destination_technology: The technology we're connecting to
            
        Returns:
            Dictionary of parsed connection details
        """
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # Get user input
                user_input = self._display_connection_prompt(destination_technology)
                
                if not user_input:
                    printer.print("❌ No connection details provided.")
                    continue
                
                # Parse with AI
                parsed_credentials = await self._parse_credentials_with_ai(user_input)
                
                if parsed_credentials is None:
                    printer.print("❌ Failed to parse connection details. Please try again.")
                    continue
                
                # Display for confirmation
                if self._display_parsed_credentials(parsed_credentials):
                    # Validate credentials
                    is_valid, validation_message = await self._validate_credentials(
                        parsed_credentials, destination_technology
                    )
                    
                    if not is_valid:
                        printer.print(f"⚠️ Validation warning: {validation_message}")
                        from workflow_tools.common import get_user_approval
                        if not get_user_approval("Continue anyway?"):
                            continue
                    
                    printer.print("✅ Connection details confirmed!")
                    return parsed_credentials
                else:
                    # User wants to make corrections
                    correction_input = self._get_correction_input()
                    if correction_input:
                        user_input = correction_input
                        continue
                    else:
                        printer.print("❌ No corrections provided.")
                        continue
                        
            except Exception as e:
                printer.print(f"❌ Error during credential collection: {e}")
                workflow_logger.error(f"Credential collection error: {e}")
                continue
        
        printer.print("❌ Failed to collect valid connection details after maximum attempts.")
        return {}