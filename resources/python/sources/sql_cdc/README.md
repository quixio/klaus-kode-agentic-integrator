# SQL Change Data Capture (CDC)

[This connector](https://github.com/quixio/quix-samples/tree/main/python/sources/sql_cdc) demonstrates how to capture changes to an SQL database table (using CDC) and publish the change events to a Kafka topic.

It uses sqlite as a temporary storage to track the latest timestamp and QuixStreams Producer to publish data changes to Kafka.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment variables

The connector uses the following environment variables:

- **output**: The output topic for the captured data.
- **driver**: The driver required to access your database. e.g. `\{/opt/microsoft/msodbcsql18/lib64/libmsodbcsql-18.1.so.1.1\}`
- **server**: The server address.
- **userid**: The user ID.
- **password**: The password.
- **database**: The database name.
- **table_name**: The table to monitor.
- **last_modified_column**: The column holding the last modified or update date and time. e.g. `timestamp`
- **time_delta**: The amount of time in the past to look for data. It should be in this format. `0,0,0,0,0` These are seconds, minutes, hours, days, weeks. `30,1,0,0,0` therefore this is 1 minute and 30 seconds.
- **offset_is_utc**: True or False depending on whether the last_modified_column is in UTC.
- **columns_to_drop**: Comma separated list of columns to exclude from data copied from the target table to Quix.
- **columns_to_rename**: Columns to rename while streaming to Quix. This must be valid json e.g. `\{"DB COLUMN NAME":"QUIX_COLUMN_NAME"\}` or `\{"source_1":"dest_1", "source_2":"dest_2"\}`
- **poll_interval_seconds**: How often to check for new data in the source table.

Note that the columns to rename and columns to drop settings do not affect the source database. They are used when streaming data into Quix.

Driver and columns to rename should include `{` and `}` and the start and end of their values and these MUST be escaped with a `\`.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
