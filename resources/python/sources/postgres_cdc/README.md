# PostgreSQL CDC

[This connector](https://github.com/quixio/quix-samples/tree/main/python/sources/postgres_cdc) demonstrates how to capture changes to a PostgreSQL database table (using CDC) and publish the change events to a Kafka topic.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment variables

The connector uses the following environment variables:

- **output**: Name of the output topic to write into.
- **PG_HOST**: The IP address or fully qualified domain name of your server.
- **PG_PORT**: The Port number to use for communication with the server.
- **PG_DATABASE**: The name of the database for CDC.
- **PG_USER**: The username of the sink should use to interact with the database.
- **PG_PASSWORD**: The password for the user configured above.
- **PG_SCHEMA**: The name of the schema for CDC.
- **PG_TABLE**: The name of the table for CDC.

## Requirements / Prerequisites

- A Postgres Database.
- Set `wal_level = logical` in `postgresql.conf`.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
