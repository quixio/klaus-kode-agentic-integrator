# Segment

[This connector](https://github.com/quixio/quix-samples/tree/main/python/sources/segment_webhook) demonstrates how to connect to Segment, read event data and publish that data to a Kafka topic.

It's secure, using a secret shared with both Quix and Segment.

And we've used [Waitress](https://github.com/Pylons/waitress), "a production-quality pure-Python WSGI server with very acceptable performance. It has no dependencies except ones that live in the Python standard library. It runs on CPython on Unix and Windows.”

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment variables

This connector uses the following environment variables:

- **output**: The output topic to stream Segment data into
- **shared_secret**: The secret you configured in Segment

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
