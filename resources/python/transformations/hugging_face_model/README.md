# Hugging Face model

[This code sample](https://github.com/quixio/quix-samples/tree/main/python/transformations/hugging_face_model) demonstrates how to consume data from a Kafka topic, use an ML model (downloaded from [Hugging Face](https://huggingface.co/)) to run inference on a specific field within the data, then publish the results to an output topic:

- It listens to the input Kafka topic for data to predict on.
- It generates a prediction using the selected Hugging Face model.
- It outputs the class and score of the prediction to another Kafka topic.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the Samples to use this project.

Clicking `Deploy` on the Sample, deploys a pre-built container in Quix. Complete the environment variables to configure the container.

Clicking `Edit code` on the Sample, forks the project to your own Git repo so you can customize it before deploying.

## Environment variables

The code sample uses the following environment variables:

- **input**: This is the raw data input topic.
- **output**: This is the output for the hugging face model score.
- **HuggingFaceModel**: Name of the Hugging Face model to be used. A list of available Hugging Face models can be found [here](https://huggingface.co/models).
- **TextColumnName**: "For the table structured input, name of the column where input text to perform predictions on."

## Requirements/prerequisites

When deploying this Python project, ensure you allow enough computational resources (1GB RAM) to host and execute the Hugging Face pipeline objects.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
