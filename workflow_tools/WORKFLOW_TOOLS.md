# Workflow Tools Directory Documentation

## Overview

The `workflow_tools/` directory contains the core implementation of the Quix Coding Agent's workflow system. This modular architecture supports both **Sink** (data out) and **Source** (data in) workflows through a clean, inheritance-based design following SOLID principles.

## Directory Structure

```
workflow_tools/
├── 📁 core/              # Core utilities and management
├── 📁 integrations/      # External system integrations
├── 📁 phases/           # Workflow phase implementations
├── 📁 services/         # Service layer implementations
├── 📁 legacy_unused/    # Deprecated/legacy files
├── 📄 Root level files  # Configuration and utilities
```

## 📁 Core Directory (`core/`)

**Purpose**: Central utilities, configuration, and management systems.

| File | Purpose | Key Functionality |
|------|---------|-------------------|
| `config_loader.py` | Configuration management | YAML config loading, environment variable handling |
| `error_handler.py` | Error handling utilities | Custom exceptions, error recovery |
| `interfaces.py` | Service contracts | Abstract interfaces for dependency injection |
| `logger_service.py` | Logging infrastructure | Structured logging, workflow printer |
| `placeholder_workflows.py` | Future workflow types | Placeholders for transform/diagnosis workflows |
| `prompt_manager.py` | AI prompt management | External prompt loading from markdown files |
| `triage_agent.py` | Workflow selection | AI-powered workflow type determination |
| `url_builder.py` | Quix Portal URL builder | Constructs clickable URLs for Quix resources |

## 📁 Integrations Directory (`integrations/`)

**Purpose**: External system integrations and API clients.

| File | Purpose | Key Functionality |
|------|---------|-------------------|
| `credential_mapper.py` | Credential mapping | Maps user inputs to environment variables |
| `credentials_parser.py` | Credential parsing | Parses and validates connection credentials |
| `deployment_monitoring.py` | Deployment monitoring | Health checks, performance monitoring |
| `quix_tools.py` | Quix Platform API | Complete Quix Platform API client |

### `quix_tools.py` - Core Integration
- **Workspace Management**: List workspaces, get details
- **Topic Operations**: Create, list, manage Kafka topics
- **Application Lifecycle**: Create, deploy, manage applications
- **Session Management**: IDE session creation and management
- **Library Integration**: Search and use Quix Library templates

## 📁 Phases Directory (`phases/`)

**Purpose**: Implementation of all workflow phases using the Template Method pattern.

### 📁 Base (`phases/base/`)
Foundation class for all workflow phases.

| File | Purpose | Key Functionality |
|------|---------|-------------------|
| `base_phase.py` | Abstract base class | Template Method pattern, lifecycle management, error handling, retry logic, navigation support via `NavigationBackRequest` |

### 📁 Shared (`phases/shared/`)
Phases and knowledge management components used by both sink and source workflows.

| File | Purpose | Key Functionality |
|------|---------|-------------------|
| `phase_deployment.py` | Application deployment | Production deployment, resource configuration |
| `phase_monitoring.py` | Post-deployment monitoring | Health checks, performance monitoring |
| `app_management.py` | Application management | Create apps from templates, session management |
| `cache_utils.py` | Caching utilities | Template selection caching, performance optimization, navigation support for cached prompts |
| `env_var_management.py` | Environment variables | AI-powered env var translation and collection |
| `template_selection.py` | Template selection | Fixed starter template selection (`starter-source`, `starter-destination`) with navigation support |

### 📁 Sink (`phases/sink/`)
Phases specific to sink workflows (data out to external systems).

| File | Purpose | Key Functionality |
|------|---------|-------------------|
| `phase_sink_prerequisites.py` | Prerequisites collection | Workspace, topic, destination system setup |
| `phase_sink_schema.py` | Schema analysis | Analyze incoming data schema from topics |
| `phase_sink_knowledge.py` | Knowledge gathering | Fixed starter template selection, documentation gathering |
| `phase_sink_generation.py` | Code generation | AI-powered sink code generation using Claude Code SDK |
| `phase_sink_sandbox.py` | Sandbox testing | Test generated code in isolated environment (uses QuixStreams with built-in stop conditions), enhanced with Claude Code debugging (up to 50 turns) |

**Sink Workflow Flow**:
1. Prerequisites → 2. Schema Analysis → 3. Knowledge Gathering → 4. Code Generation → 5. Sandbox Testing → 6. Deployment → 7. Monitoring

### 📁 Source (`phases/source/`)
Phases specific to source workflows (data in from external systems).

