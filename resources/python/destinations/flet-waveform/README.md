# Flet Real-time Waveform Viewer

[This code sample](https://github.com/quixio/quix-samples/tree/main/python/destinations/flet) demonstrates how to create a real-time data visualization web application using Flet and Quix Streams. The application consumes data from a Kafka topic and displays sensor data (temperature and humidity) in real-time charts.

This destination creates an interactive web interface that visualizes streaming data with live updates and connection status monitoring.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the Samples to use this project.

Clicking `Edit code` on the Sample, forks the project to your own Git repo so you can customize it before deploying.

## Environment variables

The code sample uses the following environment variables:

- **input**: Name of the input topic to listen to (expects data with 'temperature' and 'humidity' fields).

## Features

- **Real-time Data Visualization**: Live charts displaying temperature and humidity data
- **Connection Status Monitoring**: Visual indicators for Kafka connection status
- **Web Interface**: Accessible via web browser on port 80
- **Multi-instance Support**: Handles multiple browser tabs/instances gracefully
- **Responsive Design**: Adapts to different screen sizes


## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
