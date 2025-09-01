# PostgreSQL Sink

[This connector](https://github.com/quixio/quix-samples/tree/main/python/destinations/postgres) demonstrates how to consume data from a Kafka topic in Quix and persist the data to a PostgreSQL database using the `PostgresSink`.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment Variables

The connector uses the following environment variables:

### Required
- **input**: The input kafka topic.
- **POSTGRES_HOST**: Host address for the PostgreSQL instance.
- **POSTGRES_PORT**: Port number for the PostgreSQL instance.
- **POSTGRES_DBNAME**: Database name in PostgreSQL where data should be stored.
- **POSTGRES_USER**: Username for the PostgreSQL database.
- **POSTGRES_PASSWORD**: Password for the PostgreSQL database.
- **POSTGRES_TABLE**: The PostgreSQL table where data will be stored. If the table does not exist, it will be created automatically.  
  Default: `default_table`

### Optional
- **POSTGRES_SCHEMA**: The schema name. Schemas are a way of organizing tables and not related to the table data, referenced as `<schema_name>.<table_name>`.  
  Default: `public` (also the Postgres default).
- **POSTGRES_SCHEMA_AUTO_UPDATE**: Automatically update the schema by adding new columns when new fields are detected.  
  Default: `true`
- **POSTGRES_PRIMARY_KEY_COLUMNS**: An optional comma-separated list of primary key column(s). Often paired with `POSTGRES_UPSERT_ON_PRIMARY_KEY=true`.
- **POSTGRES_UPSERT_ON_PRIMARY_KEY**: If `true`, upsert based on the given `primary_keys`, else every message is treated as an independent entry, and any primary key collisions will consequently raise an exception.  
  Default: `true`
- **CONSUMER_GROUP_NAME**: The name of the consumer group to use when consuming from Kafka.  
  Default: `postgres-sink`
- **BATCH_SIZE**: The number of records that the sink holds before flushing data to PostgreSQL.  
  Default: `1000`
- **BATCH_TIMEOUT**: The number of seconds that the sink holds before flushing data to PostgreSQL.  
  Default: `1`

## Requirements / Prerequisites

You will need to have a PostgreSQL instance available and ensure that the connection details (host, port, database, user, and password) are correctly configured.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you, and you'll receive $200 in Quix credit.

## Open Source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo. Please star us and mention us on social media to show your appreciation.