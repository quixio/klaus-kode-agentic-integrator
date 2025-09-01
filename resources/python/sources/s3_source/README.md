# S3 Source Connector

[This connector](https://github.com/quixio/quix-samples/tree/main/python/sources/s3_source) demonstrates how to connect to Amazon S3 to read files into a Kafka topic.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment variables

This connector uses the following environment variables:

- **output**: The output topic to stream Segment data into
- **S3_BUCKET**: The URI or URL to your S3 bucket
- **S3_REGION**: The region of your S3 bucket
- **S3_SECRET**: Your AWS secret
- **S3_ACCESS_KEY_ID**: Your AWS Access Key
- **S3_FOLDER_PATH**: The path to the S3 folder to consume
- **S3_FILE_FORMAT**: The file format of the files
- **S3_FILE_COMPRESSION**: The type of file compression used for the files

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