| File | Purpose | Key Functionality |
|------|---------|-------------------|
| `phase_source_prerequisites.py` | Prerequisites collection | Workspace setup, external system configuration |
| `phase_source_schema.py` | Schema definition | Define output data schema |
| `phase_source_knowledge.py` | Knowledge gathering | Fixed starter template selection using unified `KnowledgeGatheringService` |
| `phase_source_generation.py` | Code generation | AI-powered source code generation using Claude Code SDK |
| `phase_source_connection_testing.py` | Connection testing | Test external system connectivity (uses timeout-based execution) |
| `phase_source_sandbox.py` | Sandbox testing | Test generated code with forced termination after 30s (sources may not have built-in stop conditions), enhanced with Claude Code debugging |

**Source Workflow Flow**:
1. Prerequisites → 2. Schema Definition → 3. Knowledge Gathering → 4. Code Generation → 5. Connection Testing → 6. Sandbox Testing → 7. Deployment → 8. Monitoring

#### Important Architectural Difference: Sink vs Source Execution
- **Sink workflows**: Always use QuixStreams library with built-in stop conditions (`app.run(seconds=30)`), ensuring clean termination
- **Source workflows**: Use various external libraries (SSE, webhooks, polling) that may run indefinitely, requiring forced termination after log collection

## 📁 Services Directory (`services/`)

**Purpose**: Service layer implementations following dependency injection patterns.

| File | Purpose | Key Functionality |
|------|---------|-------------------|
| `claude_code_service.py` | Claude Code SDK integration | Claude Sonnet wrapper, streaming responses, code generation and debugging with up to 50 turns, cost-optimized |
| `code_generator.py` | Code generation service | AI model management with temperature control (0.1 for code), centralized generation for legacy workflows |
| `data_specification_collector.py` | Data specification service | Collects user requirements for targeted data retrieval/sinking |
| `debug_analyzer.py` | Debug analysis service | AI-powered error analysis and fixing |
| `dependency_parser.py` | Dependency parsing | Extract Python dependencies from code |
| `file_manager.py` | File management service | File operations, artifact management |
| `knowledge_gatherer.py` | Unified knowledge service | Centralized knowledge gathering for workflows with fixed starter templates |
| `log_analyzer.py` | AI log analysis service | AI-powered execution log analysis with confidence scoring |
| `prerequisites_collector.py` | Prerequisites service | Unified prerequisites collection for both workflows |
| `requirements_updater.py` | Requirements management | Automatic package version updates, QuixStreams version sync |
| `sandbox_error_handler.py` | Error handling service | Centralized error detection with `determine_execution_status()` - handles critical errors, exit codes, and success indicators |

## Root Level Files

| File | Purpose | Key Functionality |
|------|---------|-------------------|
| `__init__.py` | Package initialization | Exports main classes and functions |
| `common.py` | Common utilities | Shared utilities, user interaction helpers |
| `contexts.py` | Context management | Workflow state management with sub-contexts |
| `exceptions.py` | Custom exceptions | Domain-specific exception hierarchy including `NavigationBackRequest` for workflow navigation |
| `service_container.py` | Dependency injection | Service container for dependency management |
| `workflow_factory.py` | Workflow creation | Factory pattern for workflow instantiation |
| `workflow_types.py` | Type definitions | Enums and type definitions |

### Context Architecture (`contexts.py`)

The context system uses a **clean separation of concerns**:

```python
@dataclass
class WorkflowContext:
    workspace: WorkspaceContext        # Workspace/topic information
    technology: TechnologyContext      # Technology selection and templates
    schema: SchemaContext             # Data schema information
    code_generation: CodeGenerationContext  # Code generation artifacts
    deployment: DeploymentContext     # Application deployment details
    credentials: CredentialsContext   # Credentials and environment variables
```

## 📁 Legacy/Unused Directory (`legacy_unused/`)

**Purpose**: Deprecated files kept for reference during refactoring.

| File | Status | Notes |
|------|--------|-------|
| `common_refactored.py` | ⚠️ Deprecated | Old context structure, replaced by `contexts.py` |
| `phase_source_knowledge.py` | ⚠️ Deprecated | Old implementation before unified service refactoring. Current active version at `phases/source/phase_source_knowledge.py` uses the unified `KnowledgeGatheringService` |
| `service_factory.py` | ⚠️ Deprecated | Partial service factory implementation |

## Architecture Principles

### 1. **Clean Code Architecture** ✅
- **Single Responsibility**: Each class has one clear purpose
- **Open/Closed**: Extensible through inheritance
- **Dependency Inversion**: Depends on abstractions, not concretions
- **Template Method Pattern**: BasePhase defines the algorithm structure

### 2. **Phase Inheritance Hierarchy** ✅
```python
BasePhase (Abstract)
├── SinkPrerequisitesCollectionPhase
├── SinkSchemaPhase
├── SinkGenerationPhase
├── SourcePrerequisitesCollectionPhase
├── SourceGenerationPhase
├── DeploymentPhase
└── MonitoringPhase
```

