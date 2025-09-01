import time
from collections import defaultdict
from quixstreams import Application

import os
import json
import redis

from dotenv import load_dotenv
load_dotenv()

run = True # a flag to stop the main loop

r = redis.Redis(
    host=os.environ['redis_host'],
    port=int(int(os.environ['redis_port'])),
    password=os.environ['redis_password'],
    username=os.environ['redis_username'] if 'redis_username' in os.environ else None,
    decode_responses=True)

# Create a Quix Application, this manages the connection to the Quix platform
app = Application()
# Create the producer, this is used to write data to the output topic
producer = app.get_producer()

# Check the output topic is configured
output_topic_name = os.getenv("output", "")
if output_topic_name == "":
    raise ValueError("output_topic environment variable is required")
output_topic = app.topic(output_topic_name)


# This function is used only to print the information about the keys
def print_info(key_name, key_info):
    print(f"\tTotal samples: {key_info.total_samples}")
    print(f"\tFirst timestamp: {key_info.first_timestamp}")
    print(f"\tLast timestamp: {key_info.last_timestamp}")
    print(f"\tRetention time: {key_info.retention_msecs}ms")
    print(f"\tLabels: {key_info.labels}")
    print(f"\tSource key: {key_info.source_key}")
    print(f"\tRules: {key_info.rules}")


# This is the main function that reads from Redis and publishes to Quix
def get_data():
    first_timestamp = 0

    while run:
        data = r.ts().mrange(first_timestamp, "+", filters=["ts=true"], count=1000, with_labels=True)
        data_by_timestamp = defaultdict(dict)
        
        for data_stream in data:
            stream_name = next(iter(data_stream))
            samples = data_stream[stream_name][1]

            for ts, value in samples:
                data_by_timestamp[ts][stream_name] = value
                if first_timestamp == "-" or ts > first_timestamp:
                    first_timestamp = ts + 1

        number_of_samples = len(data_by_timestamp)
        if number_of_samples == 0:
            print("No data, waiting..")
            time.sleep(0.5)
        else:
            print(f"Publishing {number_of_samples} samples")
            for timestamp, stream_data in data_by_timestamp.items():
                for stream_name, value in stream_data.items():
                    message = {
                        stream_name: value,
                        "Timestamp": timestamp
                    }
                    producer.produce(topic=output_topic.name,
                                     key=stream_name,
                                     value=json.dumps(message))


def main():
    keys = r.keys()

    for key in keys:
        try:
            print(f"Key: {key}")
            info = r.ts().info(key)
            existing_labels = info.labels
            existing_labels["ts"] = "true"
            r.ts().alter(key, labels=existing_labels)
            info = r.ts().info(key)
            print_info(key, info)
        except:
            print(f"Key {key} is not a ts key")

    get_data()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting.")
        run = False
