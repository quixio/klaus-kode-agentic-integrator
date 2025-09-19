<problem>
The {workflow_type} application encountered errors when running on the cloud platform. Please analyze and fix the issues.
</problem>

<important-context>
- The code runs remotely on the cloud platform, not locally
- You don't need to install anything locally - focus on fixing dependencies in requirements.txt
- The platform handles the actual package installation based on requirements.txt
- **PATH MAPPING**: Error logs show paths like `/project/app-name/main.py` (cloud environment) but you're working on the equivalent local files in: {app_path}
- **CURRENT LOCATION**: You are in the main workflow directory. The application files are in: {app_path}
- Always use the full relative path when editing files (e.g., {app_path}/main.py, {app_path}/requirements.txt)
</important-context>

<expected-data-schema>
The application should be processing data with this schema (from Kafka topic analysis):

```
{schema_analysis}
```
</expected-data-schema>

<error-logs>
```
{error_logs}
```
</error-logs>

<previous-debug-attempts>
Learn from these previous debug attempts to avoid repeating the same mistakes:
(if you just see empty space between "**START PREVIOUS ATTEMPTS:**" and "**END PREVIOUS ATTEMPTS:**", then there are no previous attempts yet)

**START PREVIOUS ATTEMPTS:**
{previous_thoughts}
**END PREVIOUS ATTEMPTS:**

The above includes both:
- [THINKING]: Your internal reasoning from previous attempts
- VISIBLE OUTPUT: What you communicated to the user

CRITICAL: Review the [THINKING] sections carefully to understand what approaches you've already tried internally.
If you notice you're about to try the same approach again, STOP and try a completely different strategy.

Please acknowledge what you learned from the previous attempts before proceeding.
If you find yourself repeating the same mistakes, try to reason about the problem from a fundamentally different angle.
</previous-debug-attempts>

<critical-instructions>
**IMPORTANT: You MUST use the Edit or Write tools to actually FIX the files, not just read them!**

Please fix the issues by:
1. First, analyze the error messages carefully by reading the relevant files
2. **THEN USE THE EDIT TOOL ON MAIN.PY** to fix the code in {app_path}/main.py and other files in {app_path} as needed and ensure all imports are correct and available
3. **USE THE EDIT TOOL ON REQUIREMENTS.TXT** to update {app_path}/requirements.txt with proper package names and versions if dependency errors occur—also verify that package extras are included if needed (check error messages for required extras) - but don't update it if the error has nothing to do with dependencies.
4. **USE THE EDIT TOOL ON APP.YAML** Make sure environment variables are properly handled and if there are errors due to variables not being defined properly, and update {app_path}/app.yaml with proper variable names or at least make sure that the right variables exist

**DO NOT just analyze the code - you MUST actually EDIT the files to fix the errors!**
Focus on making the code work correctly on the remote platform by editing, code and/or variables and/or dependencies.
</critical-instructions>


<stop-conditions-note>
* If you see stop conditions such as `app.run(count=10, timeout=20)`, leave them in for now. They are there to ensure that the app does not endlessly produce logs which makes debugging hard.
* If you see stop conditions that read only a limited number of items from the source, leave them in for now. They are also there to ensure that the app does not endlessly produce logs which makes debugging hard.
</stop-conditions-note>

<files-to-avoid>
* Do not change the Dockerfile unless you are 100% sure that it relates to the bug
* Do not change the README, the user can update it themselves.
</files-to-avoid>


<evidence-requirement>
**CRUCIAL:** **PROVIDE EVIDENCE OF SINKING**: When debugging a sink application, you must log evidence that the table you are writing to actual exists in the db, and that you have successfully written messages to the table. It is not enough to log that you have read the messages. You must confirm that the batch has been successfully written.
</evidence-requirement>

<todo-list-note>
If you are creating an internal TODO list for yourself, please print it as part of your thoughts so that the user can see whats going on. You don't need approval for the list, just make it visible.
</todo-list-note>

<general-debugging-guidance>
If you are struggling to debug the issue double-check the documentation for relevant informaton.

For example:

* for general debugging help, check `.../../resources/common/debugging.md`
* for issues with serialization, check `.../../resources/common/serialization.md`
* for issues with processings and producing data (and how to use `sdf` streaming dataframes), check `.../../resources/source/processing.md`

Although your job is to debug the application and ensure that it works correctly, avoid creating overly complex, byzantine code that is difficult for users to read. Remember, this connection code is still a prototype, not yet ready for production.

Once you have fixed the bug in the original bug report, do not try to continue optimizing the code. Your primary object is to simply fix the bug. Do not check other or other files unnecessarily.

Just fix the bug and thats it. The user does not want to wait several minutes while you sniff through every single file in the directory.

If you are still unsure about how to best leverage the technology or framework used in the code, feel free to search the web.
</general-debugging-guidance>

