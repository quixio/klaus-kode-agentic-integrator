# credential_mapper.py - Dynamic credential field mapping utilities

import re
from typing import Dict, List, Optional, Tuple
from workflow_tools.common import workflow_logger

class CredentialFieldMapper:
    """Handles mapping between dynamic credential field names and standard field types."""
    
    # Standard field mappings with common variations
    FIELD_MAPPINGS = {
        'host': ['host', 'hostname', 'server', 'address', 'endpoint', 'url'],
        'port': ['port', 'port_number', 'portnumber', 'service_port'],
        'database': ['database', 'db', 'dbname', 'db_name', 'schema', 'service'],
        'user': ['user', 'username', 'userid', 'user_id', 'login', 'account'],
        'password_secret_key': ['password', 'password_secret_key', 'secret', 'token', 'api_key', 'key'],
        'table_name': ['table', 'table_name', 'tablename'],
        'region': ['region', 'aws_region', 'location'],
        'bucket': ['bucket', 'bucket_name', 'container'],
        'access_key': ['access_key', 'accesskey', 'access_key_id', 'key_id'],
        'secret_key': ['secret_key', 'secretkey', 'secret_access_key'],
        'api_key': ['api_key', 'apikey', 'key', 'token'],
        'auth_token': ['auth_token', 'token', 'bearer_token', 'access_token'],
        'ssl': ['ssl', 'use_ssl', 'enable_ssl', 'secure'],
        'timeout': ['timeout', 'connection_timeout', 'request_timeout'],
        'protocol': ['protocol', 'scheme'],
        'path': ['path', 'base_path', 'endpoint_path'],
    }
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
    
    def normalize_field_name(self, field_name: str) -> str:
        """Normalize field name by removing special characters and converting to lowercase."""
        if not field_name:
            return ""
        
        # Remove special characters and convert to lowercase
        normalized = re.sub(r'[^a-zA-Z0-9_]', '', field_name.lower())
        return normalized
    
    def find_standard_field_type(self, field_name: str) -> Optional[str]:
        """Find the standard field type for a given field name."""
        normalized_name = self.normalize_field_name(field_name)
        
        # Direct match first
        for standard_type, variations in self.FIELD_MAPPINGS.items():
            if normalized_name in [self.normalize_field_name(var) for var in variations]:
                return standard_type
        
        # Fuzzy matching for partial matches
        for standard_type, variations in self.FIELD_MAPPINGS.items():
            for variation in variations:
                normalized_variation = self.normalize_field_name(variation)
                if normalized_name in normalized_variation or normalized_variation in normalized_name:
                    return standard_type
        
        return None
    
    def map_credentials_to_standard(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """Map dynamic credential field names to standard field types."""
        standard_credentials = {}
        unmapped_fields = {}
        
        for field_name, value in credentials.items():
            standard_type = self.find_standard_field_type(field_name)
            
            if standard_type:
                # If we already have a value for this standard type, keep the first one
                if standard_type not in standard_credentials:
                    standard_credentials[standard_type] = value
                    if self.debug_mode:
                        workflow_logger.debug(f"Mapped '{field_name}' -> '{standard_type}' = '{value}'")
                else:
                    if self.debug_mode:
                        workflow_logger.debug(f"Duplicate mapping for '{standard_type}': '{field_name}' (ignored)")
            else:
                # Keep unmapped fields as-is
                unmapped_fields[field_name] = value
                if self.debug_mode:
                    workflow_logger.debug(f"Unmapped field kept: '{field_name}' = '{value}'")
        
        # Include unmapped fields in the result
        standard_credentials.update(unmapped_fields)
        
        return standard_credentials
    
    def get_credential_value(self, credentials: Dict[str, str], target_field: str) -> Optional[str]:
        """Get credential value for a target field, trying standard mapping first."""
        # Try direct match first
        if target_field in credentials:
            return credentials[target_field]
        
        # Try to find through standard mapping
        standard_credentials = self.map_credentials_to_standard(credentials)
        return standard_credentials.get(target_field)
    
    def get_environment_variable_mapping(self, credentials: Dict[str, str], 
                                       destination_technology: str) -> Dict[str, str]:
        """
        Create environment variable mapping for deployment.
        
        Args:
            credentials: Dynamic credential dictionary
            destination_technology: The technology name for env var prefixing
            
        Returns:
            Dictionary mapping environment variable names to credential values
        """
        env_vars = {}
        tech_prefix = destination_technology.upper().replace(' ', '_').replace('-', '_')
        
        # Map credentials to standard types
        standard_credentials = self.map_credentials_to_standard(credentials)
        
        # Create environment variables for standard fields
        for standard_field, value in standard_credentials.items():
            env_var_name = f"{tech_prefix}_{standard_field.upper()}"
            env_vars[env_var_name] = value
        
        return env_vars
    
    def get_credential_display_info(self, credentials: Dict[str, str]) -> List[Tuple[str, str, str]]:
        """
        Get formatted credential information for display using exact field names.
        
        Returns:
            List of tuples (display_name, field_name, value)
        """
        display_info = []
        
        # Use exact field names provided by user, not standardized ones
        for field_name, value in credentials.items():
            display_name = field_name.replace('_', ' ').title()
            display_info.append((display_name, field_name, value))
        
        return display_info
    
    def validate_required_fields(self, credentials: Dict[str, str], 
                                required_fields: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that required fields are present in credentials.
        
        Args:
            credentials: Dynamic credential dictionary
            required_fields: List of required standard field names
            
        Returns:
            Tuple of (is_valid, missing_fields)
        """
        standard_credentials = self.map_credentials_to_standard(credentials)
        missing_fields = []
        
        for required_field in required_fields:
            if required_field not in standard_credentials or not standard_credentials[required_field]:
                missing_fields.append(required_field)
        
        return len(missing_fields) == 0, missing_fields