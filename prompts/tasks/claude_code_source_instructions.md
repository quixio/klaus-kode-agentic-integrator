<user-request>
I have the following request for a source application:

{user_prompt}

Please help me fulfill this request.
</user-request>

<working-directory>
A workflow agent has already prepared an app folder for you to work in. The app is located at: {app_path}

IMPORTANT: You are currently in the main workflow directory, NOT in the app directory.
You must work on files in the {app_path} directory. NEVER try to look at any files outside of this directory except those in the "resources" directory - i.e. `resources/**./*.md`—and even then, only look at those files when instructed to do so.
</working-directory>

<important-context-files>
Before starting, please read the following documentation and sample files to understand the system:

<knowledge-resources>
1. **Source-specific sample code**:
In the master directory `resources/python/sources` you will find a list of subdirectories that each contain a sample app that also uses the quixstreams python library to get data from kind of source.

From the list, pick ONE source that you think is most relevant to the current requirements, and examine the python files in your chosen directory (usually just `main.py`) as well as the `app.yaml` file for appropriate variables, and `requirements.txt` for the appropriate dependencies)

2. **Common Quix Streams documentation**:
Read all files in `resources/common/*.md` to understand how data serialization and debugging work.

3. **Technology-specific documentation**:
List the files in the directory `resources/other/source_external_docs` and check the file and directory names to see if there are any documents that are relevant to the current requirements.

4. **The previous simple connection test**
We have already done a simple connection text to read a small sample of messages from the source. You can find it in the working directory, it is called `connection_test.py`. Use this code to see what has worked already when connecting to the source system and incorporate it into your final version that uses quixstreams to write the data to a kafka topic.
</knowledge-resources>
</important-context-files>

<environment-variables>
Read app.yaml file (which is the equivalent to a .env file) and update the variables in there to match the new use case.

**IMPORTANT**: When updating app.yaml, set the default value for the output topic variable to "{topic_name}". This is the topic the user originally selected during the workflow setup.
</environment-variables>

<template-reference>
The {app_path} directory contains boilerplate starter code in `main.py` from library item '{library_item_id}'. Use framework and pattern is this boilerplate as your starting reference.
</template-reference>

<data-schema-analysis>
**CRITICAL**: The exact data structure for this task is documented in:
- Primary file: `working_files/cache/source/schemas/{app_name}_schema.md`

READ THE SCHEMA FILE CAREFULLY - it contains the exact message structure you need to process.
</data-schema-analysis>

<critical-implementation-requirements>
Please modify {app_path}/main.py to fulfill my request. Use the existing framework in {app_path}/main.py and adapt it based on the schema analysis and requirements above.

Important instructions:
1. **CRITICALLY IMPORTANT**: Pay careful attention to the message structure from the schema analysis. Do NOT assume messages have a 'value' field. Check if the data is directly in the message or nested in fields.
2. Update {app_path}/requirements.txt with any new dependencies you have used (use correct pip package names)
3. Update {app_path}/app.yaml with all new environment variables you have introduced in this new code

Note that variables in app.yaml can have one of the following types:

    "Topic",
    "FreeText",
    "HiddenText",
    "InputTopic",
    "OutputTopic",
    "Secret"

Please set the appropriate type for each variable (note that the "Secret" type is reserved for confidential variables such as passwords and API tokens)

4. **CRITICAL**: For the output topic variable in {app_path}/app.yaml, set the defaultValue to "{topic_name}" (this is the topic the user selected during setup)
5. If there is an {app_path}/.env file present, update it with all the new environment variables to match app.yaml
6. For debugging, include early print statements to show raw message structure
7. Handle errors gracefully with try/except blocks and add appropriate logging
8. NEVER hardcode connection strings - always use environment variables
9. The application should be production-ready when complete
</critical-implementation-requirements>

<source-specific-requirements>
1. **Data Flow**: Read data from the external source system and write to the Kafka output topic
2. **Message Processing**:
   - Use appropriate source implementation to read from the external system
   - Transform data into Kafka message format based on the schema analysis
   - Produce messages to the output topic using `sdf`

3. **Polling/Streaming**: Implement appropriate polling or streaming strategy based on the source system

4. **Data Transformation**:
   - Convert source data to the expected Kafka message format
   - Handle data type conversions appropriately
   - Include proper timestamps in messages

