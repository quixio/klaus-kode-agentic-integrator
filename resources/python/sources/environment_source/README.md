# Quix Environment Source

This project provides a ready-to-use solution for mirroring data from one Quix environment to another. It is ideal for replicating production data into development environments for testing, analysis, or debugging purposes.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment Variables

The following environment variables are required for this connector:

- **topic**: The Quix topic that will be mirrored from the source environment.
- **source_workspace_id**: The workspace ID of the Quix environment you are mirroring from.
- **source_sdk_token**: The SDK token to authenticate access to the source environment.
- **consumer_group**: *(Optional)* The Kafka consumer group used by the source environment. Defaults to `quix_environment_source`.
- **auto_offset_reset**: *(Optional)* Specifies the offset reset policy when starting a new consumer group. Defaults to `earliest`.

## How it works

This project enables seamless data streaming from one Quix environment to another by utilizing the `QuixEnvironmentSource` to read data from the source environment's Kafka topic and publish it to a designated output topic.

The `main.py` script is designed to run in your Quix environment, leveraging environment variables for configuration to ensure that data flows smoothly between workspaces.

## Contribute

You are encouraged to submit forked versions of this project to the Quix [GitHub](https://github.com/quixio/quix-samples) repository. If accepted, you'll be credited with $200 in Quix credits.

## Open Source

This project is open source under the Apache 2.0 license. Check it out on [GitHub](https://github.com/quixio/quix-samples) and feel free to star us or mention us on social media to show your support.