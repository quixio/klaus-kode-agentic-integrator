# workflow_types.py - Workflow type definitions and enums

from enum import Enum
from typing import Dict, Any

class WorkflowType(Enum):
    """Enum for different workflow types."""
    SOURCE = "source"
    SINK = "sink"
    TRANSFORM = "transform"
    DIAGNOSE = "diagnose"

class WorkflowInfo:
    """Information about each workflow type."""
    
    WORKFLOW_DETAILS: Dict[WorkflowType, Dict[str, Any]] = {
        WorkflowType.SOURCE: {
            "name": "Source Workflow",
            "description": "Bring data in from another system",
            "status": "IMPLEMENTED",
            "implemented": True
        },
        WorkflowType.SINK: {
            "name": "Sink Workflow", 
            "description": "Write data out into an external system",
            "status": "IMPLEMENTED",
            "implemented": True
        },
        WorkflowType.TRANSFORM: {
            "name": "Transform Workflow",
            "description": "Process data that is already in Quix",
            "status": "TBD", 
            "implemented": False
        },
        WorkflowType.DIAGNOSE: {
            "name": "Diagnose and Update",
            "description": "Diagnose and update an existing application *experimental",
            "status": "IMPLEMENTED",
            "implemented": True
        }
    }
    
    @classmethod
    def get_display_options(cls) -> str:
        """Get formatted display options for user selection."""
        options = []
        for i, (workflow_type, info) in enumerate(cls.WORKFLOW_DETAILS.items(), 1):
            status_suffix = f" !{info['status']}" if info['status'] == "TBD" else ""
            options.append(f"{i}) {info['name']} ({info['description']}){status_suffix}")
        return "\n".join(options)
    
    @classmethod
    def get_workflow_by_choice(cls, choice: int) -> WorkflowType:
        """Get workflow type by user choice number (1-4)."""
        workflows = list(cls.WORKFLOW_DETAILS.keys())
        if 1 <= choice <= len(workflows):
            return workflows[choice - 1]
        raise ValueError(f"Invalid choice: {choice}")
    
    @classmethod
    def is_implemented(cls, workflow_type: WorkflowType) -> bool:
        """Check if a workflow type is implemented."""
        return cls.WORKFLOW_DETAILS[workflow_type]["implemented"]
    
    @classmethod
    def get_name(cls, workflow_type: WorkflowType) -> str:
        """Get the display name for a workflow type."""
        return cls.WORKFLOW_DETAILS[workflow_type]["name"]