5. **Error Handling**:
   - Implement retry logic with exponential backoff for source connection issues
   - Handle connection failures gracefully
   - Log errors without exposing credentials

6. **Environment Variables**:
   - Use environment variables for all configuration
   - Never hardcode credentials or connection strings
   - **Set the output topic variable defaultValue to "{topic_name}" in app.yaml**

7. **Testing**: When reading from a source, limit the output to 100 entries for initial testing

8. **Debugging**: Add early print statements to show raw message structure
</source-specific-requirements>

<additional-rules>
1. Create a complete main.py that uses Quix Streams
2. Read data from the chosen technology using the connection parameters
3. Transform data into appropriate Kafka message format based on the schema analysis
4. Use Quix Streams Application and Topic classes correctly
5. Include proper error handling and logging
6. Add a stop condition after processing 100 messages (for testing)
7. Include proper connection cleanup and resource management
8. NEVER use the broker_address argument (i.e do not do this `app = Application(broker_address="localhost:19092"`) because the code will be deployed in an environment where the broker address is automatically detected.
9. NEVER use inner imports such as `try: \n import json`, always specific all required imports at the beginning of your code.
10. ALWAYS use the `sdf` method to produce data to a topic. E.g:`sdf = app.dataframe(topic=topic, source=source)`
11. Always use sdf print statements to help users see messages being produced: `sdf.print(metadata=True)`

Generate clean, production-ready Python code for the source application.
</additional-rules>

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

<rest-api-note>
If you are reading data from a REST API, please think carefully about the following guideline:

Your code needs to be robust enough to be able to handle unexpected response structures. For example, an API may return data in the expected structure for a while, be then suddenly return a different response with a different structure, this often occurs when an API wants to tell you that you have run out of your allotted request quota, or API credits. This information is often returned in a specially formatted JSON response. Your code should be robust enough to handle this sudden change in response structure.
</rest-api-note>

<dependencies-and-extras>
The quixstreams python library supports the following extras so you dont have to install these packages separately if you need to use any of these:

quixstreams[elasticsearch]
quixstreams[avro]
quixstreams[aws]
quixstreams[azure-file]
quixstreams[azure]
quixstreams[bigquery]
quixstreams[elasticsearch]
quixstreams[iceberg_aws]
quixstreams[iceberg]
quixstreams[influxdb1]
quixstreams[influxdb3]
quixstreams[kinesis]
quixstreams[mongodb]
quixstreams[neo4j]
quixstreams[pandas]
quixstreams[postgresql]
quixstreams[protobuf]
quixstreams[pubsub]
quixstreams[redis]
quixstreams[s3]
quixstreams[tdengine]

Except for the quixstreams library, NEVER add ANY version constraints to common dependencies - no ==, >=, <=, ~=, or any other version specifiers (BAD: "requests==2.2.1", "pandas>=1.5.0", GOOD: "requests", "pandas")—unless you are explicitly asked to do so.

<dependency-examples>
CORRECT requirements.txt format:
requests
pandas
openpyxl

INCORRECT (DO NOT DO THIS):
requests>=2.25.0
pandas>=1.5.0
openpyxl>=3.0.9
</dependency-examples>
</dependencies-and-extras>

<critical-dependency-versions>
If the user specifies a particular technology version, make sure you use the appropriate library for that version. For example, if the user specifies "Influx DB V2" do not install `quixstreams[influxdb1]` or `quixstreams[influxdb3]` as those extras are for InfluxDB Versions 1 and Version 3 respectively. Instead you should install a separate module, `influxdb-client` which is known to work with InfluxDB version 2. Generally, if you are unsure about what library version to use with that specific version of the sink technology, search the web.
</critical-dependency-versions>

<testing-documentation-note>
* NEVER add documentation or a README for this project unless explicitly requested to do so.
* NEVER try to write any tests unless explicitly requested to do so.
* NEVER touch the Dockerfile, this file is off-limits so you dont need to read it.
* In there is no .env already, dont try to create one.

Generally, the application you are writing is designed to help the user get started rather than being a full fledged production app.
So proceed with the assumption that you are creating a prototype rather than creating a production-ready app.

If you feel like you dont have enough information about how to connect to the sink using python, try and search the web to get form information.
</testing-documentation-note>

<todo-list-note>
If you are creating an internal TODO list for yourself, please print it as part of your thoughts so that the user can see whats going on. You don't need approval for the list, just make it visible.
</todo-list-note>