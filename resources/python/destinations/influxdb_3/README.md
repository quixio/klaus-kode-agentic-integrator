# InfluxDB v3

[This connector](https://github.com/quixio/quix-samples/tree/main/python/destinations/influxdb_3) demonstrates how to consume data from a Kafka topic in Quix and persist the data to an InfluxDB v3 database using the InfluxDB write API.

To learn more about how it functions, [check out the underlying 
Quix Streams `InfluxDB3Source`](https://quix.io/docs/quix-streams/connectors/sinks/influxdb3-sink.html).

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment Variables

The connector uses the following environment variables:

- **input**: This is the input topic (Default: `detection-result`, Required: `True`)
- **TIMESTAMP_COLUMN**: This is the column in your data that represents the timestamp in nanoseconds. Defaults to use the message timestamp received from the broker if not supplied. Case sensitive. (Default: ``, Required: `False`)
- **INFLUXDB_HOST**: Host address for the InfluxDB instance. (Default: `https://eu-central-1-1.aws.cloud2.influxdata.com`, Required: `True`)
- **INFLUXDB_TOKEN**: Authentication token to access InfluxDB. (Default: `<TOKEN>`, Required: `True`)
- **INFLUXDB_ORG**: Organization name in InfluxDB. (Default: `<ORG>`, Required: `False`)
- **INFLUXDB_DATABASE**: Database name in InfluxDB where data should be stored. (Default: `<DATABASE>`, Required: `True`)
- **INFLUXDB_TAG_KEYS**: Keys to be used as tags when writing data to InfluxDB. These are columns that are available in the input topic. (Default: ``, Required: `False`)
- **INFLUXDB_FIELD_KEYS**: Keys to be used as fields when writing data to InfluxDB. These are columns that are available in the input topic. (Default: ``, Required: `True`)
- **INFLUXDB_MEASUREMENT_NAME**: The InfluxDB measurement to write data to. If not specified, the name of the input topic will be used. (Default: `measurement1`, Required: `False`)

## Requirements / Prerequisites

You will need to have an InfluxDB 3.0 instance available and an API authentication token.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open Source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo. Please star us and mention us on social to show your appreciation.
