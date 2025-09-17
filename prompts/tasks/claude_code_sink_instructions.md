<user-request>
I have the following request for a sink application:

{user_prompt}

Please help me fulfill this request.
</user-request>

<working-directory>
A workflow agent has already prepared an app folder for you to work in. The app is located at: {app_path}

IMPORTANT: You are currently in the main workflow directory, NOT in the app directory.
You must work on files in the {app_path} directory. NEVER try to look at any files outside of this directory except those in the "resources" directory - i.e. `resources/**./*.md`—and even then, only look at those files when instructed to do so.
</working-directory>

<important-context-files>
Before starting, please read refer to the following extra documentation and sample files understand the quixstreams python better:

<knowledge-resources>
1. **Sink-specific sample code**:
In the master directory `resources/python/destinations` you will find a list of subdirectories that each contain a sample app that also uses the quixstreams python library to write data to some kind of sink.

From the list, pick ONE sink app that you think is most relevant to the current requirements, and examine the python files in your chosen directory (usually just `main.py`) as well as the `app.yaml` file for appropriate variables, and `requirements.txt` for the appropriate dependencies)

2. **Common Quix Streams documentation**:
Read all files in `resources/common/*.md` to understand how data serialization and debugging work.

3. **Technology-specific documentation**:
List the files in the directory `resources/other/sink_external_docs` and check the file and directory names to see if there are any documents that are relevant to the current requirements.

4. **(optional) transformation and output related information**

If the user's request includes a requirement to output data TO a topic as well as reading data FROM a topic you might also want to check one of the transformation examples which show you how to route data from an input topic, do something to it, then write all or some of the data to an output topic.

If you are building a simple-one way sink dont bother reading the next paragraph, skip to the `Data Schema Analysis` section.

If you need to do something like the previously described output use case, list the sample apps in this folder: `resources/python/transformations`, and pick the one that best suits the requirements (usually `starter_transformation`) and examine the python files in your chosen directory (usually just `main.py`) as well as the `app.yaml` file for appropriate variables, and `requirements.txt` for the appropriate dependencies).
</knowledge-resources>
</important-context-files>

<data-schema-analysis>
**CRITICAL**: The exact data structure for this task is documented in:
- Primary file: `working_files/cache/sink/schemas/{topic_id}_schema_analysis_schema.md`

READ THE SCHEMA FILE CAREFULLY - it contains the exact message structure you need to process.

<general-schema-guidance>
Here is the basic message schema as it comes from the topic:

  'key': b'SOMEKEY',
  'timestamp': 1755528526770,
  'headers': None
  {{ 'value': {{ 'some_id': 'PARIS-P0045',
             'some_measurement': '12',
             'timestamp': 1755528526770038016}}
             }},

However, the quix sdf methods extracts the data for you, so if you print value of sdf without the metadata flag, you get:

             {{
              'some_id': 'PARIS-P0045',
             'some_measurement': '12',
             'timestamp': 1755528526770038016}}
             }}
</general-schema-guidance>
</data-schema-analysis>

<environment-variables>
Read app.yaml file (which is the equivalent to a .env file) and update the variables in there to match the new use case.

**IMPORTANT**: When updating app.yaml, set the default value for the input topic variable to "{topic_name}". This is the topic the user originally selected during the workflow setup.
</environment-variables>

<template-reference>
The {app_path} directory contains boilerplate starter code in `main.py` from library item '{library_item_id}'. Use framework and pattern is this boilerplate as your starting reference.
</template-reference>

<critical-implementation-requirements>
Please modify {app_path}/main.py to fulfill my request. Use the existing framework in {app_path}/main.py and adapt it based on the schema analysis and requirements above.

Important instructions:

1. **CRITICALLY IMPORTANT**: Pay careful attention to the message structure from the schema analysis. Do NOT assume messages have a 'value' field. Check if the data is directly in the message or nested in fields.
2. Update {app_path}/requirements.txt with any new dependencies you have used (use correct pip package names)
3. Update {app_path}/app.yaml with all new environment variables you have introduced in this new code

4. **CRITICAL**: For the input topic variable in {app_path}/app.yaml, set the defaultValue to "{topic_name}" (this is the topic the user selected during setup)
5. If there is an {app_path}/.env file present, update it with all the new environment variables to match app.yaml
6. For debugging, include early print statements to show raw message structure
7. Handle errors gracefully with try/except blocks and add appropriate logging
8. NEVER hardcode connection strings - always use environment variables
9. The application should be production-ready when complete
</critical-implementation-requirements>

<sink-specific-requirements>
1. **Data Flow**: Read messages from the Kafka input topic and write to the destination system
2. **Message Processing**:
   - Use `sdf.sink()` with appropriate sink implementation
   - Pay careful attention to the message structure from schema analysis
   - Do NOT assume messages have a 'value' field - check the actual structure

3. **Batching**: Implement appropriate batching for the destination system to optimize performance

4. **Database/Table Setup** (if applicable):
   * If it is a database, make sure that you explicitly map the message value schema to the table schema and add a check to create the table if it doesnt exist. NEVER try to alter the table schema to match the schema of the message. It should be the other way around - ALWAYS update schema of the kafka message to match the schema of the table

   * If you do need to create the table, create it as early as possible and commit the DDL immediately, and also convert epoch timestamps to native datetime types.

   **summary**
   - Create table/collection if it doesn't exist
   - Map Kafka message fields to destination schema correctly
   - Convert epoch timestamps to native datetime types

