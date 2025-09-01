# HiveMQ

[This connector](https://github.com/quixio/quix-samples/tree/main/python/sources/hivemq) demonstrates how to consume data from a HiveMQ broker's MQTT topic and publish that data to a Kafka topic.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment Variables

The connector uses the following environment variables:

- **output**: Name of the output topic to publish to.
- **mqtt_topic**: The MQTT topic to listen to. Can use wildcards e.g. MyTopic/#
- **mqtt_server**: The address of your MQTT server.
- **mqtt_port**: The port of your MQTT server.
- **mqtt_username**: Username of your MQTT user.
- **mqtt_password**: Password for the MQTT user.

## Requirements / Prerequisites

You'll need to have a HiveMQ broker running either locally or in the cloud

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
