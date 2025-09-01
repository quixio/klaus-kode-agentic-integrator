# InfluxDB v2

[This connector](https://github.com/quixio/quix-samples/tree/main/python/sources/influxdb_2) demonstrates how to use the InfluxDB v2 query API to periodically query InfluxDB and publish the results to a Kafka topic.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment Variables

The connector uses the following environment variables:

- **output**: This is the ouput topic that will receive the stream (Default: `influxdb`, Required: `True`)
- **task_interval**: Interval to run query. Must be within the InfluxDB notation; 1s, 1m, 1h, 1d, 1w, 1mo, 1y (Default: `5m`, Required: `True`)
- **INFLUXDB_HOST**: Host address for the InfluxDB instance. (Default: `eu-central-1-1.aws.cloud2.influxdata.com`, Required: `True`)
- **INFLUXDB_TOKEN**: Authentication token to access InfluxDB. (Default: `<TOKEN>`, Required: `True`)
- **INFLUXDB_ORG**: Organization name in InfluxDB. (Default: `<ORG>`, Required: `False`)
- **INFLUXDB_BUCKET**: Bucket name in InfluxDB where data is stored. (Default: `<BUCKET>`, Required: `True`)
- **INFLUXDB_MEASUREMENT_NAME**: The InfluxDB measurement to read data from. If not specified, the name of the output topic will be used (Default: `<INSERT MEASUREMENT>`, Required: `False`)

## Requirements / Prerequisites

You will need to have an InfluxDB 2.0 instance available and an API authentication token.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open Source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo. Please star us and mention us on social to show your appreciation.
