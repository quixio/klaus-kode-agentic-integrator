# TDengine

[This connector](https://github.com/quixio/quix-samples/tree/main/python/destinations/tdengine) demonstrates how to consume data from a Kafka topic in Quix and persist the data to an TDengine database using the TDengine write API.

To learn more about how it functions, [check out the underlying 
Quix Streams `TDengine3Sink`](https://quix.io/docs/quix-streams/connectors/sinks/tdengine-sink.html).

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment Variables

The connector uses the following environment variables:


### Required
- **input**: This is the input topic.
- **TDENGINE_HOST**: Host address for the TDengine instance.
- **TDENGINE_DATABASE**: TDengine database name.
- **TDENGINE_TIME_PRECISION**: Time precision used when converting timestamps. Options: `ns`, `us`, `ms`, `s`.  
  Default: `ms`
- **CONSUMER_GROUP_NAME**: The name of the Kafka consumer group to use.  
  Default: `tdengine-sink`
- **TDENGINE_TOKEN**: Authentication token to access TDengine.
- **TDENGINE_SUPERTABLE**: The TDengine supertable name. This is required in the event 
  that its functionality is not directly replaced in the template with a user-defined 
  callable (see `main.py` for details).

### Optional
- **TDENGINE_NAME_SUBTABLES_FROM_TAGS**: If `true`, name subtables using the tag values (joined on `__`), else use TDengine's auto-generated randomized values. Can optionally ignore this and replace in code with a different callable for more control (see `main.py` for details).
- **TDENGINE_TAGS_KEYS**: Comma-separated keys to be used as tags when writing data to TDengine. Can optionally ignore this and replace in code with a callable for more control (see `main.py` for details).
- **TDENGINE_FIELDS_KEYS**: Comma-separated keys to be used as fields when writing data to TDengine. Can optionally ignore this and replace in code with a callable for more control (see `main.py` for details).
- **TIMESTAMP_COLUMN**: A key to be used as 'time' when converting to InfluxDB line protocol, else uses Kafka timestamp. May require adjusting `TDENGINE_TIME_PRECISION` to match.
- **TDENGINE_ALLOW_MISSING_FIELDS**: If `true`, missing field keys are skipped; otherwise a `KeyError` is raised.  
  Default: `false`
- **TDENGINE_INCLUDE_METADATA_TAGS**: If `true`, includes Kafka metadata (`key`, `topic`, `partition`) as tags.  
  Default: `false`
- **TDENGINE_CONVERT_INTS_TO_FLOATS**: If `true`, converts all integer values to floats.  
  Default: `false`
- **TDENGINE_ENABLE_GZIP**: If `true`, enables gzip compression when writing data.  
  Default: `true`
- **TDENGINE_MAX_RETRIES**: Maximum number of retries for failed requests.  
  Default: `5`
- **TDENGINE_RETRY_BACKOFF_FACTOR**: A {factor * 2^(retry_count)} backoff factor per retry attempt, starting from the second.  
  Default: `1.0`
- **BUFFER_SIZE**: Number of records to buffer before writing to TDengine.  
  Default: `50`
- **BUFFER_TIMEOUT**: Maximum time (in seconds) to buffer records before writing to TDengine.  
  Default: `1`



## Requirements / Prerequisites

You will need to have an TDengine instance available and an API authentication token.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open Source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo. Please star us and mention us on social to show your appreciation.
