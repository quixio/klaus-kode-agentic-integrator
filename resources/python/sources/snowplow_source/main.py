from quixstreams import Application
from snowplow_analytics_sdk import event_transformer as et
import boto3

from datetime import datetime
import traceback
import time
import json
import os

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

# should the main loop keep running?
run = True
is_connected = False

kinesis_client = None
producer_topic = None
quix_producer = None


def connect_to_aws() -> bool:
    global kinesis_client

    if quix_producer is None:
        print("Not connected to Quix")
        return False

    try:
        kinesis_client = boto3.client(
            'kinesis',
            aws_access_key_id = os.environ["aws_access_key_id"],
            aws_secret_access_key = os.environ["aws_secret_access_key"],
            region_name = os.environ["aws_region_name"]
        )
    except Exception as e:
        print(f"ERROR! - Failed to connect to AWS: {e}")
        return False

def publish_to_quix(data):

    # use the snowplow sdk to transform the incoming data
    snowplow_data_dict = et.transform(data)

    # add a time stamp to the row
    snowplow_data_dict["time"] = datetime.now()

    # use the event name for the status message and the message key
    event_name = str(snowplow_data_dict["event_name"].values[0])

    # publish to the stream
    producer.produce(topic=producer_topic.name,
                     key=event_name,
                     value=json.dumps(snowplow_data_dict))

    print(f"Published {event_name}")

def get_kinesis_data():
    global is_connected

    if quix_producer is None:
        print("Not connected to Quix")
        return False

    si = kinesis_client.get_shard_iterator(
        StreamName = os.environ["aws_stream_name"],
        ShardId='shardId-000000000000',
        ShardIteratorType='LATEST'
    )

    shard_iterator = si["ShardIterator"]

    if not is_connected:
        print("CONNECTED!")
        is_connected = True

    while run:
        record_data = kinesis_client.get_records(ShardIterator = shard_iterator)
        shard_iterator = record_data["NextShardIterator"]

        if len(record_data["Records"]) > 0:

            for record in record_data["Records"]:
                data = record["Data"]

                if isinstance(data, bytes):
                    publish_to_quix(data.decode())
                else:
                    publish_to_quix(data)

        behind = record_data["MillisBehindLatest"]
        if behind < 1000:
            time.sleep(1) # if < 1s behind wait 1 second
        else:
            time.sleep(0.1) # if behind > 1s, go a bit faster!


def connect_to_quix():
    global producer_topic
    global producer

    # Create a Quix Application, this manages the connection to the Quix platform
    app = Application()

    print("Opening output topic")
    
    # Create the producer, this is used to write data to the output topic
    producer = app.get_producer()

    # Check the output topic is configured
    output_topic_name = os.getenv("output", "")
    producer_topic = app.topic(output_topic_name)


def main():
    global run

    # validate the required env vars have been set supplied
    required_env_vars = ["aws_access_key_id", "aws_secret_access_key", "aws_region_name", "output"]
    for var in required_env_vars:
        if var not in os.environ:
            raise ValueError(f"Environment variable {var} is required but not set.")

    try:
        connect_to_quix()
        aws_connected = connect_to_aws()

        if not aws_connected:
            raise ValueError("Error connecting to AWS")

        print("Waiting for Kinesis data")
        get_kinesis_data() # blocking call, gets data from AWS and published with Quix

    except KeyboardInterrupt:
        print("Exiting.")
        run = False
    except Exception as e:
        print("ERROR! - {}".format(traceback.format_exc()))
        raise e

if __name__ == "__main__":
    main()
