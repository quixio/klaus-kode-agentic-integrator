# Snowplow

[This connector](https://github.com/quixio/quix-samples/tree/main/python/sources/snowplow_source) demonstrates how to read data from Snowplow and publish it to a Kafka topic.

Note that this connector works with Snowplow instances on AWS Kinesis, so you will need connection details for Kinesis.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment variables

The connector uses the following environment variables:

- **output**: This is the Quix Topic that will receive the stream.
- **aws_access_key_id**: AWS Access Key Id.
- **aws_secret_access_key**: AWS Secret Access Key.
- **aws_region_name**: AWS Region Name.
- **aws_stream_name**: The name of the AWS stream you want to use.

## Requirements/prerequisites

You will need Snowplow deployed to AWS to use this project.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
