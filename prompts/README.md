# External Prompt Management System

This directory contains externalized prompts for all AI agents and tasks in the Quix Coding Agent workflow system.

## Directory Structure

```
prompts/
├── agents/          # Agent system instructions
│   ├── SinkKnowledgeGathererAgent.md
│   ├── SourceKnowledgeGathererAgent.md
│   ├── SinkCodeGeneratorAgent.md
│   ├── SourceCodeGeneratorAgent.md
│   └── ...
├── tasks/           # Task-specific prompts
│   ├── source_template_selection.md
│   ├── sink_code_generation.md
│   ├── source_schema_analysis.md
│   └── ...
└── README.md        # This file
```

## Agent Instructions

Agent instruction files contain the system instructions that define each AI agent's role, capabilities, and behavior. These are loaded when agents are created.

### Available Agent Instructions:

- **SinkKnowledgeGathererAgent.md** - Template matching for sink applications
- **SourceKnowledgeGathererAgent.md** - Template matching for source applications
- **EnvVarTranslatorAgent.md** - Unified environment variable translation for all workflows
- **MissingVariablesDetectorAgent.md** - Detects missing crucial variables
- **SmartDefaultsAgent.md** - Provides default values for environment variables
- **SinkSchemaAnalyzerAgent.md** - Analyzes Kafka topic schemas for sinks
- **SourceSchemaAnalyzerAgent.md** - Analyzes external data schemas for sources
- **SinkCodeGeneratorAgent.md** - Generates sink application code
- **SourceCodeGeneratorAgent.md** - Generates source application code
- **SinkDebugAgent.md** - Debugs sink application issues
- **SourceDebugAgent.md** - Debugs source application issues
- **SourceConnectionCodeAgent.md** - Generates connection testing code
- **SourceConnectionDebugAgent.md** - Debugs connection issues
- **ExternalTechPrepAgent.md** - Prepares external technology requirements

## Task Prompts

Task prompt files contain specific prompts used for particular operations. They support template variables using Python's `.format()` syntax.

### Available Task Prompts:

- **env_var_translation.md** - Unified prompt for translating environment variables
- **missing_variables_detection.md** - Prompt for detecting missing crucial variables
- **source_template_selection.md** - Prompt for selecting source templates
- **source_connection_code_generation.md** - Prompt for generating connection test code
- **source_schema_analysis.md** - Prompt for analyzing source data schemas
- **source_code_generation.md** - Prompt for generating source application code
- **source_technology_prep.md** - Prompt for preparing source technology requirements
- **sink_code_generation.md** - Prompt for generating sink application code
- **sink_technology_prep.md** - Prompt for preparing sink technology requirements

## Usage in Code

### Loading Agent Instructions

```python
from workflow_tools import load_agent_instructions

# Create agent with external instructions
agent = Agent[WorkflowContext](
    name="MyAgent",
    model="gpt-4o",
    instructions=load_agent_instructions("MyAgent"),
    tools=[],
)
```

### Loading Task Prompts

```python
from workflow_tools import load_task_prompt

# Load and format task prompt with variables
prompt = load_task_prompt(
    "my_task_prompt",
    variable1="value1",
    variable2="value2"
)
```

## Benefits

1. **Easy Editing** - Prompts can be edited in markdown files without touching code
2. **Version Control** - Prompt changes are tracked in git
3. **Collaboration** - Multiple team members can easily review and edit prompts
4. **Template Support** - Task prompts support variable substitution
5. **Organization** - Clear separation between agent instructions and task prompts
6. **Debugging** - Easy to see exactly what prompts are being sent to agents

## Template Variables

Task prompts support template variables using Python format syntax:

```markdown
Target Technology: {destination_technology}

Available Templates:
{template_list}

Find the best template for {destination_technology}.
```

Variables are passed when loading the prompt:

```python
prompt = load_task_prompt(
    "template_selection", 
    destination_technology="PostgreSQL",
    template_list=json.dumps(templates, indent=2)
)
```

## Adding New Prompts

### For Agent Instructions:
1. Create a new `.md` file in `prompts/agents/`
2. Name it after the agent (e.g., `MyNewAgent.md`)
3. Write the agent's system instructions
4. Load in code: `load_agent_instructions("MyNewAgent")`

### For Task Prompts:
1. Create a new `.md` file in `prompts/tasks/`
2. Use a descriptive name (e.g., `data_validation.md`)
3. Use `{variable_name}` for template variables
4. Load in code: `load_task_prompt("data_validation", variable_name="value")`

## Error Handling

The prompt manager provides graceful error handling:
- Missing files return error messages that are visible in logs
- Template variable errors are logged but don't crash the workflow
- All operations are logged for debugging

## Migration Status

The system is currently implemented in:
- ✅ Source workflow phases (knowledge, connection testing)
- ✅ Main orchestrator
- 🔄 Sink workflow phases (partial)
- ⏳ Other workflow components (planned)

To complete migration, update remaining phase files to use `load_agent_instructions()` and `load_task_prompt()` instead of inline strings.