from quixstreams import Application

import os
import json
import redis


# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

r = redis.Redis(
    host=os.environ['redis_host'],
    port=int(int(os.environ['redis_port'])),
    password=os.environ['redis_password'],
    username=os.environ['redis_username'] if 'redis_username' in os.environ else None,
    decode_responses=True)

redis_key_prefix = os.environ['redis_key_prefix']

app = Application(consumer_group="redis-destination")

input_topic = app.topic(os.environ["input"])


def send_data_to_redis(value: dict) -> None:
    print(value)

    # Convert the entire dictionary to a JSON string
    json_data = json.dumps(value)

    # Use a Redis key for storing the JSON data. This key can be a combination of
    # some unique identifier in your value dict, like a timestamp or a specific tag.
    # For this example, let's assume you have a unique 'id' in your value dict.
    key = f"{redis_key_prefix}:{value['key']}"

    # Store the JSON string in Redis
    r.set(key, json_data)

    print(f"Data stored in Redis under key: {key}")


sdf = app.dataframe(input_topic)
sdf = sdf.update(send_data_to_redis)

if __name__ == "__main__":
    print("Starting application")
    app.run(sdf)
