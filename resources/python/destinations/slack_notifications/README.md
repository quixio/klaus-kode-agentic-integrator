# Slack Notifications

[This connector](https://github.com/quixio/quix-samples/tree/main/python/destinations/slack_notifications) demonstrates how to consume data from a Kafka topic and trigger a Slack webhook based on specific matching critera that you apply to the incoming data.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment Variables

The connector uses the following environment variables:

- **input**: Name of the input topic to listen to.
- **webhook_url**: The webhook url to send notifications to

## Requirements / Prerequisites

You'll need to have access to Slack and be able to set up a webhook here: https://api.slack.com/apps

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
