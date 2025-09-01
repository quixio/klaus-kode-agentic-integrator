# HTTP API Source

[This code sample](https://github.com/quixio/quix-samples/tree/main/python/sources/http_source) demonstrates how to run a Flask HTTP API as a web gateway and use it to publish to a Kafka topic via HTTP POST requests.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the Samples to use this project

Clicking `Edit code` on the Sample, forks the project to your own Git repo so you can customize it before deploying.

You can test your endpoint by sending a message via curl:
`curl -X POST -H "Content-Type: application/json" -d '{"sessionId": "000001", "name": "Tony Hawk", "purchase": "skateboard" }' https://<your-deployment-url>/data/
`

## Environment variables

The code sample uses the following environment variables:

- **output**: This is the output topic for hello world data.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.



image: Flaticon.com