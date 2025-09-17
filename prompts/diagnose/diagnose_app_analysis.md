<title>Application Analysis</title>

<role>
You are analyzing an existing application to help the user understand what it does and identify potential issues or improvements.
</role>

<application-details>
- **Application Name:** {app_name}
- **Application ID:** {app_id}
- **Workspace:** {workspace_id}
</application-details>

<files-to-analyze>
The application files are located in: `{app_directory}`

Please analyze the following files:
{file_list}
</files-to-analyze>

<task>
1. **Examine the main application file** (typically `app.py` or `main.py`)
2. **Review the configuration** in `app.yaml` to understand:
   - Environment variables and their purposes
   - Dependencies listed in requirements
   - The application's input/output topics
3. **Identify the application's purpose** based on:
   - Code structure and logic
   - External systems it connects to
   - Data transformations it performs
4. **Note any potential issues** such as:
   - Missing error handling
   - Hardcoded values that should be variables
   - Deprecated libraries or patterns
   - Performance bottlenecks
</task>

<output-format>
Provide a concise summary in the following format:

### Application Summary
[2-3 sentences describing what this application does]

### Key Components
- **Input:** [What data it reads and from where]
- **Processing:** [Main operations/transformations]
- **Output:** [What it produces and where it sends it]

### Configuration
- **Environment Variables:** [List key variables and their purposes]
- **Dependencies:** [Notable libraries used]

### Observations
[Any issues, improvements, or notable patterns you've identified]

### Recommendation
[Brief suggestion on whether to run as-is, fix issues first, or provide more context]
</output-format>