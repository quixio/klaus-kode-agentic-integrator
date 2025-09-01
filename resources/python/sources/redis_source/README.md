# Redis Source

[This connector](https://github.com/quixio/quix-samples/tree/main/python/sources/redis_source) demonstrates how to use the Redis Python client to query Redis and publish the results to a Kafka topic.

Note that you need [Redis Stack](https://redis.io/docs/about/about-stack/) to use it.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment Variables

The connector uses the following environment variables:

- **output**: This is the ouput topic that will receive the stream (Default: `output`, Required: `True`)
- **redis_host**: Host address for the Redis instance (Required: `True`)
- **redis_host**: Host address for the Redis instance (Required: `True`)
- **redis_port**: Port for the Redis instance (Default: `6379`, Required: `True`)
- **redis_password**: Password for the Redis instance (Default: `None`, Required: `False`)
- **redis_username**: Username for the Redis instance (Default: `None`, Required: `False`)

## Requirements / Prerequisites

You will need to have a Redis Stack database. Either you can use the [Redis Cloud](https://redis.com/cloud/overview/) or
you can install Redis locally. You can find the instructions to [install Redis locally](https://redis.io/docs/install/install-stack/).

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open Source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo. Please star us and mention us on social to show your appreciation.
