# OPC UA Client

[This connector](https://github.com/quixio/quix-samples/tree/main/python/sources/opc_ua_client) allows you to connect to your OPC UA server to capture and handle your data in Quix.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Locate and click the connector tile, fill in the required parameters, then click `Test connection & deploy` to deploy the connector to your Quix instance.

Clicking `Customise` allows you to view or save the code to the repo that backs your Quix cloud instance.

## Environment Variables

The connector uses the following environment variables:

- **output**: Name of the output topic to publish to.
- **OPC_SERVER_URL**: The URL to your OPC UA server.
- **OPC_NAMESPACE**: The namespace of the data coming from your OPC UA server.
- **PARAMETER_NAMES_TO_PROCESS**: List of parameters from your OPC UA server that you want to process. e.g. ['a', 'b', 'c']. NB:Use single quotes.


## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
