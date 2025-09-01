# Import utility modules
import os
import random
import json
import logging
from time import sleep

# import vendor-specific libraries
from quixstreams import Application
from quixstreams.models.serializers.quix import JSONSerializer, SerializationContext
import influxdb_client_3 as InfluxDBClient3

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a Quix Application
app = Application(use_changelog_topics=False)

# Define a serializer for messages, using JSON Serializer for ease
serializer = JSONSerializer()

# Define the topic using the "output" environment variable
topic_name = os.environ["output"]
topic = app.topic(topic_name)

influxdb3_client = InfluxDBClient3.InfluxDBClient3(token=os.environ["INFLUXDB_TOKEN"],
                         host=os.environ["INFLUXDB_HOST"],
                         org=os.environ["INFLUXDB_ORG"],
                         database=os.environ["INFLUXDB_DATABASE"])

measurement_name = os.environ.get("INFLUXDB_MEASUREMENT_NAME", os.environ["output"])
interval = os.environ.get("task_interval", "5m")

# Global variable to control the main loop's execution
run = True

# InfluxDB interval-to-seconds conversion dictionary
UNIT_SECONDS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
    "w": 604800,
    "y": 31536000,
}

# Helper function to convert time intervals (like 1h, 2m) into seconds for easier processing.
# This function is useful for determining the frequency of certain operations.
def interval_to_seconds(interval: str) -> int:
    try:
        return int(interval[:-1]) * UNIT_SECONDS[interval[-1]]
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(
                "interval format is {int}{unit} i.e. '10h'; "
                f"valid units: {list(UNIT_SECONDS.keys())}")
    except KeyError:
        raise ValueError(
            f"Unknown interval unit: {interval[-1]}; "
            f"valid units: {list(UNIT_SECONDS.keys())}")

interval_seconds = interval_to_seconds(interval)

# Function to fetch data from InfluxDB and send it to Quix
# It runs in a continuous loop, periodically fetching data based on the interval.
def get_data():
    # Run in a loop until the main thread is terminated
    while run:
        try:
            query_definition = f'SELECT * FROM "{measurement_name}" WHERE time >= now() - {interval}'
            print(f"Sending query {query_definition}")
            # Query InfluxDB 3.0 using influxql or sql
            table = influxdb3_client.query(
                                    query=query_definition,
                                    mode="pandas",
                                    language="influxql")

            table = table.drop(columns=["iox::measurement"])

            # If there are rows to write to the stream at this time
            if not table.empty:
                # Convert to JSON for JSON-to-bytes serializer
                json_result = table.to_json(orient='records', date_format='iso')
                yield json_result
                print(f"Query retrieved {table.size} records")
            else:
                print("No new data to publish.")

            # Wait for the next interval
            sleep(interval_seconds)

        except Exception as e:
            print("query failed", flush=True)
            print(f"error: {e}", flush=True)
            sleep(1)

def main():
    """
    Read data from the Query and publish it to Kafka
    """

    # Create a pre-configured Producer object.
    # Producer is already setup to use Quix brokers.
    # It will also ensure that the topics exist before producing to them if
    # Application.Quix is initialized with "auto_create_topics=True".

    with app.get_producer() as producer:
        for res in get_data():
            # Parse the JSON string into a Python object
            records = json.loads(res)
            for index, obj in enumerate(records):
                # Generate a unique message_key for each row
                # Change to a tag name if you want to aggregate data by a specific tag such as "SensorID"—e.g. message_key = obj['SensorID']
                message_key = f"INFLUX_DATA_{str(random.randint(1, 100)).zfill(3)}_{index}" 
                logger.info(f"Produced message with key:{message_key}, value:{obj}")

                # Serialize row value to bytes
                serialized_value = serializer(
                    value=obj, ctx=SerializationContext(topic=topic.name)
                )

                # publish the data to the topic
                producer.produce(
                    topic=topic.name,
                    key=message_key,
                    value=serialized_value,
                )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting.")