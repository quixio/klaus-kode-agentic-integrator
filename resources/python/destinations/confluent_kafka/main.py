from quixstreams.app import Application
from quixstreams import message_context
from quixstreams.kafka.producer import Producer
import os
import json

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

# SASL configuration
sasl_config = {
    'sasl.mechanism': 'PLAIN',
    'security.protocol': 'SASL_SSL',
    'sasl.username': os.getenv("kafka_key", ""),
    'sasl.password': os.getenv("kafka_secret", "")
}
broker_address = os.getenv("kafka_broker_address", "")
input_topic_name = os.getenv("input", "")
output_topic_name = os.getenv("kafka_topic", "")

if sasl_config["sasl.username"] == "" or sasl_config["sasl.password"] == "":
    print("Please provide kafka_key and kafka_secret")
    exit(1)

if broker_address == "":
    print("Please provide kafka_broker_address")
    exit(1)

if input_topic_name == "" or output_topic_name == "":
    print("Please provide input and output topics")
    exit(1)

# Initialize the Kafka Producer
producer = Producer(broker_address=broker_address, extra_config=sasl_config)

# Define your application
app = Application(consumer_group="kafka-connector-consumer-group", 
                       auto_offset_reset="earliest")

# Define the input and output topics
input_topic = app.topic(input_topic_name)

# Create a StreamingDataFrame instance for consuming data
sdf = app.dataframe(input_topic)

# Define a function to produce messages to Kafka
def produce_to_kafka(value):

    message_key = message_context().key

    # build the payload object
    payload = {
        "StreamId": message_key.decode('utf-8'),
        "MessageType": str(type(value)),
        "Value": json.dumps(value),
    }

    # Convert the payload dictionary to a JSON string
    json_payload = json.dumps(payload)
    
    # Encode the JSON string to bytes
    payload_bytes = json_payload.encode('utf-8')

    # # Produce the message to the output topic
    producer.produce(topic=output_topic_name, value=payload_bytes)
    # # Ensure delivery of the message
    producer.flush()

# Apply the produce function to the StreamingDataFrame
sdf = sdf.update(produce_to_kafka)

# Run the application to start consuming, processing, and producing data
app.run(dataframe=sdf)