5. **Error Handling**:
   - Implement retry logic with exponential backoff
   - Handle connection failures gracefully
   - Use SinkBackpressureError for temporary issues

6. **Environment Variables**:
   - Use environment variables for all configuration
   - Never hardcode credentials or connection strings
   - **Set the input topic variable defaultValue to "{topic_name}" in app.yaml**

7. **Testing**: Include `app.run(count=10, timeout=20)` for initial testing

8. **Debugging**: Add early print statements to show raw message structure
</sink-specific-requirements>

<common-gotchas>
CRITICAL: Please be aware of these gotchas and ensure that you avoid them in your code.

<gotcha-1>
As an AI developer, your code tends to introduce this error fairly often:

ERROR: `AttributeError: 'MyCustomSink' object has no attribute '_on_client_connect_success' or has not attribute 'on_client_connect_success'

This is a common coding problem – when that connection attempt raises an exception. Make sure you initialize a customer sink according to this pattern:

```python
class MyMyCustomSink(BatchingSink):
    """
    Some sink writing data to a database
    """
    def __init__(self, on_client_connect_success=None, on_client_connect_failure=None):
        super().__init__(
           on_client_connect_success=on_client_connect_success,
           on_client_connect_failure=on_client_connect_failure
        )
```
</gotcha-1>

<gotcha-2>
You often get errors relating the the user of "len" when trying get the length of a batch.

The `SinkBatch` class doesn't support the `len()` function. So dont try and use it with `SinkBatch`
</gotcha-2>
</common-gotchas>

<additional-rules>
Follow these rules precisely:
1. Your code must correctly process the incoming data based on the provided schema analysis and it MUST use an input topic variable.
2. Use the provided template code as a structural guide, but adapt it for the new schema and destination.
3. If it is a database, make sure that you explicitly map the message value schema to the table schema and add a check to create the table if it doesnt exist.
3.1 If you do need to create the table, create it as early as possible and commit the DDL immediately, and also convert epoch timestamps to native datetime types,
4. Use environment variables for all connection credentials. Use the exact environment variable names as defined in app.yaml.
5. IMPORTANT: The application must stop after processing 10 messages. Use `app.run(count=10, timeout=20)`.
6. CRITICAL: Pay careful attention to the message structure from the schema analysis. Do NOT assume messages have a 'value' field. Check if the data is directly in the message or nested in fields. Use safe access like `item.value.get('field')` instead of `item.value['field']`. Treat `item.value` as an already-parsed dictionary; only apply `json.loads()` when the payload is still a string/bytes.
HINT: Pay close attention to the structure of the example message in the schema analysis file.
7. For debugging, include an early print statement to show the raw message structure as soon as you receive it: `print(f'Raw message: <message-body>')`.
9. Always use the sink API as specified in the Quix documentation. Write data using something like this: 'mysink = (<sink properties)' THEN 'sdf.sink(my_sink)'
10. CRITICAL: Never try to add lines connecting to a local broker (i.e. NEVER use broker_address = localhost:9092). The quixstreams library can auto-detect the broker in its environment anyway.
11. IMPORTANT: Never use int() directly on environment variables, especially ports. Always use try/except blocks to handle cases where environment variables might contain unexpected values in deployment environments. For example, use: `try: port = int(os.environ.get('DB_PORT', '5432')); except ValueError: port = 5432` where the fallback port matches the default in the environment variable.
12. SECRETS HANDLING: When using secrets for passwords, use the environment variable name that references the secret (e.g., `os.environ.get('DB_PASSWORD_SECRET')`). In Quix, secrets are automatically resolved when properly configured as environment variables.

Generally, try not to overengineer the task, try to keep the code simple, elegant and easy for others to read.
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

<todo-list-note>
If you are creating an internal TODO list for yourself, please print it as part of your thoughts so that the user can see whats going on. You don't need approval for the list, just make it visible.
</todo-list-note>

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

Except for the quixstreams library, NEVER pin common dependencies to a specific version (such as "requests==2.2.1" or "python-dotenv==1.3.0") unless you are explicitly asked to do so. Instead, specify dependencies purely by name such as ("requests" or "python-dotenv").
</dependencies-and-extras>

<critical-dependency-versions>
If the user specifies a particular technology version, make sure you use the appropriate library for that version. For example, if the user specifies "Influx DB V2" do not install `quixstreams[influxdb1]` or `quixstreams[influxdb3]` as those extras are for InfluxDB Versions 1 and Version 3 respectively. Instead you should install a separate module, `influxdb-client` which is known to work with InfluxDB version 2. Generally, if you are unsure about what library version to use with that specific version of the sink technology, search the web.
</critical-dependency-versions>

<testing-documentation-note>
* NEVER add documentation for this project unless explicitly requested to do so.
* NEVER try to write any tests unless explicitly requested to do so.
* NEVER touch the Dockerfile, this file is off-limits so you dont need to read it.
* In there is no .env already, dont try to create one.

Generally, the application you are writing is designed to help the user get started rather than being a full fledged production app.
So proceed with the assumption that you are creating a prototype rather than creating a production-ready app. Dont try to over engineer things.
</testing-documentation-note>

<evidence-requirement>
**CRUCIAL**: You must log evidence that the table you are writing to actual exists in the db, and that you have successfully written messages to the table. It is not enough to log that you have read the messages. You must confirm that the batch has been successfully written.
</evidence-requirement>