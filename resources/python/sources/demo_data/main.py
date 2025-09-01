import os

import pandas as pd

# import the dotenv module to load environment variables from a file
from dotenv import load_dotenv
from quixstreams import Application
from quixstreams.sources.community.pandas import PandasDataFrameSource

load_dotenv(override=False)

# Define the topic using the "output" environment variable
topic_name = os.getenv("output")
if topic_name is None:
    raise ValueError(
        "The 'output' environment variable is required. This is the output topic that data will be published to."
    )

# Use "Quix__Deployment__Id" env variable as a consumer group name to run multiple instances independently
# If not provided, "demo-data" will be used
consumer_group = os.getenv('Quix__Deployment__Id', 'demo-data')

# Create an Application.
app = Application(consumer_group=consumer_group)

# Specify the filename here
filename = "demo-data.csv"

# Read data from the csv file
df = pd.read_csv(filename)

# Create a Source instance based on a DataFrame
pandas_source = PandasDataFrameSource(
    df=df,
    name=f"pandas-source-{consumer_group}",  # Use random consumer group as a name to generate random intermediate topics on each Source run
    key_column="SessionId",  # use the "SessionId" column for message keys
    delay=0.05,  # Add a delay between each row to simulate real-time processing
)
output_topic = app.topic(topic_name)

# Connect the Source to a StreamingDataFrame
sdf = app.dataframe(source=pandas_source)

# Print incoming data
sdf.print(metadata=True)
# Send data to the output topic
sdf.to_topic(output_topic)


if __name__ == "__main__":
    # Start the application
    app.run(sdf)
