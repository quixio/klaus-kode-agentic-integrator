# navigation.py - Unified navigation system for workflows

from enum import IntEnum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class SinkWorkflowSteps(IntEnum):
    """Unified step indexing for sink workflow.

    Phases are at hundreds (100, 200, 300...)
    Steps within phases are increments (101, 102, 103...)
    """
    # Phase 1: Prerequisites (100)
    PREREQUISITES_START = 100
    COLLECT_REQUIREMENTS = 101
    COLLECT_APP_NAME = 102
    COLLECT_WORKSPACE = 103
    COLLECT_TOPIC = 104

    # Phase 2: Schema Analysis (200)
    SCHEMA_START = 200
    ANALYZE_SCHEMA = 201

    # Phase 3: Knowledge Gathering (300)
    KNOWLEDGE_START = 300
    GATHER_KNOWLEDGE = 301

    # Phase 4: Code Generation (400)
    GENERATION_START = 400
    GENERATE_CODE = 401

    # Phase 5: Sandbox Testing (500)
    SANDBOX_START = 500
    TEST_IN_SANDBOX = 501

    # Phase 6: Deployment (600)
    DEPLOYMENT_START = 600
    DEPLOY_APP = 601

    # Phase 7: Monitoring (700)
    MONITORING_START = 700
    MONITOR_APP = 701


class SourceWorkflowSteps(IntEnum):
    """Unified step indexing for source workflow.

    Phases are at hundreds (100, 200, 300...)
    Steps within phases are increments (101, 102, 103...)
    """
    # Phase 1: Prerequisites (100)
    PREREQUISITES_START = 100
    COLLECT_REQUIREMENTS = 101
    COLLECT_APP_NAME = 102
    COLLECT_WORKSPACE = 103

    # Phase 2: Knowledge Gathering (200)
    KNOWLEDGE_START = 200
    GATHER_KNOWLEDGE = 201

    # Phase 3: Connection Testing (300)
    CONNECTION_START = 300
    TEST_CONNECTION = 301

    # Phase 4: Schema Analysis (400)
    SCHEMA_START = 400
    ANALYZE_SCHEMA = 401

    # Phase 5: Code Generation (500)
    GENERATION_START = 500
    GENERATE_CODE = 501

    # Phase 6: Sandbox Testing (600)
    SANDBOX_START = 600
    TEST_IN_SANDBOX = 601

    # Phase 7: Deployment (700)
    DEPLOYMENT_START = 700
    DEPLOY_APP = 701

    # Phase 8: Monitoring (800)
    MONITORING_START = 800
    MONITOR_APP = 801


class DiagnoseWorkflowSteps(IntEnum):
    """Unified step indexing for diagnose workflow.

    Phases are at hundreds (100, 200, 300...)
    Steps within phases are increments (101, 102, 103...)
    """
    # Phase 1: App Selection (100)
    APP_SELECTION_START = 100
    SELECT_WORKSPACE = 101
    SELECT_APPLICATION = 102

    # Phase 2: App Download & Analysis (200)
    APP_DOWNLOAD_START = 200
    DOWNLOAD_APP = 201
    ANALYZE_APP = 202
    CHOOSE_ACTION = 203  # Run vs provide context

    # Phase 3: Edit (300)
    EDIT_START = 300
    PROVIDE_CONTEXT = 301
    CHOOSE_EDIT_OR_RUN = 302
    EDIT_CODE = 303

    # Phase 4: Sandbox Testing (400)
    SANDBOX_START = 400
    TEST_IN_SANDBOX = 401
    DEBUG_ISSUES = 402
    FOLLOW_UP_IMPROVEMENTS = 403

    # Phase 5: Deployment Sync (500)
    DEPLOYMENT_START = 500
    SELECT_DEPLOYMENT = 501
    SYNC_DEPLOYMENT = 502

    # Phase 6: Monitoring (600)
    MONITORING_START = 600
    MONITOR_DEPLOYMENT = 601


@dataclass
class NavigationRequest:
    """Request to navigate to a specific step."""
    target_step: int
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class NavigationManager:
    """Manages navigation between workflow steps."""

    def __init__(self, workflow_type: str):
        """Initialize navigation manager.

        Args:
            workflow_type: Type of workflow ('sink', 'source', or 'diagnose')
        """
        self.workflow_type = workflow_type
        self.current_step = 100  # Start at first phase

        # Get the appropriate step enum
        if workflow_type == 'sink':
            self.steps = SinkWorkflowSteps
        elif workflow_type == 'source':
            self.steps = SourceWorkflowSteps
        elif workflow_type == 'diagnose':
            self.steps = DiagnoseWorkflowSteps
        else:
            # Default to source for backward compatibility
            self.steps = SourceWorkflowSteps

    def get_phase_from_step(self, step: int) -> int:
        """Get the phase number from a step index.

        Args:
            step: Step index

        Returns:
            Phase number (100, 200, 300, etc.)
        """
        return (step // 100) * 100

    def is_phase_start(self, step: int) -> bool:
        """Check if a step is the start of a phase.

        Args:
            step: Step index

        Returns:
            True if step is a phase start
        """
        return step % 100 == 0

    def get_next_step(self) -> int:
        """Get the next step in sequence.

        Returns:
            Next step index
        """
        # Find the next valid step
        all_steps = sorted([s.value for s in self.steps])
        current_idx = all_steps.index(self.current_step)

        if current_idx < len(all_steps) - 1:
            return all_steps[current_idx + 1]
        return self.current_step  # At the end

    def get_previous_step(self) -> int:
        """Get the previous step in sequence.

        Returns:
            Previous step index
        """
        # Find the previous valid step
        all_steps = sorted([s.value for s in self.steps])
        current_idx = all_steps.index(self.current_step)

        if current_idx > 0:
            return all_steps[current_idx - 1]
        return self.current_step  # At the beginning

    def can_go_back(self) -> bool:
        """Check if we can go back from current step.

        Returns:
            True if we can go back
        """
        return self.current_step > 100

    def navigate_to(self, target_step: int) -> bool:
        """Navigate to a specific step.

        Args:
            target_step: Step to navigate to

        Returns:
            True if navigation was successful
        """
        # Validate the step exists
        if target_step in [s.value for s in self.steps]:
            self.current_step = target_step
            return True
        return False

    def get_step_name(self, step: Optional[int] = None) -> str:
        """Get human-readable name for a step.

        Args:
            step: Step index (uses current if not provided)

        Returns:
            Step name
        """
        if step is None:
            step = self.current_step

        # Find the enum member with this value
        for s in self.steps:
            if s.value == step:
                return s.name.replace('_', ' ').title()

        return f"Step {step}"