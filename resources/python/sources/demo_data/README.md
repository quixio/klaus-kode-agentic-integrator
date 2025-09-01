# Demo Telemetry Data

[This code sample](https://github.com/quixio/quix-samples/tree/main/python/sources/demo_data) demonstrates how to publish F1&reg; telemetry data into a topic from a recorded Codemasters&reg; F1&reg; 2019 game session.

You'll have access to the speed, acceleration, braking and other detailed data from a real F1&reg; car, rebroadcast in real time.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the Samples to use this project.

Clicking `Deploy` on the Sample, deploys a pre-built container in Quix. Complete the environment variables to configure the container.

Clicking `Edit code` on the Sample, forks the project to your own Git repo so you can customize it before deploying.

## Environment variables

The code sample uses the following environment variables:

- **Topic**: Name of the output topic to write into.

## CSV data

### Columns

The columns included in this CSV sample are:

| Column                | Description                                                                                                                                                 |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Timestamp             | The timestamp, in unix format, of the data originally arriving into the Quix platform.                                                                      |
| Motion_WorldPositionZ | Z axis position of the player in the world                                                                                                                  |
| Motion_WorldPositionY | Y axis position of the player in the world                                                                                                                  |
| Motion_WorldPositionX | X axis position of the player in the world                                                                                                                  |
| TotalLapDistance      | Total distance of all the laps                                                                                                                              |
| Steer                 | Position of the steering wheel                                                                                                                              |
| Speed                 | Speed of the vehicle                                                                                                                                        |
| LapDistance           | Distance covered this lap                                                                                                                                   |
| Gear                  | Currently selected gear                                                                                                                                     |
| EngineTemp            | Engine temperature                                                                                                                                          |
| EngineRPM             | Engine RPM                                                                                                                                                  |
| Brake                 | Amount of brake being applied                                                                                                                               |
| DriverStatus          | Information about the drivers status, e.g. Flying_lap or In_garage                                                                                          |
| LapNumber             | The current lap number                                                                                                                                      |
| LapValidity           | Is the lap valid? If the driver comitted an office the lap may not be valid                                                                                 |
| PitStatus             | Is the vehicle in the pit                                                                                                                                   |
| Sector                | Which sector the vehicle is currently completing                                                                                                            |
| SessionID             | The session ID associated with this stream                                                                                                                  |

### Rows

This is a sample of the rows from the CSV file. Note that some columns have been omitted for brevity and clarity.

| Timestamp     | Motion_WorldPositionZ | Motion_WorldPositionY | Motion_WorldPositionX | TotalLapDistance  | Steer | Speed | LapDistance       | Gear | EngineTemp | EngineRPM |
| ------------- | --------------------- | --------------------- | --------------------- | ----------------- | ----- | ----- | ----------------- | ---- | ---------- | --------- |
| 1687180461013 | 218.9416961669922     | 98.20722961425781     | -25.482023239135742   | 2095.084228515625 | -1    | 223   | 2095.084228515625 | 6    | 90         | 10251     |
| 1687180461057 | 216.65463256835938    | 98.32571411132812     | -24.000829696655273   | 2097.9296875      | -1    | 224   | 2097.9296875      | 6    | 90         | 10308     |

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