### 3. **Standardized Phase Interface** ✅
Every phase follows this pattern:
```python
class MyPhase(BasePhase):
    phase_name = "my_phase"
    phase_description = "Description"
    
    async def execute(self) -> PhaseResult:
        # Core business logic here
        return PhaseResult(success=True, message="Completed")
```

### 4. **Context-Driven Design** ✅
- All state flows through strongly-typed context objects
- No global state or singletons
- Clear data ownership and lifecycle

### 5. **Service Layer Pattern** ✅
- Business logic separated from infrastructure
- Dependency injection through service container
- Testable and mockable service interfaces

## Key Features

### 🔄 **Workflow Navigation**
- **Back Navigation Support**: Users can navigate back to previous phases to modify selections
- **NavigationBackRequest Exception**: Custom exception for handling navigation requests
- **Cache Integration**: Navigation preserves cached template selections and user inputs
- **Multi-Step Phase Navigation**: Internal navigation within complex phases
- **Context Preservation**: Workflow state maintained during navigation transitions

### 🤖 **AI-Powered Code Generation**
- **Primary**: Claude Code SDK using Claude Sonnet for cost-optimized code generation and debugging (up to 50 turns)
- **Secondary**: OpenAI Agents SDK for workflow orchestration
- Specialized agents for different tasks (schema analysis, code generation, debugging, external technology preparation, log analysis)
- External prompt management from markdown files (15 agents including LogAnalyzerAgent)
- Temperature control: 0.1 for deterministic code generation

### 🔄 **Multi-Model AI Support**
- **Claude Sonnet**: Primary code generation via Claude Code SDK (cost-optimized)
- **Claude Opus 4.1**: Legacy code generation with GPT-4o fallback
- **GPT-4o**: Schema analysis and template matching
- **GPT-5**: Error debugging and log analysis (with GPT-4o fallback)

### 📚 **Comprehensive Documentation Integration**
- Built-in Quix Streams documentation
- Template-specific documentation
- Fixed starter template selection

### 🧪 **Sandbox Testing Environment**
- Isolated testing before production deployment
- Automatic dependency detection and installation
- Error debugging with AI assistance

### 🚀 **Production Deployment**
- Seamless deployment to Quix Platform
- Resource configuration (CPU, memory, replicas)
- Health monitoring and alerting

### 🔧 **Claude Code SDK Integration**
- **ClaudeCodeService**: Wrapper for Claude Code SDK operations (`workflow_tools/services/claude_code_service.py`)
- **Model**: Claude Sonnet for cost optimization (previously used Claude Opus)
- **Streaming Responses**: Real-time feedback during code generation
- **Multi-file Updates**: Updates main.py, app.yaml, requirements.txt, and .env files
- **Environment Variables**: Post-generation extraction from updated app.yaml
- **Debugging Support**: Integrated error analysis and code fixing with up to 50 turns
- **Feedback Loop**: Iterative refinement with user approval
- **Working Directory**: Operates from main workflow directory with relative path handling
- **Cost Savings**: ~80% reduction in API costs compared to Claude Opus

## Usage Patterns

### Creating a New Phase
```python
from workflow_tools.phases.base.base_phase import BasePhase, PhaseResult

class MyNewPhase(BasePhase):
    phase_name = "my_new_phase"
    phase_description = "My custom phase"
    
    async def execute(self) -> PhaseResult:
        # Implement your logic here
        if success:
            return PhaseResult(success=True, message="Phase completed")
        else:
            return PhaseResult(success=False, message="Phase failed")
```

### Using Services
```python
from workflow_tools.service_container import ServiceContainer

# Get services through dependency injection
services = ServiceContainer(context, debug_mode)
code_generator = services.get_code_generator()
file_manager = services.get_file_manager()
```

### Context Access
```python
# Access context through sub-contexts
workspace_id = self.context.workspace.workspace_id
app_name = self.context.deployment.application_name
generated_code = self.context.code_generation.generated_code_draft
credentials = self.context.credentials.env_var_values
```

## Testing and Quality

### ✅ **Comprehensive Testing**
- All phases tested for instantiation and basic functionality
- Context attribute access verified
- Import paths validated

### ✅ **Error Handling**
- Custom exception hierarchy
- Graceful error recovery
- Detailed error logging and reporting

### ✅ **Code Quality**
- Follows PEP 8 style guidelines
- Type hints throughout
- Comprehensive documentation

## Future Extensibility

The architecture is designed for easy extension:

1. **New Workflow Types**: Add to `workflow_types.py` and implement phases
2. **New AI Providers**: Extend service interfaces
3. **New Integrations**: Add to `integrations/` directory
4. **New Phase Types**: Inherit from `BasePhase` or specialized base classes

## Conclusion

The `workflow_tools/` directory implements a robust, scalable, and maintainable architecture for AI-powered workflow automation. The clean separation of concerns, standardized interfaces, and comprehensive service layer make it easy to understand, test, and extend the system.

**Status**: ✅ **Fully Refactored and Functional** (2025-08-03)