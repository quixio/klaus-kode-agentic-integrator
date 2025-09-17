<task>
Create a Python script to test connection to: {user_prompt}
</task>

<purpose>
This is a connection test to verify we can successfully connect to the external source system and read sample data. This is NOT about integration yet - just testing the connection to the third-party system.
</purpose>

<working-directory>
A workflow agent has already prepared an app folder for you to work in. The app is located at: {app_path}

IMPORTANT: You are currently in the main workflow directory, NOT in the app directory.
You must work on files in the {app_path} directory. NEVER try to look at any files outside of this directory except those in the "resources" directory - i.e. `resources/**./*.md`—and even then, only look at those files when instructed to do so.
</working-directory>

<environment-variables>
Read app.yaml file (which is the equivalent to a .env file) and update the variables in there to match the new use case.

**NOTE**: Since this is a connection test only, you don't need to configure any Kafka topic variables yet. Focus only on the source system connection parameters (credentials, endpoints, etc.).
</environment-variables>

<credential-handling>
This only applies to systems that normally load credentials from a file. When using these systems, never assume credentials are stored in a file such as "path/to/credentials.json" and never add handling for loading credentials from a file.
Instead, assume that the file contents have been already loaded into env var such as "SECRET_KEY", "PASSWORD_KEY" or "API_KEY" etc.. and write code that will read credentials accordingly.
For example, for GCP, suppose that you receive an env var such as GCP_SECRET_KEY.
 - This will contain the credentials JSON (the same applies to other systems that require some kind of creds file to be specified)
 - When creating code, ignore the value of this variable.
 - For example, if you see something like GCP_SECRET_KEY=GCLOUD_PK_JSON, ignore the "GCLOUD_PK_JSON" part, that gets replaced during runtime.
 - Instead, you use the env var name "GCP_SECRET_KEY" to get the JSON. Follow the same pattern for other technologies too.
 - Also, NEVER check the JSON like this `credentials_key = os.environ['GCP_CREDENTIALS_KEY']\ncredentials_json = os.environ.get(credentials_key)\nif not credentials_json:` just check the contents of `os.environ['GCP_CREDENTIALS_KEY']` directly.
 - In app.yaml, credentials such as these must ALWAYS have the field type `Secret`
</credential-handling>

<knowledge-resources>
1. **Source-specific sample code**:
In the master directory `resources/python/sources` you will find a list of subdirectories that each contain a sample app that also uses the quixstreams python library to get data from kind of source. You're not supposed to use the quixstreams library yet, so don't worry about quixstreams usage yet, however there might still be some other code in there that could help you achieve your task so its worth looking in there anyway.

From the list, pick ONE source that you think is most relevant to the current requirements, and examine the python files in your chosen directory (usually just `main.py`) as well as the `app.yaml` file for appropriate variables, and `requirements.txt` for the appropriate dependencies)

2. **External Documentation**
If you need technology-specific documentation, check the files in `resources/other/source_external_docs/` directory to see if there is any file that relates to the technology that you're currently working on.
</knowledge-resources>

<requirements>
1. Connect to the source system specified in the user's request using the provided credentials
2. Read exactly 10 sample items/entries/records from the source
3. Print each item to console for inspection (use clear formatting)
4. Include proper error handling with informative messages
5. Do NOT write to Kafka topics - this is connection testing only
6. Use appropriate Python libraries for the source system
7. All imports must be at the top of the file (no inline imports)
</requirements>

<output-format>
The test should produce clear output showing:
- Connection status (success/failure)
- Sample data retrieved (formatted for readability)
- Any relevant metadata about the source (e.g., total records available, API limits, etc.)
</output-format>

<error-handling>
- Provide clear error messages that help diagnose connection issues
- Never expose sensitive credential information in error messages
- Include retry logic where appropriate for transient failures
</error-handling>

<instructions>
Update `main.py` with clean, working Python code for testing the connection to the source system specified in the user's request.

We will also use the data that you generate to infer the structure of the data for writing to kafka later on (not yet though)
</instructions>

<critical-note-testing>
This code will be uploaded to a code sandbox and tested there. NEVER attempt to do any local testing unless its a basic test to see if the code compiles and can be done without installing extra dependencies.
</critical-note-testing>

<important-note-todos>
If you are creating an internal TODO list for yourself, please print it as part of your thoughts so that the user can see whats going on. You don't need approval for the list, just make it visible.
</important-note-todos>