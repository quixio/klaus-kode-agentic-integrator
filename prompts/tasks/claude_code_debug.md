The {workflow_type} application encountered errors when running on the Quix cloud platform. Please analyze and fix the issues.

**Important Context:**
- The code runs remotely on the Quix cloud platform, not locally
- You don't need to install anything locally - focus on fixing dependencies in requirements.txt
- The platform handles the actual package installation based on requirements.txt
- **PATH MAPPING**: Error logs show paths like `/project/app-name/main.py` (cloud environment) but you're working on the equivalent local files in: {app_path}
- **CURRENT LOCATION**: You are in the main workflow directory. The application files are in: {app_path}
- Always use the full relative path when editing files (e.g., {app_path}/main.py, {app_path}/requirements.txt)

## Expected Data Schema
The application should be processing data with this schema (from Kafka topic analysis):

```
{schema_analysis}
```

## Error Logs
```
{error_logs}
```

## Previous Debug Attempts
Learn from these to avoid repeating the same mistakes:
(if you just see empty space between "**START THOUGHTS:**" and "**END THOUGHTS:**, then are no previous thoughts yet)

**START THOUGHTS:**
{previous_thoughts}
**END THOUGHTS:**

Please use the previous thoughts to prevent yourself from trying the same thing over and over again. 
Please also provide an indication that you acknowledge the thoughts.

If you find yourself repeating the same mistakes over and over again, try to ultrathink about the problem from a different perspective.

**IMPORTANT: You MUST use the Edit or Write tools to actually FIX the files, not just read them!**

Please fix the issues by:
1. First, analyze the error messages carefully by reading the relevant files
2. **THEN USE THE EDIT TOOL ON MAIN.PY** to fix the code in {app_path}/main.py and other files in {app_path} as needed and ensure all imports are correct and available
4. **USE THE EDIT TOOL ON REQUIREMENTS.TXT** to update {app_path}/requirements.txt with proper package names and versions if dependency errors occur—also verify that package extras are included if needed (check error messages for required extras) - but don't update it if the error has nothing to do with dependencies.
5. **USE THE EDIT TOOL ON APP:YAML** Make sure environment variables are properly handled and if there are errors due to variables not being defined properly, and update {app_path}/app.yaml with proper variable names or at least make sure that the right variables exist


**DO NOT just analyze the code - you MUST actually EDIT the files to fix the errors!**
Focus on making the code work correctly on the remote Quix platform by editing, code and/or variables and/or dependencies.


## Note about stop conditions
* If you see stop conditions such as `app.run(count=10, timeout=20)`, leave them in for now. They are there to ensure that the the app does not endlessly produce logs which makes debugging hard.
* If you see stop conditions that read only a limited number of items from the source, leave them in for now. They are also there to ensure that the the app does not endlessly produce logs which makes debugging hard.


## Files to avoid editing
* Do not change the Dockerfile unless you are 100% sure that it relates to the bug
* Do not change the README, the user can update it themselves.


**CRUCIAL:** **PROVIDE EVIDENCE OF SINKING**: When debugging a sink application, you must log evidence that the table you are writing to actual exists in the db, and that you have successfully written messages to the table. It is not enough to log that you have read the messages. You must confirm that the batch has been successfully written.

## IMPORTANT NOTE ABOUT TODO LISTS

If you are creating an internal TODO list for yourself, please print it as part of your thoughts so that the user can see whats going on. You don't need approval for the list, just make it visible.

## GENERAL DEBUGGING GUIDANCE
If you are unsure about how to best leverage the technology or framework used in the code, feel free to search the web.

Although your job is to debug the application and ensure that it works correctly, avoid creating overly complex, byzantine code that is difficult for users to read. Remember, this connection code is still a prototype, not yet ready for production.

Once you have fixed the bug in the original bug report, do not try to continue optimizing the code. Your primary object is to simply fix the bug. Do not check other or other files unnecessarily. 

Just fix the bug and thats it. The user does not want to wait several minutes while you sniff through evey single file in the directory.

If you are not sure about what to do, search the web.

