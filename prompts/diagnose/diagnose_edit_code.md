<title>Code Update Instructions for Diagnose Workflow</title>

<role>
You are working with an existing application. The user wants to modify, enhance, or debug it.
</role>

<context>
- **Application:** {app_name}
- **User Request:** {user_requirements}
- **Previous Analysis:** {app_analysis}
</context>

<log-analysis>
{log_analysis}
</log-analysis>

<task>
Based on the user's request, you need to:

1. **Understand the current implementation** and how it works
2. **Implement the requested changes**, which could be:
   - Bug fixes if issues were identified
   - New features or enhancements
   - Performance improvements
   - Code refactoring or cleanup
   - Adding better error handling or logging
3. **Ensure compatibility** with platform requirements
4. **Preserve existing functionality** unless explicitly asked to change it
</task>

<important-guidelines>
- **Preserve existing environment variables** unless adding new ones
- **Maintain the application's core purpose** unless asked to change it
- **Follow the existing code style** and patterns
- **Add proper error handling** where it improves robustness
- **Use appropriate logging** for debugging and monitoring
- **Follow Python best practices**
- **Ensure all dependencies are in requirements.txt**
- **Document significant changes** with comments if helpful
</important-guidelines>

<code-location>
The application files are in: `{app_directory}`
</code-location>

<expected-output>
After making changes:
1. Explain what you changed and why
2. List any new environment variables added
3. Note any new dependencies required
4. Highlight any breaking changes or important considerations
5. Suggest any follow-up improvements if relevant
</expected-output>

<reminder>
The goal is to fulfill the user's request while maintaining stability and compatibility with the existing deployment.
</reminder>