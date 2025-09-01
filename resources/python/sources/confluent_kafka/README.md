# Confluent Kafka

[This connector](https://github.com/quixio/quix-samples/tree/main/python/sources/confluent_kafka) demonstrates how to consume data from a Kafka topic in Confluent Cloud and publish the data to a Kafka topic configured in Quix.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment variables

The connector uses the following environment variables:

- **output**: This is the Quix Topic that will receive the stream.
- **kafka_key**: Obtained from the Confluent Kafka portal.
- **kafka_secret**: Obtained from the Confluent Kafka portal.
- **kafka_broker_address**: Obtained from the Confluent Kafka portal.
- **kafka_topic**: The Confluent Kafka Topic you wish to read from.
- **kafka_ca_location**: (Optional) Path to the SSL CA certificate file for secure connections. If not provided, the system's default CA certificates will be used.
- **kafka_sasl_mechanism**: (Optional) SASL mechanism for authentication. Defaults to "SCRAM-SHA-256".

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
